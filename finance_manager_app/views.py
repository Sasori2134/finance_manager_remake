import secrets
from datetime import date
from hashlib import sha256

from django.db.models import Avg, Case, Exists, F, OuterRef, Q, Sum, When
from django.db.models.functions import ExtractMonth
from django_filters.rest_framework import DjangoFilterBackend
from django_redis import get_redis_connection
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from . import cache, models
from .decorators.cache_decorator import cache_set_or_get
from .decorators.rate_limiter_decorator import rate_limiter
from .filters import (
    DashboardFilter,
    MonthlyBudgetFilter,
    RecurringBillFilter,
    TransactionFilter,
)
from .helper_functions import get_budgets_with_totals, get_single_budget_with_totals
from .serializers import (
    BudgetSerializer,
    ChangepasswordinputSerializer,
    DashboardSerializer,
    ForgotPasswordEmailSerializer,
    RecurringBillSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    TransactionSerializer,
)
from .tasks import send_password_reset_email


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer) -> None:
        serializer.save()


class TransactionViewSet(ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TransactionFilter

    def get_queryset(self):
        query = models.Transaction.objects.filter(user=self.request.user)
        if self.action == "destroy":
            return query
        return query.select_related("category")

    def perform_create(self, serializer) -> None:
        serializer.save(user=self.request.user)


class MonthlyBudgetViewSet(ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = MonthlyBudgetFilter

    def get_queryset(self):
        query = models.Monthly_budget.objects.filter(user=self.request.user)
        if self.action == "destroy":
            return query
        return query.select_related("category")

    def perform_create(self, serializer) -> None:
        serializer.save(user=self.request.user)

    def budget_response(self, instance):
        current_date = date.today()
        obj = get_single_budget_with_totals(instance, current_date, self.request.user)
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return self.budget_response(instance)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        instance = serializer.instance
        return self.budget_response(instance)

    @cache_set_or_get(key="budget", timeout=300)
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        current_date = date.today()

        new_queryset = get_budgets_with_totals(queryset, current_date, request.user)

        serialized = self.get_serializer(new_queryset, many=True)
        return Response(serialized.data)


class RecurringBillViewSet(ModelViewSet):
    serializer_class = RecurringBillSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecurringBillFilter

    def get_queryset(self):
        query = models.Recurring_bill.objects.filter(user=self.request.user)

        if self.action == "destroy":
            return query

        current_month = date.today().month
        current_year = date.today().year

        return query.select_related("category").annotate(
            paid=Exists(
                models.Transaction.objects.filter(
                    recurring_bill=OuterRef("pk"),
                    user=self.request.user,
                    created_at__month=current_month,
                    created_at__year=current_year,
                )
            )
        )

    def perform_create(self, serializer) -> None:
        serializer.save(user=self.request.user)


class DashboardView(generics.ListAPIView):
    serializer_class = DashboardSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = DashboardFilter

    def get_queryset(self):
        return models.Transaction.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )

    @cache_set_or_get(key="dashboard", timeout=300)
    def list(self, request, *args, **kwargs) -> Response:
        serialized = DashboardSerializer(data=request.query_params)
        serialized.is_valid(raise_exception=True)

        queryset = self.filter_queryset(self.get_queryset())
        calculations = queryset.aggregate(
            avg_income=Avg("price", default=0, filter=Q(transaction_type="income")),
            avg_expense=Avg("price", default=0, filter=Q(transaction_type="expense")),
            balance=Sum(
                Case(
                    When(transaction_type="income", then=F("price")),
                    When(transaction_type="expense", then=-F("price")),
                ),
                default=0,
            ),
            income=Sum("price", default=0, filter=Q(transaction_type="income")),
            expense=Sum("price", default=0, filter=Q(transaction_type="expense")),
        )

        donut_chart = (
            queryset.order_by()
            .values(
                transaction_category=F("category__category"),
            )
            .annotate(price=Sum("price"))
        )

        monthly_income_expense = (
            queryset.order_by()
            .values(month=ExtractMonth(F("created_at")))
            .annotate(
                expense=Sum("price", filter=Q(transaction_type="expense"), default=0),
                income=Sum("price", filter=Q(transaction_type="income"), default=0),
            )
        )

        recent_transactions = TransactionSerializer(
            queryset.select_related("category")[:5], many=True
        )

        data = {
            "avg_income": round(calculations["avg_income"], 2),
            "avg_expense": round(calculations["avg_expense"], 2),
            "balance": round(calculations["balance"], 2),
            "total_income": round(calculations["income"], 2),
            "total_expense": round(calculations["expense"], 2),
            "donut_chart": list(donut_chart),
            "monthly_income_expense_chart": list(monthly_income_expense),
            "recent_transactions": recent_transactions.data,
        }

        return Response(data)


class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordEmailSerializer
    permission_classes = [AllowAny]

    @rate_limiter(key="ratelimit", limit=3, timeout=600)
    def post(self, request, *args, **kwargs) -> Response:
        serialized = self.serializer_class(data=request.data)
        serialized.is_valid(raise_exception=True)
        email = serialized.data.get("email")

        token = secrets.token_urlsafe(64)
        hash_token = sha256(token.encode()).hexdigest()
        conn = get_redis_connection("default")
        conn.set(f"{email}:resetpasswordcode", hash_token, 300)

        send_password_reset_email.delay(email, token)
        return Response(status=status.HTTP_200_OK)


class NewPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]

    @rate_limiter(key="ratelimit", limit=5, timeout=600)
    def post(self, request, *args, **kwargs) -> Response:
        merged_data = {**request.data, **request.query_params.dict()}
        serialized = self.serializer_class(data=merged_data)
        serialized.is_valid(raise_exception=True)
        email = serialized.data.get("email")
        token = serialized.validated_data.get("token")
        conn = get_redis_connection("default")

        cached_token = (
            conn.get(f"{email}:resetpasswordcode").decode()
            if conn.get(f"{email}:resetpasswordcode")
            else None
        )

        if cached_token != sha256(token.encode()).hexdigest():
            return Response(
                {"detail": "Wrong or expired token"}, status=status.HTTP_400_BAD_REQUEST
            )

        conn.delete(f"{email}:resetpasswordcode")

        serialized.save()
        return Response({"detail": "Your password has successfully been changed"})


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs) -> Response:
        try:
            token = RefreshToken(request.data.get("refresh"))
        except TokenError:
            return Response(
                {"detail": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED
            )
        token.blacklist()
        return Response(status=status.HTTP_200_OK)
