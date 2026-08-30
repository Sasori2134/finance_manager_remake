from debug_toolbar.toolbar import debug_toolbar_urls
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

router = SimpleRouter()
router.register(r"transactions", views.TransactionViewSet, basename="transactions")
router.register(r"budgets", views.MonthlyBudgetViewSet, basename="budgets")
router.register(
    r"recurring-bills", views.RecurringBillViewSet, basename="recurring-bills"
)


urlpatterns = (
    [
        path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
        path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
        path("dashboard/", views.DashboardView.as_view()),
        path("auth/forgot-password/", views.ForgotPasswordView.as_view()),
        path("auth/new-password/", views.NewPasswordView.as_view()),
        path("api/register/", views.RegisterView.as_view()),
        path("api/logout/", views.LogoutView.as_view()),
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/schema/swagger-ui/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
    ]
    + router.urls
    + debug_toolbar_urls()
)
