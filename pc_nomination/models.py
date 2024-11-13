from django.db import models

from pc_nomination.choices import AREA_CHOICES, PHD_DATE_CHOICES


class Area(models.Model):
    slug_name = models.SlugField(max_length=50, choices=AREA_CHOICES, unique=True)
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Nomination(models.Model):
    first_name = models.CharField(max_length=50, verbose_name="first name")
    last_name = models.CharField(max_length=50, verbose_name="last name")
    full_name = models.CharField(max_length=100, verbose_name="full name")
    dblp = models.URLField(verbose_name="DBLP url")
    added_date = models.DateTimeField()
    proposer = models.CharField(
        max_length=50, verbose_name="Proposer identifier", blank=True, null=True
    )
    areas = models.ManyToManyField(
        Area,
        related_name="persons",
        blank=True,
    )
    phd_date = models.CharField(
        verbose_name="PhD delivery date",
        max_length=50,
        choices=PHD_DATE_CHOICES,
        blank=True,
        null=True,
    )
    comment = models.TextField()
    ec_invited = models.BooleanField(
        verbose_name="Invited on EasyChair", blank=True, null=True, default=False
    )
    ec_accepted = models.BooleanField(
        verbose_name="Invitation accepted on EasyChair",
        blank=True,
        null=True,
        default=False,
    )
    in_reserve = models.BooleanField(
        verbose_name="In the reserve list", blank=True, null=True, default=False
    )

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name + " - " + self.dblp


class EmailAddress(models.Model):
    email = models.EmailField()
    person = models.ForeignKey(
        Nomination, related_name="emails", on_delete=models.CASCADE
    )

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return f"{self.person.full_name} - {self.email}"


class Duplicate(models.Model):
    nomination1 = models.ForeignKey(
        Nomination, on_delete=models.CASCADE, related_name="conflicts_as_1"
    )
    nomination2 = models.ForeignKey(
        Nomination, on_delete=models.CASCADE, related_name="conflicts_as_2"
    )
    reason = models.TextField()
    ignored = models.BooleanField(default=False)

    class Meta:
        ordering = ["nomination1", "nomination2"]

    def __str__(self):
        return f"{self.nomination1.full_name} - {self.nomination2.full_name}"
