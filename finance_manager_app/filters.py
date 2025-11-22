from django_filters import rest_framework as filters
from finance_manager_app import models
from datetime import datetime, timedelta

class TransactionFilter(filters.FilterSet):
    created_at = filters.DateTimeFromToRangeFilter(field_name='created_at')
    category__icontains = filters.CharFilter(field_name='category__category', lookup_expr='icontains')
    category__iexact = filters.CharFilter(field_name='category__category', lookup_expr='iexact')

    class Meta:
        model = models.Transaction
        fields = {
            'transaction_type' : ['iexact']
        }

class Monthly_budgetFilter(filters.FilterSet):
    created_at = filters.DateFromToRangeFilter(field_name='created_at')
    category__icontains = filters.CharFilter(field_name='category__category', lookup_expr='icontains')
    category__iexact = filters.CharFilter(field_name='category__category', lookup_expr='iexact')
    

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

class DashboardFilter(filters.FilterSet):
    period = filters.CharFilter(method='filter_data')

    def filter_data(self, queryset, name, value):
        if value == '2m':
            start = datetime.isoformat(datetime.now() - timedelta(days=60))
        elif value == '3m':
            start = datetime.isoformat(datetime.now() - timedelta(days=90))
        else:
            start = datetime.isoformat(datetime.now() - timedelta(days=30))
        return queryset.filter(created_at__gte = start)
    
    class Meta:
        model = models.Transaction
        fields = ['period']