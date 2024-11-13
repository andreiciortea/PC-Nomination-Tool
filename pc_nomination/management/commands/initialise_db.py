from django.core.management.base import BaseCommand

from pc_nomination.choices import AREA_CHOICES
from pc_nomination.models import Area


class Command(BaseCommand):
    help = "Initialise the database"

    def handle(self, *args, **options):
        for area in AREA_CHOICES:
            Area.objects.update_or_create(slug_name=area[0], name=area[1])
