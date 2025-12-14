from django_redis import get_redis_connection
import simplejson as json
from datetime import date

current_date = date.today()

def set_cached_data(user_id, key, value, period = None, timeout = 120):
    conn = get_redis_connection("default")
    if period:
        key = f"{user_id}:{key}:{current_date.day}:{period}"
    else:
        key = f"{user_id}:{key}:{current_date.month}:{current_date.year}"
    conn.set(key, json.dumps(value, use_decimal = True), timeout)


def get_cached_data(user_id, key, period = None):
    conn = get_redis_connection("default")
    if period:
        key = f"{user_id}:{key}:{current_date.day}:{period}"
    else:
        key = f"{user_id}:{key}:{current_date.month}:{current_date.year}"
    cached = conn.get(key)
    if cached:
        return json.loads(cached, use_decimal=True)
    return None