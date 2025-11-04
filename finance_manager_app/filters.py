from django_filters import rest_framework as filters
from finance_manager_app import models

class TransactionFilter(filters.FilterSet):
    created_at = filters.DateTimeFromToRangeFilter(field_name='created_at')

    class Meta:
        model = models.Transaction
        fields = {
            'category' : ['icontains', 'iexact'],
            'transaction_type' : ['iexact']
        }

class Monthly_budgetFilter(filters.FilterSet):
    created_at = filters.DateFromToRangeFilter(field_name='created_at')

    class Meta:
        model = models.Monthly_budget
        fields = {
            'category' : ['icontains', 'iexact']
        }

class RecurringBillFilter(filters.FilterSet):
    created_at = filters.DateTimeFromToRangeFilter(field_name='created_at')
    max_amount = filters.NumberFilter(field_name='amount', lookup_expr="lte")
    min_amount = filters.NumberFilter(field_name='amount', lookup_expr='gte')

    class Meta:
        model = models.Recurring_bill
        fields = {
            'category' : ['icontains', 'iexact'],
            'item' : ['icontains', 'iexact'],

        }