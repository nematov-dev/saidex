"""
Foydalanuvchilarning Pro obunasi tugashiga oz qolganda super adminga (siz) Telegram orqali ogohlantirish yuboradi.

Kunlik cron sifatida ishlatilishi kerak, masalan:
    0 9 * * * cd /opt/agent_shablon/clients/<slug> && venv/bin/python manage.py check_subscription_alert
"""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from assistant.models import ProjectSubscription

ALERT_THRESHOLD_DAYS = 5


class Command(BaseCommand):
    help = "Foydalanuvchilarning Pro obunasi tugashiga 5 kun (yoki kamroq) qolganda Telegram orqali ogohlantirish yuboradi."

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN or not settings.SUPERADMIN_TELEGRAM_ID:
            self.stdout.write(self.style.WARNING(
                "TELEGRAM_BOT_TOKEN yoki SUPERADMIN_TELEGRAM_ID sozlanmagan — ogohlantirish o'tkazib yuborildi."
            ))
            return

        today = timezone.now().date()
        subscriptions = ProjectSubscription.objects.filter(plan="pro").select_related("workspace__owner")
        for subscription in subscriptions:
            self._check(subscription, today)

    def _check(self, subscription, today):
        name = subscription.workspace.owner.get_username()
        days_left = subscription.days_left

        # Faqat 5 kun qolganidan to muddati o'tganiga 3 kungacha ogohlantiramiz —
        # aks holda Pro'si allaqachon tugagan eski foydalanuvchilar haqida har kuni xabar kelaverardi.
        if days_left > ALERT_THRESHOLD_DAYS or days_left < -3:
            return

        if subscription.last_alert_sent_at == today:
            return

        if days_left >= 0:
            text = (
                f"⚠️ <b>{name}</b> Pro obunasi {days_left} kundan so'ng tugaydi "
                f"({subscription.subscription_end:%d.%m.%Y})."
            )
        else:
            text = (
                f"🛑 <b>{name}</b> Pro obunasi muddati o'tib ketdi "
                f"({subscription.subscription_end:%d.%m.%Y}) — endi bepul tarif qoidalari amal qilmoqda."
            )

        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": settings.SUPERADMIN_TELEGRAM_ID, "text": text, "parse_mode": "HTML"},
                timeout=10,
            )
            resp.raise_for_status()
            subscription.last_alert_sent_at = today
            subscription.save(update_fields=["last_alert_sent_at"])
            self.stdout.write(self.style.SUCCESS(f"{name}: ogohlantirish yuborildi."))
        except requests.RequestException as exc:
            self.stdout.write(self.style.ERROR(f"{name}: yuborib bo'lmadi: {exc}"))
