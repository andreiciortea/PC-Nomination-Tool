import csv
from copy import deepcopy
from io import TextIOWrapper
from urllib.parse import urlparse

import django
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from pc_nomination.choices import (
    AREA_CHOICES,
    PHD_DATE_CHOICES,
    IMPORT_ACTIONS_CHOICES,
)
from pc_nomination.models import Nomination, EmailAddress


class ProposerForm(forms.Form):
    identifier = forms.CharField(
        max_length=Nomination._meta.get_field("proposer").max_length,
        label_suffix="",
        label="User name",
    )


class NominationForm(forms.Form):
    first_name = forms.CharField(
        max_length=Nomination._meta.get_field("first_name").max_length,
        label="First name",
        label_suffix="",
    )
    last_name = forms.CharField(
        max_length=Nomination._meta.get_field("last_name").max_length,
        label="Last name",
        label_suffix="",
    )
    dblp = forms.URLField(label="DBLP page", label_suffix="")
    full_name = forms.CharField(
        max_length=Nomination._meta.get_field("full_name").max_length,
        label="Full name",
        label_suffix="",
        required=False,
    )
    email = forms.EmailField(label="Email address", label_suffix="")
    areas = forms.MultipleChoiceField(
        choices=AREA_CHOICES, widget=forms.widgets.CheckboxSelectMultiple
    )
    phd_date = forms.ChoiceField(
        label="PhD date",
        choices=[("", "----")] + PHD_DATE_CHOICES,
        widget=forms.Select(),
    )
    comment = forms.CharField(
        widget=forms.Textarea(),
        label_suffix="",
        label="Comments (optional)",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super(NominationForm, self).__init__(*args, **kwargs)
        self.fields["full_name"].widget.attrs["readonly"] = True

    def clean_first_name(self):
        return self.cleaned_data["first_name"].title()

    def clean_last_name(self):
        return self.cleaned_data["last_name"].title()

    def clean_dblp(self):
        dblp_url = self.cleaned_data["dblp"]
        u = urlparse(dblp_url)
        if u.hostname not in ["dblp.org", "www.dblp.org"]:
            raise forms.ValidationError("This URL does not seem to come from DBLP.")
        if dblp_url.endswith(".html"):
            return dblp_url[:-5]
        return dblp_url

    def clean(self):
        cleaned_data = super().clean()

        if (
            "dblp" in cleaned_data
            and Nomination.objects.filter(dblp=cleaned_data["dblp"]).exists()
        ):
            raise forms.ValidationError(
                "Someone with the same DBLP page has already been proposed."
            )

        if (
            "email" in cleaned_data
            and EmailAddress.objects.filter(email=cleaned_data["email"]).exists()
        ):
            raise forms.ValidationError(
                "Someone with the same email address has already been proposed."
            )

        return cleaned_data


class UpdateNominationForm(forms.Form):
    first_name = forms.CharField(
        max_length=Nomination._meta.get_field("first_name").max_length, required=False
    )
    last_name = forms.CharField(
        max_length=Nomination._meta.get_field("last_name").max_length, required=False
    )
    dblp = forms.URLField(required=False)
    full_name = forms.CharField(
        max_length=Nomination._meta.get_field("full_name").max_length, required=False
    )
    emails = forms.CharField(required=False, widget=forms.Textarea())
    areas = forms.MultipleChoiceField(
        choices=AREA_CHOICES,
        required=False,
    )
    proposer = forms.CharField(
        max_length=Nomination._meta.get_field("proposer").max_length,
        required=False,
    )
    phd_date = forms.ChoiceField(
        label="PhD date",
        choices=PHD_DATE_CHOICES,
        widget=forms.Select(),
        required=False,
    )
    invited = forms.BooleanField(required=False)
    accepted = forms.BooleanField(required=False)
    reserve = forms.BooleanField(required=False)
    comment = forms.CharField(
        max_length=5000,
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.nomination = kwargs.pop("nomination")
        self.is_hidden = kwargs.pop("hidden", None)
        if self.nomination:
            kwargs.update(
                initial={
                    "first_name": self.nomination.first_name,
                    "last_name": self.nomination.last_name,
                    "dblp": self.nomination.dblp,
                    "full_name": self.nomination.full_name,
                    "proposer": self.nomination.proposer,
                    "emails": "\n".join(
                        self.nomination.emails.all().values_list("email", flat=True)
                    ),
                    "phd_date": self.nomination.phd_date,
                    "invited": self.nomination.ec_invited,
                    "accepted": self.nomination.ec_accepted,
                    "reserve": self.nomination.in_reserve,
                    "comment": self.nomination.comment,
                }
            )
        super(UpdateNominationForm, self).__init__(*args, **kwargs)
        if self.is_hidden:
            self.fields["first_name"].widget = forms.HiddenInput()
            self.fields["last_name"].widget = forms.HiddenInput()
            self.fields["full_name"].widget = forms.HiddenInput()
            self.fields["dblp"].widget = forms.HiddenInput()
            self.fields["proposer"].widget = forms.HiddenInput()
            self.fields["comment"].widget = forms.HiddenInput()

    def clean_first_name(self):
        return self.cleaned_data["first_name"].title()

    def clean_last_name(self):
        return self.cleaned_data["last_name"].title()

    def clean_dblp(self):
        dblp_url = self.cleaned_data["dblp"]
        if dblp_url:
            u = urlparse(dblp_url)
            if u.hostname not in ["dblp.org", "www.dblp.org"]:
                raise forms.ValidationError("This URL does not seem to come from DBLP.")
        if dblp_url.endswith(".html"):
            return dblp_url[:-5]
        return dblp_url

    def clean_emails(self):
        emails = []
        for e in self.cleaned_data["emails"].split("\n"):
            stripped = e.strip().lower()
            if stripped:
                emails.append(stripped)
        for email in emails:
            try:
                validate_email(email)
            except django.core.exceptions.ValidationError:
                raise forms.ValidationError(f"The email {email} is malformed.")
        return list(set(emails))

    def clean(self):
        cleaned_data = super().clean()
        dblp = cleaned_data.get("dblp", None)
        if (
            dblp
            and dblp != self.nomination.dblp
            and Nomination.objects.filter(dblp=cleaned_data["dblp"]).exists()
        ):
            raise forms.ValidationError(
                "Someone with the same DBLP page has already been proposed."
            )

        emails = cleaned_data.get("emails", None)
        if emails:
            for email in emails:
                if email:
                    existing_email = EmailAddress.objects.filter(
                        email__iexact=email
                    ).exclude(person=self.nomination)
                    if existing_email.exists():
                        existing_email = existing_email.first()
                        if existing_email.person.full_name != self.nomination.full_name:
                            raise forms.ValidationError(
                                f"{existing_email.person.full_name} is "
                                f"already using the email address "
                                f"{existing_email.email}"
                            )
                        # is_subset = True
                        # for e in existing_email.person.emails.all():
                        #     if e.email not in emails:
                        #         is_subset = False
                        #         break

        return cleaned_data


def validate_csv_file(value):
    value = deepcopy(value)
    if not value.name.endswith(".csv"):
        raise forms.ValidationError(
            'Only CSV files are allowed (extension must be ".csv").'
        )
    try:
        csv_reader = csv.reader(TextIOWrapper(value, encoding="utf-8"))
        header = next(csv_reader, None)
        if header is None:
            raise forms.ValidationError("CSV file must have a header row.")
        num_columns = len(header)
        for row in csv_reader:
            if row:
                if len(row) != num_columns:
                    raise forms.ValidationError(
                        "All rows must have the same number of columns as the header."
                    )

    except csv.Error as e:
        raise forms.ValidationError(f"Error reading CSV file: {e}")


class ImportFileForm(forms.Form):
    csv_file = forms.FileField(
        label="Upload CSV File",
        validators=[validate_csv_file],
        widget=forms.ClearableFileInput(attrs={"accept": ".csv"}),
    )
    action = forms.ChoiceField(
        label="Action", label_suffix="", choices=[("", "----")] + IMPORT_ACTIONS_CHOICES
    )

    def clean_csv_file(self):
        uploaded_file = self.cleaned_data["csv_file"]
        if not uploaded_file.name.endswith(".csv"):
            raise forms.ValidationError("Only CSV files are allowed.")
        return uploaded_file


class DuplicateResolverForm(forms.Form):
    first_name = forms.CharField(
        max_length=Nomination._meta.get_field("first_name").max_length,
        required=False,
        widget=forms.HiddenInput(),
    )
    last_name = forms.CharField(
        max_length=Nomination._meta.get_field("last_name").max_length,
        required=False,
        widget=forms.HiddenInput(),
    )
    full_name = forms.CharField(
        max_length=Nomination._meta.get_field("full_name").max_length,
        required=False,
        widget=forms.HiddenInput(),
    )
    dblp = forms.URLField(required=False, widget=forms.HiddenInput())
    emails = forms.CharField(required=False, widget=forms.Textarea())
    areas = forms.MultipleChoiceField(
        choices=AREA_CHOICES,
        required=False,
    )
    proposer = forms.CharField(
        max_length=Nomination._meta.get_field("proposer").max_length,
        required=False,
        widget=forms.HiddenInput(),
    )
    phd_date = forms.ChoiceField(
        label="PhD date",
        choices=[("", "----")] + PHD_DATE_CHOICES,
        widget=forms.Select(),
        required=False,
    )
    ec_invited = forms.BooleanField(required=False)
    ec_accepted = forms.BooleanField(required=False)
    in_reserve = forms.BooleanField(required=False)
    comment = forms.CharField(max_length=5000, required=False, widget=forms.Textarea())

    def clean_emails(self):
        emails = []
        for e in self.cleaned_data["emails"].split("\n"):
            stripped = e.strip().lower()
            if stripped:
                emails.append(stripped)
        for email in emails:
            try:
                validate_email(email)
            except django.core.exceptions.ValidationError:
                raise forms.ValidationError(f"The email {email} is malformed.")
        return list(set(emails))
