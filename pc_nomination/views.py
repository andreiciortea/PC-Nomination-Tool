import csv
import os.path
import tempfile
from io import StringIO

from datetime import datetime
from urllib.parse import urlparse

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.core.management import call_command
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, HttpResponse
from django.utils.dateparse import parse_date
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth import logout as django_logout

from .forms import (
    NominationForm,
    ProposerForm,
    ImportFileForm,
    UpdateNominationForm,
    DuplicateResolverForm,
)
from .models import Nomination, EmailAddress, Area, Duplicate


def logout(request):
    django_logout(request)
    return redirect("programcommittee:index")


# ==================
#    AJAX QUERIES
# ==================


def check_entry(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name", "")
        first_name = " ".join(first_name.split())
        last_name = request.POST.get("last_name", "")
        last_name = " ".join(last_name.split())
        email = request.POST.get("email", "")
        dblp = request.POST.get("dblp", "")
        # print(f"Received query: {email}, {dblp} for {first_name} {last_name}")

        if len(first_name) + len(last_name) + len(email) + len(dblp) > 2:
            similar_persons = None
            if email:
                similar_emails_pks = EmailAddress.objects.filter(
                    email__iexact=email
                ).values_list("pk", flat=True)
                similar_persons = Nomination.objects.filter(
                    emails__in=similar_emails_pks
                )
                # print(f"Emails: {similar_persons}")
            if not similar_persons:
                if dblp:
                    similar_persons = Nomination.objects.filter(dblp__iexact=dblp)
                    # print(f"DBLP: {similar_persons}")
                if not similar_persons and len(last_name) + len(first_name) > 2:
                    first_name_query = None
                    last_name_query = None
                    if first_name:
                        first_name_query = (
                            Q(first_name__icontains=first_name)
                            | Q(first_name__istartswith=first_name)
                            | Q(last_name__icontains=first_name)
                            | Q(last_name__istartswith=first_name)
                        )
                    if last_name:
                        last_name_query = (
                            Q(first_name__icontains=last_name)
                            | Q(first_name__istartswith=last_name)
                            | Q(last_name__icontains=last_name)
                            | Q(last_name__istartswith=last_name)
                        )
                    if first_name_query or last_name_query:
                        if first_name_query and last_name_query:
                            name_query = first_name_query & last_name_query
                        elif first_name_query:
                            name_query = first_name_query
                        else:
                            name_query = last_name_query
                        similar_persons = Nomination.objects.filter(name_query)
                        # print(f"Name: {similar_persons}")
            if similar_persons:
                return_val = set()
                for p in similar_persons:
                    url_parse = urlparse(p.dblp)
                    if url_parse.hostname == "dblp.org":
                        return_val.add(
                            f'{p.full_name} - <a href="{p.dblp}">{p.dblp}</a>'
                        )
                    else:
                        return_val.add(f"{p.first_name} {p.last_name}")
                return JsonResponse({"similar_persons": list(return_val)})
        return JsonResponse({"notfound": "No one found", "similar_persons": []})
    return JsonResponse({"error": "Invalid request"})


def index(request):
    if request.GET.get("logout", None):
        request.session.flush()
        return redirect("programcommittee:index")

    context = {}

    add_person_form = NominationForm()
    proposer_id_form = None
    if request.method == "POST":
        if "proposer_id_form" in request.POST:
            proposer_id_form = ProposerForm(request.POST)
            if proposer_id_form.is_valid():
                request.session["_proposer_id"] = proposer_id_form.cleaned_data[
                    "identifier"
                ]
        elif "add_person_form" in request.POST:
            add_person_form = NominationForm(request.POST)
            if add_person_form.is_valid():
                full_name = add_person_form.cleaned_data["full_name"]
                first_name = add_person_form.cleaned_data["first_name"]
                last_name = add_person_form.cleaned_data["last_name"]
                split_full_name = [s.lower() for s in full_name.split(" ")]
                if (
                    last_name.lower() not in split_full_name
                    or first_name.lower() not in split_full_name
                ):
                    full_name_split = full_name.split(" ")
                    first_name = full_name_split[0]
                    last_name = " ".join(full_name_split[1:])
                nomination = Nomination.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    full_name=full_name,
                    dblp=add_person_form.cleaned_data["dblp"],
                    proposer=request.session.get("_proposer_id"),
                    comment=add_person_form.cleaned_data["comment"],
                    phd_date=add_person_form.cleaned_data["phd_date"],
                    added_date=datetime.now(),
                )
                try:
                    email = EmailAddress.objects.create(
                        person=nomination,
                        email=add_person_form.cleaned_data["email"].lower(),
                    )
                    try:
                        for area in add_person_form.cleaned_data["areas"]:
                            nomination.areas.add(Area.objects.get(slug_name=area))
                        nomination.save()
                        context["added_nomination"] = nomination
                    except Exception as e:
                        email.delete()
                        raise e
                except Exception as e:
                    nomination.delete()
                    raise e
                add_person_form = NominationForm()
        else:
            raise Http404("POST request but unknown form type.")

    proposer_id = request.session.get("_proposer_id", None)
    context["proposer_id"] = proposer_id

    if proposer_id:
        proposed = Nomination.objects.filter(proposer=proposer_id)
        context["proposed"] = proposed
    else:
        proposer_id_form = ProposerForm()

    context["proposer_id_form"] = proposer_id_form
    context["add_person_form"] = add_person_form
    return render(request, "programcommittee/index.html", context)


