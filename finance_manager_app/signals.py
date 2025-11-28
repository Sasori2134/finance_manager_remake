from django.dispatch import receiver
from django.db.models.signals import post_delete, post_save
from .models import Transaction
from django_redis import get_redis_connection
from .tasks import send_budget_warning_email



@receiver([post_save, post_delete], sender = Transaction)
def delete_cached_data(sender, instance, **kwargs):
    conn = get_redis_connection("default")
    pattern = f"{instance.user.id}:*"
    for key in conn.scan_iter(pattern):
        conn.delete(key)

@receiver(post_save, sender=Transaction)
def email_notification(sender, instance, created, **kwargs):
    send_budget_warning_email.delay(user=instance.user_id, category=instance.category.category, user_email=instance.user.email)