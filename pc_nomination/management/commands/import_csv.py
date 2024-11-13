import csv

from django.core.management import call_command
from django.utils import timezone
from django.core.management.base import BaseCommand
from pc_nomination.models import Nomination, EmailAddress


class Command(BaseCommand):
    help = "Import persons from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the CSV file")
        parser.add_argument(
            "--reserve",
            action="store_true",
            help="Use to indicate that the persons in the CSV file are on the reserve list.",
        )
        parser.add_argument(
            "--invited",
            action="store_true",
            help="Use to indicate that the persons in the CSV file have been invited to join the PC.",
        )
        parser.add_argument(
            "--accepted",
            action="store_true",
            help="Use to indicate that the persons in the CSV file have accepted the invitation to the PC .",
        )

    def handle(self, *args, **options):
        print(f"Calling the import_csv command with {options}")
        csv_file_path = options["csv_file"]
        number_created = 0
        number_updated = 0

        with open(csv_file_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            if reader:
                first_name_header = ""
                last_name_header = ""
                email_header = ""
                dblp_header = ""
                proposer_header = ""
                for row in reader:
                    for header in row:
                        if header.lower().strip() == "first name":
                            first_name_header = header
                        elif header.lower().strip() == "last name":
                            last_name_header = header
                        elif (
                            header.lower().strip() == "email"
                            or header.lower().strip() == "email addresses"
                        ):
                            email_header = header
                        elif header.lower().strip() == "dblp":
                            dblp_header = header
                        elif header.lower().strip() == "proposer":
                            proposer_header = header
                    break

                for row in reader:
#                    print(f"\tRow is: {row}")
                    first_name = row[first_name_header].strip()
                    last_name = row[last_name_header].strip()
                    dblp = row.get(dblp_header, "").strip()
                    proposer = row.get(proposer_header, "").strip()
                    if not proposer:
                        proposer = row.get("chair", "").strip()
                    emails = [
                        email.strip().lower()
                        for email in row[email_header].split("###")
                    ]

                    existing_person = None
                    existing_person_email = None
                    for email in emails:
                        try:
                            email_obj = EmailAddress.objects.get(email=email)
                            if not existing_person:
                                existing_person = email_obj.person
                                existing_person_email = email_obj.email
                            elif email_obj.person != existing_person:
                                raise ValueError(
                                    f"For these two emails addresses {existing_person_email} and "
                                    f"{email_obj.email} linked to a single CSV row, two different persons "
                                    f"have been found in the database: {existing_person.full_name} (id={existing_person.id}) and "
                                    f"{email_obj.person.full_name} (id={existing_person.id}). This is inconsistent."
                                )
                        except EmailAddress.DoesNotExist:
                            pass
                    if dblp:
                        try:
                            person = Nomination.objects.get(dblp=dblp)
                            if existing_person and existing_person != person:
                                raise ValueError(
                                    f"From the email addresses we found {existing_person.full_name} but given"
                                    f" the DBLP page, we found {person.full_name}. This is inconsistent."
                                )
                        except Nomination.DoesNotExist:
                            pass

                    if existing_person:
#                        self.stdout.write(f"\t\tUpdating person: {existing_person}\n")
                        existing_person.first_name = first_name
                        existing_person.last_name = last_name
                        existing_person.full_name = first_name + " " + last_name
                        if options["reserve"]:
                            existing_person.in_reserve = True
                        if options["invited"]:
                            existing_person.ec_invited = True
                        if options["accepted"]:
                            existing_person.ec_accepted = True
                        existing_person.save()
                        for email in emails:
                            try:
                                EmailAddress.objects.get(email=email)
                            except EmailAddress.DoesNotExist:
                                EmailAddress.objects.create(
                                    person=existing_person, email=email
                                )
                        number_updated += 1
                    else:
#                       self.stdout.write(f"\t\tCreating a new person for {first_name} {last_name}\n")
                        person = Nomination.objects.create(
                            first_name=first_name,
                            last_name=last_name,
                            full_name=first_name + " " + last_name,
                            dblp=dblp,
                            proposer=proposer,
                            in_reserve=options["reserve"],
                            ec_invited=options["invited"],
                            ec_accepted=options["accepted"],
                            added_date=timezone.now(),
                        )
                        for email in emails:
                            EmailAddress.objects.create(person=person, email=email)
                        number_created += 1

        call_command("detect_duplicates")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully imported "
                f"{number_updated + number_created} persons: "
                f"{number_updated} updates and {number_created} "
                f"creations"
            )
        )
