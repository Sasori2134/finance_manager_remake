from django.db.models import (
    DecimalField,
    F,
    OuterRef,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce

from . import models


def get_budgets_with_totals(queryset, current_date, user):
    current_month_expenses = (
        models.Transaction.objects.filter(
            user=user,
            category=OuterRef("category_id"),
            created_at__year=current_date.year,
            created_at__month=current_date.month,
            transaction_type="expense",
        )
        .values("category_id")
        .annotate(total=Sum("price"))
        .values("total")
    )

    new_queryset = queryset.annotate(
        spent=Coalesce(
            Subquery(current_month_expenses),
            Value(0, output_field=DecimalField()),
        )
    ).annotate(remaining=F("budget") - F("spent"))

    return new_queryset


def get_single_budget_with_totals(budget_instance, current_date, user):
    current_month_expenses = (
        models.Transaction.objects.filter(
            user=user,
            category=budget_instance.category,
            created_at__year=current_date.year,
            created_at__month=current_date.month,
            transaction_type="expense",
        ).aggregate(total=Sum("price"))["total"]
        or 0
    )

    budget_instance.spent = current_month_expenses
    budget_instance.remaining = budget_instance.budget - budget_instance.spent
    return budget_instance


def get_or_create_category(category_name):
    category_obj, _ = models.CategoryModel.objects.get_or_create(category=category_name)
