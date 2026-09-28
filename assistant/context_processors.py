from urllib.parse import quote

from django.conf import settings


def business_context(request):
    from landing.models import Tariff
    from .models import Workspace

    subscription = None
    admin_users_count = None
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        subscription = Workspace.for_user(user).subscription
        if user.is_superuser:
            admin_users_count = Workspace.objects.count()

    support = settings.SUPPORT_TELEGRAM_USERNAME
    return {
        "BUSINESS_NAME": settings.BUSINESS_NAME,
        "subscription": subscription,
        "SUPPORT_TELEGRAM_USERNAME": support,
        "PRO_PLAN_PRICE": Tariff.pro_price(),
        "FREE_PLAN_QUESTION_LIMIT": Tariff.free_question_limit(),
        "ADMIN_USERS_COUNT": admin_users_count,
        # Telegram'da @support bilan chatni tayyor "Salom, pro obuna olmoqchiman" matni bilan ochadi.
        "PRO_REQUEST_URL": f"https://t.me/{support}?text={quote(settings.PRO_REQUEST_MESSAGE)}",
    }
