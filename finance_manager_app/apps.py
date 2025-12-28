from django.apps import AppConfig


class FinanceManagerAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'finance_manager_app'

    def ready(self):
        import finance_manager_app.signals
        from django_celery_beat.models import PeriodicTask, CrontabSchedule

        schedule, created = CrontabSchedule.objects.get_or_create(minute=0, hour=0, day_of_month='*')

        PeriodicTask.objects.get_or_create(
            name = 'check_recurring_bills',
            task = 'finance_manager_app.tasks.send_recurring_bill_warning_email',
            crontab = schedule
        )

        schedule, created = CrontabSchedule.objects.get_or_create(minute=0, hour=0, day_of_month=1)

        PeriodicTask.objects.get_or_create(
            name='reset_budget_email_sent_fields',
            task='finance_manager_app.tasks.reset_budget_email_sent_fields',
            crontab=schedule
        )

        
