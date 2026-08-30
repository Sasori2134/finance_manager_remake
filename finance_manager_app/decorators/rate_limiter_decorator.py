from typing import Callable

from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.response import Response


def rate_limiter(
    key, limit=3, timeout=300
) -> Callable[..., Callable[[], Response | None]]:

    def decorator(func) -> Callable[[], Response | None]:
        def wrapper(self, request, *args, **kwargs) -> Response | None:
            conn = get_redis_connection("default")

            email = request.data.get("email")
            full_key = f"{email}:{key}"

            if conn.incr(full_key, 1) >= limit:
                return Response(
                    {"detail": "Too many attempts please try again in 15 minutes"},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            conn.expire(full_key, timeout)
            return func(self, request, *args, **kwargs)

        return wrapper

    return decorator
