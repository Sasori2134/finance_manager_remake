from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from . import models
from finance_manager.permissions import IsOwner
from django_filters.rest_framework import DjangoFilterBackend
from .filters import TransactionFilter, RecurringBillFilter, Monthly_budgetFilter
from .serializers import TransactionSerializer, BudgetSerializer, RecurringBillSerializer, RegisterSerializer
from rest_framework import mixins
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.response import Response
from django.db.models import Sum, F, Q, Value, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce


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
        queryset = self.filter_queryset(self.get_queryset())
        new_queryset = queryset.select_related('category').annotate(spent=ExpressionWrapper(Sum(Coalesce('category__transaction__price', Value(
            0))), output_field=DecimalField()), filter=Q(category__transaction__user=request.user)).annotate(remaining=F('budget') - F('spent'))
        serialized = self.get_serializer(new_queryset, many=True)
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
    

class LogoutView(
    APIView
):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        token = RefreshToken(request.data.get('refresh'))
        token.blacklist()
        return Response(status=status.HTTP_200_OK)
