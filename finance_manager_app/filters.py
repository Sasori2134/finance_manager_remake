from django_filters import rest_framework as filters
from finance_manager_app import models

class TransactionFilter(filters.FilterSet):
    created_at = filters.DateTimeFromToRangeFilter(field_name='created_at')

    class Meta:
        model = models.Transaction
        fields = {
            'category' : ['icontains'],
            'transaction_type' : ['iexact']
        }