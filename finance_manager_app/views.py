from rest_framework import generics
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from . import models
from finance_manager.permissions import IsOwner
from django_filters.rest_framework import DjangoFilterBackend
from .filters import TransactionFilter
from .serializers import TransactionSerializer


class TransactionCreateApiView(generics.CreateAPIView):
    serializer_class = None
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user = self.request.user)
    

class TransactionListApiView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TransactionFilter

    def get_queryset(self):
        return models.Transaction.objects.filter(user = self.request.user)




