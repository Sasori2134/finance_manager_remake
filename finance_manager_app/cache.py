from django_redis import get_redis_connection
import simplejson as json


def set_cached_data(user_id, key, value, period, timeout = 120):
    conn = get_redis_connection("default")
    key = f"{user_id}:{key}:{period}"
    conn.set(key, json.dumps(value, use_decimal = True), timeout)


def get_cached_data(user_id, key, period):
    conn = get_redis_connection("default")
    key = f"{user_id}:{key}:{period}"
    cached = conn.get(key)
    if cached:
        return json.loads(cached, use_decimal=True)
    return None