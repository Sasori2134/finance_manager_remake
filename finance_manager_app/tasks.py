from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Monthly_budget, Recurring_bill
from django.db.models import Sum, Value, F, Q, DecimalField
from django.db.models.functions import Coalesce
from datetime import date, timedelta
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


@shared_task
def send_recurring_bill_warning_email():
    bills = Recurring_bill.objects.filter(payment_due = (date.today() + timedelta(days=1)).day).select_related("user")
    for bill in bills:
        subject = "Payment Due"
        message = f"Wanted to remind you that your bill for {bill.item} is due tomorrow \n\n Thank you for using my finance manager :)"
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [bill.user.email], fail_silently=False)
    return 1


@shared_task
def send_password_change_notification(user_email):
    subject = "Password change"
    message = "Hello just wanted to let you know that your password has been changed if it wasn't you please report it to our customer support"
    return send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_email], fail_silently=False)