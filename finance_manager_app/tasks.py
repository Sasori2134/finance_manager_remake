from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Monthly_budget
from django.db.models import Sum, Value, F, Q, DecimalField
from django.db.models.functions import Coalesce
from datetime import date
from .serializers import BudgetSerializer



@shared_task
def send_budget_warning_email(user, category, user_email):
    transaction_filter = (
        Q(category__transaction__user = user) &
        Q(category__transaction__created_at__month = date.today().month) &
        Q(category__transaction__created_at__year = date.today().year) &
        Q(category__transaction__transaction_type = 'expense')
    )
    budget = Monthly_budget.objects.filter(user = user, category__category = category).select_related('category').annotate(
    spent = Sum(Coalesce("category__transaction__price", Value(0, output_field=DecimalField())), filter=transaction_filter), remaining = F('budget')-F('spent'))[0]
    serialized = BudgetSerializer(budget)
    remaining = float(serialized.data.get('remaining'))
    subject = "Budget warning"
    if remaining < 0:
        message = f"You exceeded your monthly budget by {abs(remaining)}"
    elif remaining == 0:
        message = f"You have 0 dollars left in your budget"
    elif remaining <= float(serialized.data.get('budget')) * 0.2:
        message = f"You exceeded 80% of your monthly budget"
    else:
        return None
    return send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_email], fail_silently=False)
    
