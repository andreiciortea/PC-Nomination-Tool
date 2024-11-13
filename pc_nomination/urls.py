
from django.urls import re_path

from . import views

app_name = "programcommittee"
urlpatterns = [
    re_path(r"^$", views.index, name="index"),
    re_path(r"^logout$", views.logout, name="logout"),
    re_path(r"^manage/?$", views.manage, name="manage"),
    re_path(r"^manage/duplicates/?$", views.duplicate_index, name="duplicate_index"),
    re_path(
        r"^manage/duplicates/(?P<duplicate_id>[0-9+]+)/?$",
        views.duplicate,
        name="duplicate",
    ),
    re_path(r"^manage/export/csv/?$", views.export_csv, name="export_csv"),
    re_path(r"^manage/export/ec/?$", views.export_ec, name="export_ec"),
    re_path(r"^api/check_entry/?$", views.check_entry, name="check_entry"),
]
