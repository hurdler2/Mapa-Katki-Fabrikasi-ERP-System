from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import include, path


def _admin_or_it(request):
    """Sadece superuser ve IT_ADMIN grubuna dahil kullanıcılar Django Admin'e girebilir.
    Diğer roller portal üzerinden çalışır."""
    return request.user.is_superuser or request.user.groups.filter(name="IT_ADMIN").exists()


class RestrictedAdminSite(admin.AdminSite):
    def has_permission(self, request):
        if not request.user.is_active:
            return False
        # Django admin'in kendi has_permission'ı is_staff kontrol eder;
        # ek olarak superuser veya IT_ADMIN dışı staff kullanıcılar için engelle.
        if not request.user.is_staff:
            return False
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(name="IT_ADMIN").exists()


# admin.site'ı sarmalıyoruz — mevcut register'lar korunuyor
admin.site.__class__.has_permission = RestrictedAdminSite.has_permission


urlpatterns = [
    path("", lambda r: HttpResponseRedirect("/portal/") if r.user.is_authenticated
                       else HttpResponseRedirect("/login/?next=/portal/")),
    path("login/", auth_views.LoginView.as_view(
        template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/login/"),
         name="logout"),
    path("portal/", include("portal.urls")),
    path("admin/", admin.site.urls),
    path("reporting/", include("reporting.urls")),
    path("accounting/", include("accounting.urls")),
    path("notifications/", include("notifications.urls")),
    path("api/v1/", include("api.urls")),
    path("analytics/", include("analytics.urls")),
]
