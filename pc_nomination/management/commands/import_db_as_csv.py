import csv

from django.core.management.base import BaseCommand
from pc_nomination.models import Nomination, EmailAddress, Area


class Command(BaseCommand):
    help = (
        "Copy the database of another instance by importing the CSV generated when using the"
        " CSV export option of the website."
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the CSV file")

    def handle(self, *args, **options):
        print(f"Calling the import_csv command with {options}")
        csv_file_path = options["csv_file"]

        with open(csv_file_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            if reader:
                for row in reader:
                    first_name = row["First Name"].strip()
                    last_name = row["Last Name"].strip()
                    full_name = row["Full Name"].strip()
                    dblp = row["DBLP"].strip()
                    phd_date = row["PhD Date"]
                    proposer = row["Proposer"]
                    comment = row["Proposer Comment"]
                    added_date = row["Added Date"]
                    invited = row["Invited EC"] == "True"
                    accepted = row["Accepted EC"] == "True"
                    reserve = row["Reserve"] == "True"
                    emails = [
                        email.strip().lower()
                        for email in row["Email Addresses"].split("###")
                    ]
                    areas = [
                        area.strip()
                        for area in row["Areas"].split("###")
                        if area.strip()
                    ]

                    self.stdout.write(
                        f"\t\tCreating a new person for {first_name} {last_name}\n"
                    )
                    parameters = {
                        "first_name": first_name,
                        "last_name": last_name,
                        "full_name": full_name,
                        "phd_date": phd_date,
                        "proposer": proposer,
                        "comment": comment,
                        "added_date": added_date,
                        "in_reserve": reserve,
                        "ec_invited": invited,
                        "ec_accepted": accepted,
                    }
                    if dblp:
                        person, _ = Nomination.objects.update_or_create(
                            dblp=dblp, defaults=parameters
                        )
                    else:
                        person = Nomination.objects.create(dblp=dblp, **parameters)
                    for email in emails:
                        EmailAddress.objects.create(person=person, email=email)
                    for area in areas:
                        person.areas.add(Area.objects.get(name=area))

        self.stdout.write(self.style.SUCCESS(f"Successfully imported"))
