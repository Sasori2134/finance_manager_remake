from django.apps import AppConfig


class FinanceManagerAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'finance_manager_app'

    def ready(self):
        import finance_manager_app.signals
