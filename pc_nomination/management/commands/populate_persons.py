from django.core.management.base import BaseCommand

from pc_nomination.models import Area, Nomination, EmailAddress

import string
import random


def random_email(prefix, char_num):
    domain = random.choice(
        ["gmail.com", "hotmail.fr", "outlook.com", "proton.de", "msn.net"]
    )
    return (
        prefix
        + "".join(random.choice(string.ascii_letters) for _ in range(char_num))
        + "@"
        + domain
    )


class Command(BaseCommand):
    help = "Initialise the database"

    def handle(self, *args, **options):
        ha, _ = Nomination.objects.update_or_create(
            first_name="Haris",
            last_name="Aziz",
            dblp="https://dblp.org/pid/67/2967.html",
        )
        ha.areas.add(Area.objects.get(slug_name="multiagent_systems"))
        EmailAddress.objects.create(person=ha, email=random_email(ha.first_name, 7))

        ue, _ = Nomination.objects.update_or_create(
            first_name="Ulle",
            last_name="Endriss",
            dblp="https://dblp.org/pid/e/UlrichEndriss.html",
        )
        ue.areas.add(Area.objects.get(slug_name="multiagent_systems"))
        ue.areas.add(Area.objects.get(slug_name="knowledge_representation_reasoning"))
        EmailAddress.objects.create(person=ue, email=random_email(ue.first_name, 7))
