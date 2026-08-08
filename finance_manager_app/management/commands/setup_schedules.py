from typing import Any

from django.core.management.base import BaseCommand, CommandError

from finance_manager_app.schedule import setup_schedule


class Command(BaseCommand):
    help = "Command for schedule setup used for setting up creating schedules after running migrations"

    def handle(self, *args: Any, **options: Any) -> str | None:
        try:
            setup_schedule()
        except Exception as e:
            raise CommandError(f"Unable to setup schedule.\n\n Error: {e}")

        self.stdout.write(self.style.SUCCESS("schedule setup successful"))