@login_required
@staff_member_required
def manage(request):
    context = {}
    if request.method == "POST" and "csv_form" in request.POST:
        csv_form = ImportFileForm(request.POST, request.FILES)
        if csv_form.is_valid():
            uploaded_file = request.FILES["csv_file"]
            file_name = FileSystemStorage(location=tempfile.gettempdir()).save(
                uploaded_file.name, uploaded_file
            )
            params = {"accepted": False, "invited": False, "reserve": False}
            action = csv_form.cleaned_data["action"]
            if action in ["invited", "accepted"]:
                params["invited"] = True
            if action == "accepted":
                params["accepted"] = True
            if action == "reserve":
                params["reserve"] = True
            try:
                out = StringIO()
                params["stdout"] = out
                call_command(
                    "import_csv",
                    os.path.join(tempfile.gettempdir(), file_name),
                    **params,
                )
                context["command_log"] = out.getvalue()
            except Exception as e:
                context["command_error"] = e.__repr__()
    else:
        csv_form = ImportFileForm()
    context["csv_form"] = csv_form

    all_nominations = Nomination.objects.all().prefetch_related("emails")
    nomination_forms = []
    for nomination in all_nominations:
        if request.method == "POST" and f"update_nom_{nomination.id}" in request.POST:
            nom_up_form = UpdateNominationForm(
                request.POST, nomination=nomination, hidden=True, prefix=nomination.id
            )
            if nom_up_form.is_valid():
                nomination.first_name = nom_up_form.cleaned_data["first_name"]
                nomination.last_name = nom_up_form.cleaned_data["last_name"]
                nomination.full_name = nom_up_form.cleaned_data["full_name"]
                nomination.dblp = nom_up_form.cleaned_data["dblp"]
                nomination.proposer = nom_up_form.cleaned_data["proposer"]
                nomination.ec_invited = nom_up_form.cleaned_data["invited"]
                nomination.ec_accepted = nom_up_form.cleaned_data["accepted"]
                nomination.in_reserve = nom_up_form.cleaned_data["reserve"]
                nomination.comment = nom_up_form.cleaned_data["comment"]
                nomination.save()
                EmailAddress.objects.filter(person=nomination).delete()
                for email in nom_up_form.cleaned_data["emails"]:
                    EmailAddress.objects.create(email=email, person=nomination)
                nomination_forms.append(
                    UpdateNominationForm(
                        nomination=nomination, hidden=True, prefix=nomination.id
                    )
                )
                context["updated_nomination_full_name"] = nomination.full_name
            else:
                nomination_forms.append(nom_up_form)
                context["form_with_errors"] = nom_up_form
        elif request.method == "POST" and f"delete_nom_{nomination.id}" in request.POST:
            context["deleted_nomination_name"] = nomination.full_name
            nomination.delete()
        else:
            nomination_forms.append(
                UpdateNominationForm(
                    nomination=nomination, hidden=True, prefix=nomination.id
                )
            )
    context["nomination_forms"] = nomination_forms

    context["num_duplicates"] = Duplicate.objects.filter(ignored=False).count()
    if request.method == "POST" and "check_duplicates" in request.POST:
        call_command("detect_duplicates")
        context["duplicate_check_run"] = True

    return render(request, "programcommittee/manage.html", context)


@login_required
@staff_member_required
def duplicate_index(request):
    duplicates = Duplicate.objects.filter(ignored=False)
    if len(duplicates) == 0:
        return render(request, "programcommittee/duplicates_none.html")
    return redirect(
        "programcommittee:duplicate",
        duplicate_id=duplicates.first().id,
    )


