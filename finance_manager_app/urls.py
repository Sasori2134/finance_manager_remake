from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/dashboard/', views.DashboardListView.as_view()),
    path("password/generatetoken/", views.GenerateresetpasswordcodeView.as_view()),
    path("password/verifytoken/", views.VerifyresetpasswordcodeView.as_view()),
    path('password/resetpassword/', views.ResetpasswordView.as_view()),
    path('api/register/', views.RegisterView.as_view()),
    path('api/transaction/create/', views.TransactionView.as_view()),
    path('api/transaction/list/', views.TransactionView.as_view()),
    path('api/transaction/update/<int:pk>/', views.TransactionView.as_view()),
    path('api/transaction/delete/<int:pk>/', views.TransactionView.as_view()),
    path('api/monthlybudget/create/', views.Monthly_budgetView.as_view()),
    path('api/monthlybudget/list/', views.Monthly_budgetView.as_view()),
    path('api/monthlybudget/update/<int:pk>/', views.Monthly_budgetView.as_view()),
    path('api/monthlybudget/delete/<int:pk>/', views.Monthly_budgetView.as_view()),
    path('api/recurringbill/create/', views.RecurringBillView.as_view()),
    path('api/recurringbill/list/', views.RecurringBillView.as_view()),
    path('api/recurringbill/update/<int:pk>/', views.RecurringBillView.as_view()),
    path('api/recurringbill/delete/<int:pk>/', views.RecurringBillView.as_view()),
    path('api/changepassword/', views.ChangepasswordView.as_view()),
    path('api/logout/', views.LogoutView.as_view())
]