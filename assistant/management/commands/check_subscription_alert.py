"""
Obuna tugashiga oz qolganda super adminga (siz) Telegram orqali ogohlantirish yuboradi.

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
    help = "Obuna tugashiga 5 kun (yoki kamroq) qolganda Telegram orqali ogohlantirish yuboradi."

    def handle(self, *args, **options):
        subscription = ProjectSubscription.get_solo()

        if not settings.TELEGRAM_BOT_TOKEN or not settings.SUPERADMIN_TELEGRAM_ID:
            self.stdout.write(self.style.WARNING(
                "TELEGRAM_BOT_TOKEN yoki SUPERADMIN_TELEGRAM_ID sozlanmagan — ogohlantirish o'tkazib yuborildi."
            ))
            return

        days_left = subscription.days_left
        today = timezone.now().date()

        if days_left > ALERT_THRESHOLD_DAYS:
            self.stdout.write(f"Obuna hali {days_left} kun bor — ogohlantirish shart emas.")
            return

        if subscription.last_alert_sent_at == today:
            self.stdout.write("Bugun allaqachon ogohlantirish yuborilgan.")
            return

        if days_left >= 0:
            text = (
                f"⚠️ <b>{settings.BUSINESS_NAME}</b> obunasi {days_left} kundan so'ng tugaydi "
                f"({subscription.subscription_end:%d.%m.%Y}). Obunani uzaytirishni unutmang."
            )
        else:
            text = (
                f"🛑 <b>{settings.BUSINESS_NAME}</b> obunasi muddati o'tib ketdi "
                f"({subscription.subscription_end:%d.%m.%Y}). Loyiha hali ishlayapti, lekin tekshiring."
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
            self.stdout.write(self.style.SUCCESS("Ogohlantirish yuborildi."))
        except requests.RequestException as exc:
            self.stdout.write(self.style.ERROR(f"Yuborib bo'lmadi: {exc}"))
