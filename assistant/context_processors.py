from urllib.parse import quote

from django.conf import settings


def business_context(request):
    from .models import Workspace

    subscription = None
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        subscription = Workspace.for_user(user).subscription

    support = settings.SUPPORT_TELEGRAM_USERNAME
    return {
        "BUSINESS_NAME": settings.BUSINESS_NAME,
        "subscription": subscription,
        "SUPPORT_TELEGRAM_USERNAME": support,
        "PRO_PLAN_PRICE": settings.PRO_PLAN_PRICE,
        "FREE_PLAN_QUESTION_LIMIT": settings.FREE_PLAN_QUESTION_LIMIT,
        # Telegram'da @support bilan chatni tayyor "Salom, pro obuna olmoqchiman" matni bilan ochadi.
        "PRO_REQUEST_URL": f"https://t.me/{support}?text={quote(settings.PRO_REQUEST_MESSAGE)}",
    }
