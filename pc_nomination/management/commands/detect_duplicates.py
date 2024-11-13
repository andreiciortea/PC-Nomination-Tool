from django.core.management.base import BaseCommand
from django.db.models import Count
from pc_nomination.models import Nomination, EmailAddress, Duplicate


class Command(BaseCommand):
    help = "Detect duplicate nominations and store conflicts in the database"

    def handle(self, *args, **options):
        duplicates = (
            Nomination.objects.values("full_name", "dblp")
            .annotate(Count("id"))
            .order_by()
            .filter(id__count__gt=1)
        )

        for duplicate in duplicates:
            persons = Nomination.objects.filter(
                full_name=duplicate["full_name"], dblp=duplicate["dblp"]
            )

            if len(persons) > 1:
                if (
                    not Duplicate.objects.filter(
                        nomination1=persons[0], nomination2=persons[1]
                    ).exists()
                    and not Duplicate.objects.filter(
                        nomination1=persons[1], nomination2=persons[0]
                    ).exists()
                ):
                    duplicate_obj = Duplicate.objects.create(
                        nomination1=persons[0],
                        nomination2=persons[1],
                        reason="Automatic search for duplicate based on similar full names",
                    )
                    self.stdout.write(
                        self.style.ERROR(
                            f"Duplicate detected and stored: {duplicate_obj}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS("Duplicates have been detected and stored.")
        )
