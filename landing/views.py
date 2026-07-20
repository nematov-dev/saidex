import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from assistant.models import ConversationLog, Lead
from assistant.services.llm import transcribe_audio
from assistant.services.rag import answer_question
from .forms import ContactLeadForm
from .models import LandingSettings, Tariff, PortfolioItem, Testimonial
from .ratelimit import get_client_ip, get_pseudo_user_id, is_rate_limited

# Ovozli xabar uchun eng katta ruxsat etilgan hajm — brauzerdan yuboriladigan
# ~20 soniyalik audio bundan ancha kichik, bu faqat suiiste'moldan himoya.
MAX_AUDIO_BYTES = 8 * 1024 * 1024

RATE_LIMIT_MESSAGE = _("So'rovlar soni ko'p — biroz kuting va qaytadan urinib ko'ring.")


def home(request):
    context = {
        "settings": LandingSettings.get_solo(),
        "tariffs": Tariff.objects.filter(is_active=True),
        "portfolio_items": PortfolioItem.objects.filter(is_active=True),
        "testimonials": Testimonial.objects.filter(is_active=True),
        "contact_form": ContactLeadForm(),
    }
    return render(request, "landing/home.html", context)


@require_POST
def submit_contact(request):
    form = ContactLeadForm(request.POST)
    if form.is_valid():
        Lead.objects.create(
            telegram_user_id=0,
            full_name=form.cleaned_data["full_name"],
            phone=form.cleaned_data["phone"],
            message=form.cleaned_data["message"] or _("Saytdagi aloqa formasi orqali murojaat."),
            channel="website",
        )
        messages.success(request, _("Rahmat! Arizangiz qabul qilindi, tez orada siz bilan bog'lanamiz."))
        return redirect("/#contact")

    messages.error(request, _("Iltimos, formani to'g'ri to'ldiring."))
    context = {
        "settings": LandingSettings.get_solo(),
        "tariffs": Tariff.objects.filter(is_active=True),
        "portfolio_items": PortfolioItem.objects.filter(is_active=True),
        "testimonials": Testimonial.objects.filter(is_active=True),
        "contact_form": form,
    }
    return render(request, "landing/home.html", context)


def _log_demo_conversation(request, question, answer, answered_by_ai, in_tok, out_tok):
    ConversationLog.objects.create(
        telegram_user_id=get_pseudo_user_id(get_client_ip(request)),
        question=question, answer=answer or "", answered_by_ai=answered_by_ai,
        input_tokens=in_tok, output_tokens=out_tok, channel="website",
    )


def _create_demo_lead(request, message):
    """
    Landing page demo-chatida xarid niyati aniqlansa, guruhdagi kabi
    (userbot/handlers.py'dagi create_group_lead) — bosqichma-bosqich ism/
    telefon so'ralmaydi (anonim veb tashrif buyuruvchi, sessiya yo'q), ariza
    to'g'ridan-to'g'ri channel="website" bilan yaratiladi, keyinroq admin
    o'zi bog'lanishi uchun.
    """
    Lead.objects.create(
        telegram_user_id=get_pseudo_user_id(get_client_ip(request)),
        full_name="", phone="", message=message, channel="website",
    )


@require_POST
def demo_voice(request):
    """
    Landing page'dagi mikrofon-demo: brauzerdan yuborilgan ovozli xabarni
    Telegram userbot'dagi bilan bir xil `transcribe_audio` + `answer_question`
    orqali qayta ishlaydi. Autentifikatsiyasiz ochiq endpoint bo'lgani uchun
    IP-asoslangan rate-limit bilan himoyalangan.
    """
    if is_rate_limited(request):
        return JsonResponse({"error": str(RATE_LIMIT_MESSAGE)}, status=429)

    audio_file = request.FILES.get("audio")
    if not audio_file:
        return JsonResponse({"error": _("Audio fayl topilmadi.")}, status=400)
    if audio_file.size > MAX_AUDIO_BYTES:
        return JsonResponse({"error": _("Audio fayl juda katta.")}, status=400)

    question = transcribe_audio(audio_file.read(), mime_type=audio_file.content_type or "audio/webm")
    if not question:
        return JsonResponse({"error": _("Ovozli xabarni tushuna olmadim. Yana urinib ko'ring.")}, status=422)

    answer, in_tok, out_tok, answered_by_ai, wants_lead = answer_question(
        question, channel="website", history=None,
    )
    _log_demo_conversation(request, question, answer, answered_by_ai, in_tok, out_tok)
    if wants_lead:
        _create_demo_lead(request, question)
    return JsonResponse({"question": question, "answer": answer or str(_("Kechirasiz, hozircha javob bera olmadim."))})


@require_POST
def demo_chat(request):
    """Ovozli demo'dan keyin ochiladigan matnli chatning davomi — xuddi
    shu `answer_question` orqali, JS tomonda saqlangan tarix bilan."""
    if is_rate_limited(request):
        return JsonResponse({"error": str(RATE_LIMIT_MESSAGE)}, status=429)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": _("Noto'g'ri so'rov.")}, status=400)

    message = (payload.get("message") or "").strip()[:2000]
    if not message:
        return JsonResponse({"error": _("Xabar bo'sh bo'lishi mumkin emas.")}, status=400)

    raw_history = payload.get("history") or []
    history = [
        {"role": "assistant" if item.get("role") == "assistant" else "user", "content": str(item.get("content", ""))[:2000]}
        for item in raw_history[-10:]
        if isinstance(item, dict) and item.get("content")
    ]

    answer, in_tok, out_tok, answered_by_ai, wants_lead = answer_question(
        message, channel="website", history=history,
    )
    _log_demo_conversation(request, message, answer, answered_by_ai, in_tok, out_tok)
    if wants_lead:
        _create_demo_lead(request, message)
    return JsonResponse({"answer": answer or str(_("Kechirasiz, hozircha javob bera olmadim."))})
