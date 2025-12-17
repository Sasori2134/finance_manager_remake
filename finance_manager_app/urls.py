from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('test', views.DashboardListView.as_view()),
    path("generate", views.GenerateresetpasswordcodeView.as_view()),
    path("verify", views.VerifyresetpasswordcodeView.as_view()),
    path('reset', views.ResetpasswordView.as_view())
]