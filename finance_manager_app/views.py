from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from . import models
from finance_manager.permissions import IsOwner
from django_filters.rest_framework import DjangoFilterBackend
from .filters import TransactionFilter, RecurringBillFilter, Monthly_budgetFilter, DashboardFilter
from .serializers import TransactionSerializer, BudgetSerializer, RecurringBillSerializer, RegisterSerializer, DashboardSerializer
from rest_framework import mixins
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.response import Response
from django.db.models import Sum, Avg, F, Q, Value, ExpressionWrapper, DecimalField, Case, When
from django.db.models.functions import ExtractMonth
from django.db.models.functions import Coalesce
from . import cache
from datetime import date


class RegisterView(
    generics.CreateAPIView
):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user_model = get_user_model()
        return user_model.objects.create_user(**serializer.data)


class TransactionView(
    generics.GenericAPIView,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin
):
    serializer_class = TransactionSerializer
    permission_classes = [IsOwner, IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TransactionFilter

    def get_queryset(self):
        return models.Transaction.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class Monthly_budgetView(
    generics.GenericAPIView,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin
):
    serializer_class = BudgetSerializer
    permission_classes = [IsOwner, IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = Monthly_budgetFilter

    def get_queryset(self):
        return models.Monthly_budget.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        cached = cache.get_cached_data(user_id=request.user.id, key="budget")
        if cached:
            return Response(cached)
        queryset = self.filter_queryset(self.get_queryset())
        current_date = date.today()
        transaction_filter = (
            Q(category__transaction__user=request.user) &
            Q(category__transaction__created_at__month = current_date.month) &
            Q(category__transaction__created_at__year = current_date.month) &
            Q(category__transaction__transaction_type = 'expense')
        )

        new_queryset = queryset.select_related('category').annotate(spent=ExpressionWrapper(Sum(Coalesce('category__transaction__price', Value(
            0))), output_field=DecimalField()), filter=transaction_filter).annotate(remaining=F('budget') - F('spent'))
        
        serialized = self.get_serializer(new_queryset, many=True)
        cache.set_cached_data(user_id=request.user.id, key="budget", value=serialized.data)
        return Response(serialized.data)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, *kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class RecurringBillView(
    generics.GenericAPIView,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin
):

    serializer_class = RecurringBillSerializer
    permission_classes = [IsOwner, IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecurringBillFilter

    def get_queryset(self):
        return models.Recurring_bill.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, *kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class DashboardListView(
    generics.ListAPIView
):
    serializer_class = DashboardSerializer
    permission_classes = [IsOwner, IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = DashboardFilter

    def get_queryset(self):
        return models.Transaction.objects.filter(user=self.request.user).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        serialized = DashboardSerializer(data = request.query_params)
        if serialized.is_valid(raise_exception=True):
            cached_data = cache.get_cached_data(user_id=request.user.id, key="dashboard", period=serialized.data.get("period"))
            if cached_data:
                return Response(cached_data)
            
            queryset = self.filter_queryset(self.get_queryset())
            avg_income = queryset.filter(transaction_type='income').aggregate(
                Avg("price", default=0))['price__avg']
            
            avg_expense = queryset.filter(transaction_type='expense').aggregate(
                Avg("price", default=0))['price__avg']
            
            balance = queryset.aggregate(balance=Sum(
                Case(
                    When(transaction_type='income', then=F('price')),
                    When(transaction_type='expense', then=-F('price')),
                    default=0,
                    output_field=DecimalField()
                )
            )
            )['balance'] or 0

            total = queryset.aggregate(
                income=Sum('price', default=0, filter=Q(
                    transaction_type='income')),
                expense=Sum('price', default=0, filter=Q(
                    transaction_type='expense'))
            )
            donut_chart = queryset.values(transaction_category=F(
                'category__category')).annotate(price=Sum('price'))
            monthly_income_expense = queryset.values(month=ExtractMonth(F('created_at'))).annotate(expense=Sum('price', filter=Q(
                transaction_type='expense'), default=0), income=Sum('price', filter=Q(transaction_type='income'), default=0))
            
            recent_transactions = TransactionSerializer(queryset[:5], many=True)
            
            data = {
                'avg_income': round(avg_income, 2),
                'avg_expense': round(avg_expense, 2),
                'balance': balance,
                'total_income': total.get('income'),
                'total_expense': total.get('expense'),
                'donut_chart': list(donut_chart),
                'monthly_income_expense': list(monthly_income_expense),
                'recent_transactions': recent_transactions.data
            }
            cache.set_cached_data(user_id=request.user.id, key="dashboard", value=data, period=serialized.data.get("period"))
            return Response(data)


class LogoutView(
    generics.GenericAPIView
):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        token = RefreshToken(request.data.get('refresh'))
        token.blacklist()
        return Response(status=status.HTTP_200_OK)
