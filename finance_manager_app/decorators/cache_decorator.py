from typing import Callable

from rest_framework.response import Response

from finance_manager_app import cache


def cache_set_or_get(key, timeout=300) -> Callable[..., Callable[..., Response]]:
    def decorator(func) -> Callable[..., Response]:
        def wrapper(self, request, *args, **kwargs) -> Response:
            full_key = f"{request.user.id}:{key}:{":".join([f'{k}-{v}' for k,
                                                           v in request.query_params.items()])}"
            cached = cache.get_cached_data(user_id=request.user.id, key=full_key)

            if cached:
                return Response(cached)

            response = func(self, request, *args, **kwargs)

            cache.set_cached_data(
                user_id=request.user.id,
                key=full_key,
                value=response.data,
                timeout=timeout,
            )
            return response

        return wrapper

    return decorator
