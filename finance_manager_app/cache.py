from django_redis import get_redis_connection
import simplejson as json


def set_cached_data(user_id, key, value, period = None, timeout = 120):
    conn = get_redis_connection("default")
    if period:
        key = f"{user_id}:{key}:{period}"
    else:
        key = f"{user_id}:{key}"
    conn.set(key, json.dumps(value, use_decimal = True), timeout)


def get_cached_data(user_id, key, period = None):
    conn = get_redis_connection("default")
    if period:
        key = f"{user_id}:{key}:{period}"
    else:
        key = f"{user_id}:{key}"
    cached = conn.get(key)
    if cached:
        return json.loads(cached, use_decimal=True)
    return None