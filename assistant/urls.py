from django.urls import path
from . import views
from . import saidex_views

app_name = "assistant"

urlpatterns = [
    path("login/", views.BusinessLoginView.as_view(), name="login"),
    path("logout/", views.BusinessLogoutView.as_view(), name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("documents/", views.document_list, name="documents"),
    path("documents/<int:pk>/delete/", views.document_delete, name="document_delete"),
    path("documents/<int:pk>/reprocess/", views.document_reprocess, name="document_reprocess"),
    path("prompt/", views.prompt_settings, name="prompt_settings"),
    path("ai/toggle/", views.toggle_ai, name="toggle_ai"),
    path("leads/", views.leads_list, name="leads"),
    path("leads/archive/", views.leads_archive, name="leads_archive"),
    path("leads/export/", views.leads_export, name="leads_export"),
    path("leads/bulk-delete/", views.leads_bulk_delete, name="leads_bulk_delete"),
    path("leads/<int:pk>/status/", views.lead_update_status, name="lead_update_status"),
    path("leads/<int:pk>/archive/", views.lead_archive, name="lead_archive"),
    path("leads/<int:pk>/delete/", views.lead_delete, name="lead_delete"),
    path("groups/", views.groups_list, name="groups"),
    path("groups/<int:pk>/update/", views.group_update, name="group_update"),
    path("telegram/", views.telegram_status, name="telegram_status"),
    path("telegram/disconnect/", views.telegram_disconnect_business, name="telegram_disconnect_business"),
    path("profile/", views.profile, name="profile"),
    path("internal/stats/", views.internal_stats_api, name="internal_stats"),

    # ------------------------------------------------------------------
    # "Saidex" bo'limi — ochiq (public) landing page kontentini (tariflar,
    # qilingan ishlar, mijozlar fikri, sayt sozlamalari) boshqarish. URL
    # yo'li "site/" (pastdagi SUPER ADMIN "saidex/" prefiksi bilan
    # to'qnashmasligi uchun) — sidebar'dagi ko'rinadigan nom esa "Saidex".
    # ------------------------------------------------------------------
    path("site/settings/", saidex_views.saidex_settings, name="saidex_settings"),
    path("site/tariffs/", saidex_views.saidex_tariffs, name="saidex_tariffs"),
    path("site/tariffs/<int:pk>/delete/", saidex_views.saidex_tariff_delete, name="saidex_tariff_delete"),
    path("site/portfolio/", saidex_views.saidex_portfolio, name="saidex_portfolio"),
    path("site/portfolio/<int:pk>/delete/", saidex_views.saidex_portfolio_delete, name="saidex_portfolio_delete"),
    path("site/testimonials/", saidex_views.saidex_testimonials, name="saidex_testimonials"),
    path("site/testimonials/<int:pk>/delete/", saidex_views.saidex_testimonial_delete, name="saidex_testimonial_delete"),

    # ------------------------------------------------------------------
    # SUPER ADMIN — butunlay alohida bo'lim, /saidex/ prefiksi ostida.
    # Business admin panelida bunga hech qanday havola ko'rsatilmaydi.
    # ------------------------------------------------------------------
    path("saidex/login/", views.SuperAdminLoginView.as_view(), name="superadmin_login"),
    path("saidex/logout/", views.SuperAdminLogoutView.as_view(), name="superadmin_logout"),
    path("saidex/", views.superadmin_dashboard, name="superadmin_dashboard"),
    path("saidex/extend/", views.superadmin_extend, name="superadmin_extend"),
    path("saidex/toggle/", views.superadmin_toggle, name="superadmin_toggle"),
    path("saidex/set-model/", views.superadmin_set_model, name="superadmin_set_model"),
    path("saidex/profile/", views.superadmin_profile, name="superadmin_profile"),
    # Telegram AKKAUNT (userbot) ulash
    path("saidex/telegram-account/", views.telegram_account, name="telegram_account"),
    path("saidex/telegram-account/send-code/", views.telegram_send_code, name="telegram_send_code"),
    path("saidex/telegram-account/verify-code/", views.telegram_verify_code, name="telegram_verify_code"),
    path("saidex/telegram-account/verify-password/", views.telegram_verify_password, name="telegram_verify_password"),
    path("saidex/telegram-account/disconnect/", views.telegram_disconnect, name="telegram_disconnect"),
]
