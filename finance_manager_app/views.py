import secrets
from datetime import date

from django.db.models import Avg, Case, Exists, F, OuterRef, Q, Sum, When
from django.db.models.functions import Coalesce, ExtractMonth
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
    RecurringBillSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    SetpasswordcodeEmailSerializer,
    TransactionGetListSerializer,
    TransactionSerializer,
)
from .tasks import send_password_change_notification, send_password_reset_code


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        return serializer.save()


class TransactionViewSet(ModelViewSet):
    serializer_class = TransactionGetListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TransactionFilter

    def get_queryset(self):
        query = models.Transaction.objects.filter(user=self.request.user)
        if self.action == "destroy":
            return query
        return query.select_related("category")

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)


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

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)

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

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)


class DashboardListView(generics.ListAPIView):
    serializer_class = DashboardSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = DashboardFilter

    def get_queryset(self):
        return models.Transaction.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )

    def list(self, request, *args, **kwargs):
        serialized = DashboardSerializer(data=request.query_params)
        if serialized.is_valid(raise_exception=True):
            cached_data = cache.get_cached_data(
                user_id=request.user.id,
                key="dashboard",
                period=serialized.data.get("period"),
            )
            if cached_data:
                return Response(cached_data)
            queryset = self.filter_queryset(self.get_queryset())
            avg_income = queryset.filter(transaction_type="income").aggregate(
                Avg("price", default=0)
            )["price__avg"]

            avg_expense = queryset.filter(transaction_type="expense").aggregate(
                Avg("price", default=0)
            )["price__avg"]

            balance = (
                queryset.aggregate(
                    balance=Sum(
                        Case(
                            When(transaction_type="income", then=F("price")),
                            When(transaction_type="expense", then=-F("price")),
                        )
                    )
                )["balance"]
                or 0
            )

            total = queryset.aggregate(
                income=Sum("price", default=0, filter=Q(transaction_type="income")),
                expense=Sum("price", default=0, filter=Q(transaction_type="expense")),
            )
            donut_chart = queryset.values(
                transaction_category=F("category__category")
            ).annotate(price=Sum("price"))
            monthly_income_expense = queryset.values(
                month=ExtractMonth(F("created_at"))
            ).annotate(
                expense=Sum("price", filter=Q(transaction_type="expense"), default=0),
                income=Sum("price", filter=Q(transaction_type="income"), default=0),
            )

            recent_transactions = TransactionSerializer(queryset[:5], many=True)

            data = {
                "avg_income": round(avg_income, 2),
                "avg_expense": round(avg_expense, 2),
                "balance": balance,
                "total_income": total.get("income"),
                "total_expense": total.get("expense"),
                "donut_chart": list(donut_chart),
                "monthly_income_expense_chart": list(monthly_income_expense),
                "recent_transactions": recent_transactions.data,
            }
            cache.set_cached_data(
                user_id=request.user.id,
                key="dashboard",
                value=data,
                period=serialized.data.get("period"),
            )
            return Response(data)


class ChangepasswordView(generics.GenericAPIView):
    serializer_class = ChangepasswordinputSerializer
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        serialized = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serialized.is_valid(raise_exception=True)
        user = serialized.save()
        send_password_change_notification.delay(user.email)
        return Response(
            {"message": "Password has been changed!"}, status=status.HTTP_200_OK
        )


class GenerateresetpasswordcodeView(generics.GenericAPIView):
    serializer_class = SetpasswordcodeEmailSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        conn = get_redis_connection("default")
        serialized = self.serializer_class(data=request.data)
        serialized.is_valid(raise_exception=True)
        email = request.data.get("email")

        if conn.incr(f"{email}:ratelimit", 1) >= 3:  # Add 3 to constants
            return Response(
                {"detail": "Too many attempts please try again in 15 minutes"},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        cache_key = f"{email}:resetpasswordcode"  # Add it to constants
        conn.delete(cache_key)
        code = str(secrets.randbelow(10**6))  # add 10**6 to constants
        conn.set(f"{email}:resetpasswordcode", code, 300)  # add 300 to constants
        send_password_reset_code.delay(email, code)
        return Response(status=status.HTTP_200_OK)


class VerifyresetpasswordcodeView(generics.GenericAPIView):
    serializer_class = SetpasswordcodeEmailSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        conn = get_redis_connection("default")
        self.serializer_class(data=request.data)
        code = request.data.get("code")
        email = request.data.get("email")
        if conn.get(f"{email}:resetpasswordcode").decode() == code:
            conn.delete(f"{email}:resetpasswordcode")
            token = secrets.token_urlsafe(64)
            conn.set(f"{email}:resetpasswordtoken", token, 900)
            return Response({"token": token}, status=status.HTTP_200_OK)
        return Response(
            {"detail": "Code is expired"}, status=status.HTTP_400_BAD_REQUEST
        )


class ResetpasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        conn = get_redis_connection("default")
        serialized = self.serializer_class(data=request.data)
        serialized.is_valid(raise_exception=True)
        email = serialized.data.get("email")
        token = request.data.get("token")
        cached_token = (
            conn.get(f"{email}:resetpasswordtoken").decode()
            if conn.get(f"{email}:resetpasswordtoken")
            else None
        )
        if cached_token and cached_token == token:
            conn.delete(f"{email}:resetpasswordtoken")
            serialized.save()
            send_password_change_notification.delay(email)
            return Response({"detail": "Your password has successfully been changed"})
        return Response(
            {"detail": "Wrong or expired token"}, status=status.HTTP_400_BAD_REQUEST
        )


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            token = RefreshToken(request.data.get("refresh"))
        except TokenError:
            return Response(
                {"detail": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED
            )
        token.blacklist()
        return Response(status=status.HTTP_200_OK)
