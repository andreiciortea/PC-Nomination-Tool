from django.conf import settings
from django.contrib import admin
from django.shortcuts import render
from django.urls import path, re_path, include
from django.conf.urls import handler400, handler403, handler404, handler500
from django.contrib.auth import views as auth_views
from django.views.static import serve

urlpatterns = [
    re_path("", include("pc_nomination.urls")),
    re_path(r"^admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "password_change/",
        auth_views.PasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "password_change/done/",
        auth_views.PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
]

if settings.DEBUG:
    urlpatterns += [
        re_path(r"^static/(?P<path>.*)$", serve),
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT, "show_indexes": True},
        ),
    ]


# ==================
#    ERROR RENDER
# ==================


def error_render(request, template, status):
    response = render(request, template, locals())
    response.status_code = status
    return response


def error_400_view(request, exception):
    return error_render(request, "400.html", 400)


def error_403_view(request, exception):
    return error_render(request, "403.html", 403)


def error_404_view(request, exception):
    return error_render(request, "404.html", 404)


def error_500_view(request):
    return error_render(request, "500.html", 500)


handler400 = error_400_view
handler403 = error_403_view
handler404 = error_404_view
handler500 = error_500_view
