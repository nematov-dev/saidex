from django.conf import settings


def business_context(request):
    from .models import ProjectSubscription

    return {
        "BUSINESS_NAME": settings.BUSINESS_NAME,
        "subscription": ProjectSubscription.get_solo(),
    }