@login_required
@staff_member_required
def duplicate(request, duplicate_id):
    d = get_object_or_404(Duplicate, id=duplicate_id, ignored=False)

    context = {"duplicate": d}

    if request.method == "POST":
        if "resolve_duplicates" in request.POST:
            resolver_form = DuplicateResolverForm(request.POST)
            if resolver_form.is_valid():
                nomination1 = d.nomination1
                nomination2 = d.nomination2
                nomination1.delete()
                nomination2.delete()
                new_nomination = Nomination.objects.create(
                    first_name=resolver_form.cleaned_data["first_name"],
                    last_name=resolver_form.cleaned_data["last_name"],
                    full_name=resolver_form.cleaned_data["full_name"],
                    dblp=resolver_form.cleaned_data["dblp"],
                    added_date=datetime.now(),
                    proposer=resolver_form.cleaned_data["proposer"],
                    phd_date=resolver_form.cleaned_data["phd_date"],
                    comment=resolver_form.cleaned_data["comment"],
                    ec_invited=resolver_form.cleaned_data["ec_invited"],
                    ec_accepted=resolver_form.cleaned_data["ec_accepted"],
                    in_reserve=resolver_form.cleaned_data["in_reserve"],
                )
                for area_slug in resolver_form.cleaned_data["areas"]:
                    new_nomination.areas.add(Area.objects.get(slug_name=area_slug))
                new_nomination.save()
                for email in resolver_form.cleaned_data["emails"]:
                    EmailAddress.objects.create(email=email, person=new_nomination)
                return redirect("programcommittee:duplicate_index")
            else:
                context["resolver_form"] = resolver_form
        elif "ignore_duplicates" in request.POST:
            d.ignored = True
            d.save()
            return redirect("programcommittee:duplicate_index")

    if "resolver_form" not in context:
        resolver = {
            "first_name": d.nomination1.first_name,
            "last_name": d.nomination1.last_name,
            "full_name": d.nomination1.full_name,
            "dblp": (
                d.nomination2.dblp
                if len(d.nomination1.dblp) == 0
                else d.nomination1.dblp
            ),
            "emails": "\n".join(
                str(e.email)
                for e in list(d.nomination1.emails.all())
                + list(d.nomination2.emails.all())
            ),
            "areas": [
                area.slug_name
                for area in list(d.nomination1.areas.all())
                + list(d.nomination2.areas.all())
            ],
            "proposer": (
                d.nomination2.proposer
                if len(d.nomination1.proposer) == 0
                else d.nomination1.proposer
            ),
            "phd_date": (
                d.nomination2.phd_date
                if d.nomination1.phd_date is None
                else d.nomination1.phd_date
            ),
            "comment": d.nomination1.comment + "\n" + d.nomination2.comment,
            "ec_invited": d.nomination1.ec_invited or d.nomination2.ec_invited,
            "ec_accepted": d.nomination1.ec_accepted or d.nomination2.ec_accepted,
            "in_reserve": d.nomination1.in_reserve or d.nomination2.in_reserve,
        }
        for nom in [d.nomination1, d.nomination2]:
            if nom.first_name + " " + nom.last_name == nom.full_name:
                resolver["first_name"] = nom.first_name
                resolver["last_name"] = nom.last_name
                resolver["full_name"] = nom.full_name
        context["resolver_form"] = DuplicateResolverForm(initial=resolver)

    return render(request, "programcommittee/duplicate_resolver.html", context)


def filter_nominations(request):
    in_reserve = request.GET.get("in_reserve", None)
    ec_invited = request.GET.get("ec_invited", None)
    ec_accepted = request.GET.get("ec_accepted", None)
    added_date_before = request.GET.get("added_date_before", None)
    added_date_after = request.GET.get("added_date_after", None)

    filter_params = {}
    if in_reserve:
        filter_params["in_reserve"] = in_reserve.lower() == "true"
    if ec_invited:
        filter_params["ec_invited"] = ec_invited.lower() == "true"
    if ec_accepted:
        filter_params["ec_accepted"] = ec_accepted.lower() == "true"
    if added_date_before:
        filter_params["added_date__lt"] = parse_date(added_date_before)
    if added_date_after:
        filter_params["added_date__gt"] = parse_date(added_date_after)

    return Nomination.objects.filter(**filter_params)


@login_required
@staff_member_required
def export_csv(request):
    nominations = filter_nominations(request)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="nominations.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "First Name",
            "Last Name",
            "Full Name",
            "Email Addresses",
            "DBLP",
            "PhD Date",
            "Areas",
            "Proposer",
            "Proposer Comment",
            "Added Date",
            "Invited EC",
            "Accepted EC",
            "Reserve",
        ]
    )
    for nomination in nominations:
        areas = " ### ".join([area.name for area in nomination.areas.all()])
        emails = " ### ".join([email.email for email in nomination.emails.all()])
        writer.writerow(
            [
                nomination.first_name,
                nomination.last_name,
                nomination.full_name,
                emails,
                nomination.dblp,
                nomination.phd_date,
                areas,
                nomination.proposer,
                nomination.comment,
                nomination.added_date,
                nomination.ec_invited,
                nomination.ec_accepted,
                nomination.in_reserve,
            ]
        )
    return response


@login_required
@staff_member_required
def export_ec(request):
    nominations = filter_nominations(request)
    txt_content = ""
    for nomination in nominations:
        email = None
        if nomination.emails.first():
            email = nomination.emails.first().email
        txt_content += f'"{nomination.first_name}" "{nomination.last_name}" <{email}>\n'
    response = HttpResponse(txt_content, content_type="text/plain")
    response["Content-Disposition"] = 'attachment; filename="nomination_easychair.txt"'
    return response
