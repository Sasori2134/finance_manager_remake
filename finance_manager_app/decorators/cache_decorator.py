from rest_framework.response import Response

from finance_manager_app import cache


def cache_set_or_get(key, timeout=300):
    def decorator(func):
        def wrapper(self, request, *args, **kwargs):
            cached = cache.get_cached_data(user_id=request.user.id, key=key)

            if cached:
                return Response(cached)

            response = func(self, request, *args, **kwargs)

            cache.set_cached_data(user_id=request.user.id, key=key, value=response.data)
            return response

        return wrapper

    return decorator
