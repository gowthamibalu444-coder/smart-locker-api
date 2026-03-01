"""
Management command: create_admin
Creates an admin-role user from the command line.

Usage:
    python manage.py create_admin --email admin@example.com --name "Admin User" --password secret123
"""
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Create an admin-role user account."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, type=str, help="Admin email address")
        parser.add_argument("--name", required=True, type=str, help="Admin full name")
        parser.add_argument("--password", required=True, type=str, help="Admin password")

    def handle(self, *args, **options):
        email = options["email"]
        name = options["name"]
        password = options["password"]

        if User.objects.filter(email=email).exists():
            raise CommandError(f"A user with email '{email}' already exists.")

        user = User.objects.create_superuser(email=email, name=name, password=password)
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Admin user '{user.name}' created successfully with email: {user.email}"
            )
        )
