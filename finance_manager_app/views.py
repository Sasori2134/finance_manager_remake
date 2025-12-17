from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from . import models
from finance_manager.permissions import IsOwner
from django_filters.rest_framework import DjangoFilterBackend
from .filters import TransactionFilter, RecurringBillFilter, Monthly_budgetFilter, DashboardFilter
from .serializers import TransactionSerializer, BudgetSerializer, RecurringBillSerializer, RegisterSerializer, DashboardSerializer, ChangepasswordinputSerializer
from rest_framework import mixins
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework import status
from rest_framework.response import Response
import secrets
from django.db.models import Sum, Avg, F, Q, Value, DecimalField, Case, When
from django.db.models.functions import ExtractMonth
from django.db.models.functions import Coalesce
from . import cache
from datetime import date
from .tasks import send_password_change_notification, send_password_reset_code
from django_redis import get_redis_connection
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password



class RegisterView(
    generics.CreateAPIView
):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        return serializer.save()


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
    lookup_field = 'pk'
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
            Q(category__transaction__created_at__year = current_date.year) &
            Q(category__transaction__transaction_type = 'expense')
        )

        new_queryset = queryset.select_related('category').annotate(spent=Coalesce(Sum('category__transaction__price', filter=transaction_filter), Value(
            0, output_field=DecimalField()))).annotate(remaining=F('budget') - F('spent'))
                
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
                'monthly_income_expense_chart': list(monthly_income_expense),
                'recent_transactions': recent_transactions.data
            }
            cache.set_cached_data(user_id=request.user.id, key="dashboard", value=data, period=serialized.data.get("period"))
            return Response(data)


class ChangepasswordView(generics.GenericAPIView):
    serializer_class = ChangepasswordinputSerializer
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        serialized = self.serializer_class(data = request.data, context = {'request' : request})
        serialized.is_valid(raise_exception=True)
        user = serialized.save()
        send_password_change_notification.delay(user.email)
        return Response({"message" : "Password has been changed!"}, status=status.HTTP_200_OK)
        

class GenerateresetpasswordcodeView(generics.GenericAPIView):
    serializer_class = None
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        conn = get_redis_connection('default')
        email = request.data.get('email')
        if conn.get(f'{email}:ratelimit'):
            conn.incr(f'{email}:ratelimit', 1)
            if int(conn.get(f'{email}:ratelimit')) > 3:
                return Response({'detail' : 'Too many attempts please try again in 15 minutes'},
                                 status=status.HTTP_429_TOO_MANY_REQUESTS)
        else:
            conn.set(f'{email}:ratelimit', 1, 900)
        cache_key = f'{email}:resetpasswordcode'
        if conn.get(cache_key):
            conn.delete(cache_key)
        code = str(secrets.randbelow(10**6))
        conn.set(f'{email}:resetpasswordcode', code, 300)
        send_password_reset_code.delay(email, code)
        return Response(status=status.HTTP_200_OK)
    
class VerifyresetpasswordcodeView(generics.GenericAPIView):
    serializer_class = None
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        conn = get_redis_connection('default')
        code = request.data.get('code')
        email = request.data.get('email')
        if conn.get(f'{email}:resetpasswordcode').decode() == code:
            conn.delete(f'{email}:resetpasswordcode')
            token = secrets.token_urlsafe(64)
            conn.set(f'{email}:resetpasswordtoken', token, 900)
            return Response({'token' : token}, status=status.HTTP_200_OK)
        return Response({'detail' : 'Code is expired'}, status=status.HTTP_400_BAD_REQUEST)


class ResetpasswordView(generics.GenericAPIView):
    serializer_class = None
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        conn = get_redis_connection('default')
        email = request.data.get('email')
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        cached_token = conn.get(f'{email}:resetpasswordtoken').decode() if conn.get(f'{email}:resetpasswordtoken') else None
        if cached_token and cached_token == token:
            user_model = get_user_model()
            user = user_model.objects.get(email = email)
            if user.check_password(new_password):
                return Response({'detail' : "You password can't be same as your current password"})
            try:
                validate_password(new_password)
            except ValidationError as e:
                return Response({'detail' : e.messages}, status=status.HTTP_400_BAD_REQUEST)
            conn.delete(f'{email}:resetpasswordtoken')
            user.set_password(new_password)
            user.save()
            return Response({"detail" : "Your password has successfully been changed"})
        return Response({'detail' : 'Wrong or expired token'}, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(
    generics.GenericAPIView
):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            token = RefreshToken(request.data.get('refresh'))
        except TokenError:
            return Response({"detail" : "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
        token.blacklist()
        return Response(status=status.HTTP_200_OK)
