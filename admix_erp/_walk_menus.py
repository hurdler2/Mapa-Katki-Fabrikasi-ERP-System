"""Her demo kullanıcı için sidebar menüsündeki linkleri sırayla gez ve HTTP status kaydet.
403 alan sayfaları raporla."""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from portal.menu import filter_menu_for


ROLES_TO_TEST = [
    "gm.director",
    "tm.director",
    "op.manager",
    "qa.manager",
    "acc.manager",
    "lab.tech",
    "shift.supervisor",
    "warehouse.chief",
    "purchase.officer",
    "it.admin",
]


def resolve_url(item):
    """Special menu entries: admin_link, bi_link, iso_link."""
    url = item["url"]
    if url == "admin_link":
        return "/admin/"
    try:
        return reverse(url)
    except Exception as e:
        return None


for username in ROLES_TO_TEST:
    try:
        u = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"MISSING USER: {username}")
        continue

    c = Client()
    ok = c.login(username=username, password="Demo123!")
    if not ok:
        print(f"LOGIN FAILED: {username}")
        continue

    menu = filter_menu_for(u)
    print(f"\n=== {username} ({len(menu)} section) ===")

    for section in menu:
        for item in section["items"]:
            path = resolve_url(item)
            if path is None:
                print(f"  [-] {item['url']}: unresolvable")
                continue
            try:
                resp = c.get(path, follow=False)
                status = resp.status_code
            except Exception as e:
                status = f"EXC {type(e).__name__}"
            marker = "OK " if status == 200 else ("REDIR " if status in (301, 302) else "!!!")
            print(f"  [{marker}] {status} {path}  <{item['label']}>")

print("\nDone.")
