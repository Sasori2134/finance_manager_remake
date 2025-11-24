from django.dispatch import receiver
from django.db.models.signals import post_delete, post_save
from .models import Transaction
from django_redis import get_redis_connection



@receiver([post_save, post_delete], sender = Transaction)
def delete_cached_data(sender, instance, **kwargs):
    conn = get_redis_connection("default")
    pattern = f"{instance.user.id}:dashboard:*"
    for key in conn.scan_iter(pattern):
        conn.delete(key)