from rest_framework import generics
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from . import models
from finance_manager.permissions import IsOwner
from django_filters.rest_framework import DjangoFilterBackend
from .filters import TransactionFilter, Monthly_budgetFilter, RecurringBillFilter
from .serializers import TransactionSerializer, BudgetSerializer, RecurringBillSerializer
from rest_framework import mixins
    

class TransactionView(
    generics.GenericAPIView, 
    mixins.CreateModelMixin, 
    mixins.ListModelMixin, 
    mixins.UpdateModelMixin, 
    mixins.DestroyModelMixin
    ):
    serializer_class = TransactionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsOwner, IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TransactionFilter


    def get_queryset(self):
        return models.Transaction.objects.filter(user = self.request.user)
    
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
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsOwner, IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = Monthly_budgetFilter

    def get_queryset(self):
        return  models.Monthly_budget.objects.filter(user = self.request.user)

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
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsOwner, IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecurringBillFilter

    def get_queryset(self):
        return models.Recurring_bill.objects.filter(user = self.request.user)
    
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
