from datetime import timedelta

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from openpyxl import Workbook

from .models import (
    Document, Lead, ConversationLog, BotConfig, ProjectSubscription, TelegramAccountConnection,
    TelegramGroup, Workspace,
)
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from .forms import DocumentUploadForm, BotConfigForm, WorkspaceUserCreateForm, WorkspaceUserUpdateForm
from .services.phone import normalize_phone
from .services.rag import index_document

# Super admin bo'limi (/saidex/) butunlay alohida — business admin (is_staff)
# uchun mo'ljallanmagan, unga hech qanday havola ko'rsatilmaydi. Ruxsati
# yo'q foydalanuvchi shu yerga kirishga urinsa, business login'ga emas,
# maxsus super admin login sahifasiga (/saidex/login/) yo'naltiriladi.
superadmin_required = user_passes_test(
    lambda u: u.is_active and u.is_superuser, login_url="assistant:superadmin_login"
)


def _workspace(request) -> Workspace:
    """Joriy foydalanuvchining ish maydoni — biznes paneldagi barcha ma'lumotlar shunga cheklanadi."""
    return Workspace.for_user(request.user)


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    """Ro'yxatdan o'tganlar login sifatida email'dan foydalanadi (username=email, kichik harflarda)."""

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        return username.lower() if "@" in username else username


class BusinessLoginView(LoginView):
    template_name = "assistant/login.html"
    authentication_form = EmailOrUsernameAuthenticationForm
    redirect_authenticated_user = True


class BusinessLogoutView(LogoutView):
    next_page = "assistant:login"


class SuperAdminAuthenticationForm(AuthenticationForm):
    """Oddiy login formasi, faqat is_superuser=True hisoblarga ruxsat beradi."""

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_superuser:
            raise ValidationError(
                _("Bu hisob super admin emas."), code="not_superuser",
            )


class SuperAdminLoginView(LoginView):
    """
    Butunlay alohida, biznes admin login'idan mustaqil kirish sahifasi.
    Faqat /saidex/login/ orqali ochiladi, sidebar yoki boshqa hech qanday
    joyda unga havola ko'rsatilmaydi.
    """

    template_name = "assistant/superadmin_login.html"
    authentication_form = SuperAdminAuthenticationForm
    redirect_authenticated_user = False

    def get_success_url(self):
        return str(reverse_lazy("assistant:superadmin_dashboard"))


class SuperAdminLogoutView(LogoutView):
    next_page = "assistant:superadmin_login"


def _handle_password_change(request, template_name, success_redirect_name):
    """Parolni o'zgartirish formasi — ham biznes admin, ham super admin profil
    sahifasida ishlatiladi. Muvaffaqiyatli o'zgartirilgach, foydalanuvchi
    tizimdan chiqarib yuborilmasligi uchun sessiya yangilanadi."""
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, _("Parol muvaffaqiyatli o'zgartirildi."))
            return redirect(success_redirect_name)
    else:
        form = PasswordChangeForm(user=request.user)
    for field in form.fields.values():
        field.widget.attrs["class"] = "form-control"
    return render(request, template_name, {"form": form})


@login_required
def profile(request):
    return _handle_password_change(request, "assistant/profile.html", "assistant:profile")


@login_required
def dashboard(request):
    """
    MUHIM: avval "Suhbatlar (7 kun)" / "AI javob bergan (7 kun)" statistikasi
    ko'rsatilardi — lekin loyiha hali 7 kundan kam ishlagani sababli bu son
    har doim "jami" bilan bir xil chiqib, chalkashtirar edi ("nega ikkalasi
    ham 134?"). Shuning uchun buning o'rniga har doim tushunarli bo'ladigan
    ikkita ko'rsatkichga o'tildi: nechta ODAM (unique foydalanuvchi) muloqot
    qilgani va nechta SAVOLGA javob berilgani (shundan AI ulushi bilan).
    """
    today = timezone.now().date()
    workspace = _workspace(request)
    conversations = ConversationLog.objects.filter(workspace=workspace)
    documents = Document.objects.filter(workspace=workspace)
    leads = Lead.objects.filter(workspace=workspace)
    conversations_total = conversations.count()
    ai_answered_total = conversations.filter(answered_by_ai=True).count()
    context = {
        "config": workspace.config,
        "subscription": workspace.subscription,
        "documents_count": documents.count(),
        "documents_ready": documents.filter(status="ready").count(),
        "leads_new": leads.filter(status="new").count(),
        "leads_total": leads.count(),
        "unique_users_total": conversations.values("telegram_user_id").distinct().count(),
        "unique_users_today": conversations.filter(created_at__date=today)
            .values("telegram_user_id").distinct().count(),
        "conversations_total": conversations_total,
        "ai_answered_total": ai_answered_total,
        "ai_answered_percent": round(ai_answered_total * 100 / conversations_total) if conversations_total else 0,
        "recent_leads": leads[:5],
        "users_stats": _users_stats() if request.user.is_superuser else None,
    }
    return render(request, "assistant/dashboard.html", context)


@login_required
def document_list(request):
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.workspace = _workspace(request)
            doc.uploaded_by = request.user
            doc.save()
            index_document(doc)  # sinxron; katta hujjatlar uchun Celery/RQ ga o'tkazish tavsiya etiladi
            if doc.status == "ready":
                messages.success(
                    request,
                    _("'%(title)s' muvaffaqiyatli qo'shildi (%(chunks)s bo'lak).")
                    % {"title": doc.title, "chunks": doc.chunk_count},
                )
            else:
                messages.error(request, _("Xatolik: %(error)s") % {"error": doc.error_message})
            return redirect("assistant:documents")
    else:
        form = DocumentUploadForm()

    documents = Document.objects.filter(workspace=_workspace(request))
    return render(request, "assistant/documents.html", {"documents": documents, "form": form})


@login_required
@require_POST
def document_delete(request, pk):
    doc = get_object_or_404(Document, pk=pk, workspace=_workspace(request))
    doc.file.delete(save=False)
    doc.delete()
    messages.success(request, _("Hujjat o'chirildi."))
    return redirect("assistant:documents")


@login_required
@require_POST
def document_reprocess(request, pk):
    doc = get_object_or_404(Document, pk=pk, workspace=_workspace(request))
    index_document(doc)
    messages.info(request, _("Qayta ishlandi: %(status)s") % {"status": doc.get_status_display()})
    return redirect("assistant:documents")


@login_required
def prompt_settings(request):
    workspace = _workspace(request)
    config = workspace.config
    if request.method == "POST":
        form = BotConfigForm(request.POST, instance=config)
        if form.is_valid():
            subscription = workspace.subscription
            if form.cleaned_data["ai_enabled"] and not subscription.is_service_active:
                messages.error(request, _("AI'ni yoqish uchun avval obuna oling — adminlarga bog'laning."))
                form.instance.ai_enabled = False
            form.save()
            messages.success(request, _("Sozlamalar saqlandi."))
            return redirect("assistant:prompt_settings")
    else:
        form = BotConfigForm(instance=config)
    return render(request, "assistant/prompt_settings.html", {"form": form, "config": config})


@login_required
@require_POST
def toggle_ai(request):
    workspace = _workspace(request)
    config = workspace.config
    subscription = workspace.subscription
    if not config.ai_enabled and not subscription.is_service_active:
        messages.error(request, _("AI'ni yoqish uchun avval obuna oling — adminlarga bog'laning."))
        return redirect("assistant:dashboard")
    config.ai_enabled = not config.ai_enabled
    config.save(update_fields=["ai_enabled"])
    messages.success(request, _("AI yoqildi.") if config.ai_enabled else _("AI o'chirildi."))
    return redirect("assistant:dashboard")


LEADS_PER_PAGE = 20


def _leads_queryset(request, is_archived: bool):
    """Status bo'yicha filter (GET ?status=) qo'llangan, arxiv holatiga
    mos Lead queryset'ini qaytaradi — leads_list va leads_archive ikkalasi
    ham shu funksiyadan foydalanadi."""
    qs = Lead.objects.filter(workspace=_workspace(request), is_archived=is_archived)
    status = request.GET.get("status", "")
    if status in dict(Lead.STATUS_CHOICES):
        qs = qs.filter(status=status)
    return qs, status


def _leads_page(request, is_archived: bool):
    qs, status = _leads_queryset(request, is_archived)
    paginator = Paginator(qs, LEADS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    return {
        "page_obj": page_obj,
        "leads": page_obj.object_list,
        "status_filter": status,
        "status_choices": Lead.STATUS_CHOICES,
        "is_archive_view": is_archived,
    }


@login_required
def leads_list(request):
    return render(request, "assistant/leads.html", _leads_page(request, is_archived=False))


@login_required
def leads_archive(request):
    return render(request, "assistant/leads.html", _leads_page(request, is_archived=True))


@login_required
def leads_export(request):
    """Joriy filterga (holat, arxiv/faol) mos arizalarni Excel (.xlsx) fayl
    sifatida yuklab beradi — sahifalashsiz, mos kelgan barcha arizalar."""
    is_archived = request.GET.get("archived") == "1"
    qs, _status = _leads_queryset(request, is_archived)

    wb = Workbook()
    ws = wb.active
    ws.title = "Arxiv" if is_archived else "Arizalar"
    ws.append(["Foydalanuvchi", "Manba", "Telefon", "Xabar", "Holat", "Izoh", "Sana"])
    for lead in qs:
        ws.append([
            lead.full_name or lead.telegram_username or str(lead.telegram_user_id),
            lead.get_channel_display(),
            lead.phone,
            lead.message,
            lead.get_status_display(),
            lead.admin_note,
            lead.created_at.strftime("%d.%m.%Y %H:%M"),
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = "arxiv_arizalar.xlsx" if is_archived else "arizalar.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


def _redirect_next(request, fallback):
    next_url = request.POST.get("next")
    return redirect(next_url) if next_url else redirect(fallback)


@login_required
@require_POST
def lead_update_status(request, pk):
    lead = get_object_or_404(Lead, pk=pk, workspace=_workspace(request))
    new_status = request.POST.get("status")
    note = request.POST.get("admin_note", "")
    if new_status in dict(Lead.STATUS_CHOICES):
        lead.status = new_status
    if note:
        lead.admin_note = note
    lead.save()
    return _redirect_next(request, "assistant:leads")


@login_required
@require_POST
def lead_archive(request, pk):
    lead = get_object_or_404(Lead, pk=pk, workspace=_workspace(request))
    lead.is_archived = True
    lead.save(update_fields=["is_archived"])
    messages.success(request, _("Ariza arxivga o'tkazildi."))
    return _redirect_next(request, "assistant:leads")


@login_required
@require_POST
def lead_delete(request, pk):
    lead = get_object_or_404(Lead, pk=pk, workspace=_workspace(request))
    was_archived = lead.is_archived
    lead.delete()
    messages.success(request, _("Ariza o'chirildi."))
    return _redirect_next(request, "assistant:leads_archive" if was_archived else "assistant:leads")


@login_required
@require_POST
def leads_bulk_delete(request):
    ids = request.POST.getlist("lead_ids")
    own_leads = Lead.objects.filter(workspace=_workspace(request), pk__in=ids)
    was_archived = own_leads.filter(is_archived=True).exists()
    deleted_count, _details = own_leads.delete()
    if deleted_count:
        messages.success(request, _("%(count)s ta ariza o'chirildi.") % {"count": deleted_count})
    return _redirect_next(request, "assistant:leads_archive" if was_archived else "assistant:leads")


@login_required
def groups_list(request):
    """
    Telegram guruhlar ro'yxati — userbot birinchi marta guruh xabarini
    ko'rganda avtomatik shu yerga qo'shiladi (TelegramGroup.get_or_create).
    Admin shu yerdan har bir guruh uchun AI javob berish-bermasligini va
    javob berish tartibini (kalit so'z bilan/kalitsiz, kimga) sozlaydi.
    """
    workspace = _workspace(request)
    config = workspace.config
    if request.method == "POST" and request.POST.get("action") == "save_keywords":
        keywords = request.POST.get("group_trigger_keywords", "").strip()
        if keywords:
            config.group_trigger_keywords = keywords
            config.save(update_fields=["group_trigger_keywords"])
            messages.success(request, _("Guruh kalit so'zlari saqlandi."))
        else:
            messages.error(request, _("Kalit so'zlar bo'sh bo'lishi mumkin emas."))
        return redirect("assistant:groups")

    groups = TelegramGroup.objects.filter(workspace=workspace)
    return render(request, "assistant/groups.html", {"groups": groups, "config": config})


@login_required
@require_POST
def group_update(request, pk):
    group = get_object_or_404(TelegramGroup, pk=pk, workspace=_workspace(request))
    group.is_ai_enabled = request.POST.get("is_ai_enabled") == "on"

    reply_mode = request.POST.get("reply_mode")
    if reply_mode in dict(TelegramGroup.REPLY_MODE_CHOICES):
        group.reply_mode = reply_mode

    sender_filter = request.POST.get("sender_filter")
    if sender_filter in dict(TelegramGroup.SENDER_FILTER_CHOICES):
        group.sender_filter = sender_filter

    group.save(update_fields=["is_ai_enabled", "reply_mode", "sender_filter"])
    messages.success(
        request,
        _("'%(name)s' guruh sozlamalari yangilandi.") % {"name": group.title or group.chat_id},
    )
    return redirect("assistant:groups")


@csrf_exempt
def internal_stats_api(request):
    """Tashqi integratsiyalar uchun (masalan hisobot xizmatlari) umumiy statistikani beradi.
    Header: X-Internal-Token: <INTERNAL_API_TOKEN>
    """
    token = request.headers.get("X-Internal-Token")
    if not settings.INTERNAL_API_TOKEN or token != settings.INTERNAL_API_TOKEN:
        return HttpResponseForbidden("Forbidden")

    since_week = timezone.now() - timedelta(days=7)
    data = {
        "business_name": settings.BUSINESS_NAME,
        "workspaces_total": Workspace.objects.count(),
        "workspaces_pro": sum(1 for sub in ProjectSubscription.objects.all() if sub.is_pro),
        "documents_total": Document.objects.count(),
        "documents_ready": Document.objects.filter(status="ready").count(),
        "leads_total": Lead.objects.count(),
        "leads_new": Lead.objects.filter(status="new").count(),
        "conversations_total": ConversationLog.objects.count(),
        "conversations_week": ConversationLog.objects.filter(created_at__gte=since_week).count(),
    }
    return JsonResponse(data)


@login_required
def subscription_page(request):
    """Foydalanuvchining obunasi: joriy tarif, bepul limitdan qancha ishlatilgani va Pro olish tugmasi."""
    return render(request, "assistant/subscription.html", {"subscription": _workspace(request).subscription})


# ---------------------------------------------------------------------------
# SUPER ADMIN — faqat is_superuser=True foydalanuvchi (siz) kira oladi.
# Foydalanuvchilar (ish maydonlari), ularning obunasi va AI modeli shu yerda boshqariladi.
# ---------------------------------------------------------------------------

@superadmin_required
def superadmin_dashboard(request):
    since_week = timezone.now() - timedelta(days=7)
    subscriptions = list(ProjectSubscription.objects.select_related("workspace__owner"))
    context = {
        "workspaces_total": Workspace.objects.count(),
        "pro_total": sum(1 for sub in subscriptions if sub.is_pro),
        "free_total": sum(1 for sub in subscriptions if not sub.is_pro),
        "expiring_soon": [sub for sub in subscriptions if sub.is_pro and sub.days_left <= 5],
        "recent_workspaces": Workspace.objects.select_related("owner", "project_subscription")[:8],
        "leads_total": Lead.objects.count(),
        "conversations_week": ConversationLog.objects.filter(created_at__gte=since_week).count(),
        "telegram_connected": TelegramAccountConnection.objects.filter(status="connected").count(),
    }
    return render(request, "assistant/superadmin_dashboard.html", context)


@superadmin_required
def superadmin_profile(request):
    return _handle_password_change(
        request, "assistant/superadmin_profile.html", "assistant:superadmin_profile"
    )


USERS_PER_PAGE = 25


def _users_stats() -> dict:
    """Foydalanuvchilar bo'yicha umumiy sonlar (panel sahifalarining yuqorisida ko'rsatiladi)."""
    subscriptions = list(ProjectSubscription.objects.all())
    today = timezone.now().date()
    return {
        "total": Workspace.objects.count(),
        "today": Workspace.objects.filter(created_at__date=today).count(),
        "pro": sum(1 for sub in subscriptions if sub.is_pro),
        "free": sum(1 for sub in subscriptions if not sub.is_pro),
        "blocked": sum(1 for sub in subscriptions if not sub.is_active),
        "limit_reached": sum(1 for sub in subscriptions if sub.is_active and sub.free_limit_reached),
        "telegram_connected": TelegramAccountConnection.objects.filter(status="connected").count(),
    }


@superadmin_required
def superadmin_users(request):
    """Barcha foydalanuvchilar (ish maydonlari) ro'yxati — qidiruv va tarif bo'yicha filter bilan."""
    qs = Workspace.objects.select_related("owner", "project_subscription")
    query = request.GET.get("q", "").strip()
    if query:
        qs = qs.filter(
            Q(owner__username__icontains=query) | Q(owner__email__icontains=query)
            | Q(name__icontains=query) | Q(phone__icontains=query)
        )
    plan = request.GET.get("plan", "")
    if plan in dict(ProjectSubscription.PLAN_CHOICES):
        qs = qs.filter(project_subscription__plan=plan)

    page_obj = Paginator(qs, USERS_PER_PAGE).get_page(request.GET.get("page"))
    return render(request, "assistant/superadmin_users.html", {
        "page_obj": page_obj,
        "workspaces": page_obj.object_list,
        "query": query,
        "plan_filter": plan,
        "plan_choices": ProjectSubscription.PLAN_CHOICES,
        "form": WorkspaceUserCreateForm(),
        "stats": _users_stats(),
    })


@superadmin_required
@require_POST
def superadmin_user_create(request):
    form = WorkspaceUserCreateForm(request.POST)
    if not form.is_valid():
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
        return redirect("assistant:superadmin_users")

    workspace = form.save()
    messages.success(
        request, _("Foydalanuvchi qo'shildi: %(user)s") % {"user": workspace.owner.get_username()},
    )
    return redirect("assistant:superadmin_user_detail", pk=workspace.pk)


def _get_workspace_or_404(pk) -> Workspace:
    return get_object_or_404(Workspace.objects.select_related("owner"), pk=pk)


@superadmin_required
def superadmin_user_detail(request, pk):
    workspace = _get_workspace_or_404(pk)
    since_week = timezone.now() - timedelta(days=7)
    conversations = ConversationLog.objects.filter(workspace=workspace)
    return render(request, "assistant/superadmin_user_detail.html", {
        "workspace": workspace,
        "owner": workspace.owner,
        "subscription": workspace.subscription,
        "config": workspace.config,
        "connection": workspace.telegram_connection,
        "documents_count": Document.objects.filter(workspace=workspace).count(),
        "leads_total": Lead.objects.filter(workspace=workspace).count(),
        "conversations_total": conversations.count(),
        "conversations_week": conversations.filter(created_at__gte=since_week).count(),
        "available_models": settings.AVAILABLE_LLM_MODELS,
        "edit_form": WorkspaceUserUpdateForm(workspace=workspace),
    })


@superadmin_required
@require_POST
def superadmin_user_update(request, pk):
    workspace = _get_workspace_or_404(pk)
    form = WorkspaceUserUpdateForm(request.POST, workspace=workspace)
    if form.is_valid():
        form.save()
        messages.success(request, _("Foydalanuvchi ma'lumotlari saqlandi."))
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    return _redirect_user_detail(workspace)


def _redirect_user_detail(workspace):
    return redirect("assistant:superadmin_user_detail", pk=workspace.pk)


@superadmin_required
@require_POST
def superadmin_extend(request, pk):
    """Pro obunani berilgan muddatga uzaytiradi (bepul foydalanuvchini Pro'ga o'tkazadi)."""
    workspace = _get_workspace_or_404(pk)
    subscription = workspace.subscription
    custom_amount = request.POST.get("custom_amount", "").strip()
    if custom_amount:
        try:
            amount = int(custom_amount)
        except ValueError:
            amount = 0
        if amount <= 0:
            messages.error(request, _("Noto'g'ri muddat kiritildi."))
            return _redirect_user_detail(workspace)
        days = amount * 30 if request.POST.get("custom_unit") == "months" else amount
    else:
        days = int(request.POST.get("days", 30))
    subscription.extend(days)
    end_str = subscription.subscription_end.strftime("%d.%m.%Y")
    messages.success(
        request,
        _("Pro obuna %(days)s kunga uzaytirildi. Yangi muddat: %(end)s") % {"days": days, "end": end_str},
    )
    return _redirect_user_detail(workspace)


@superadmin_required
@require_POST
def superadmin_set_free(request, pk):
    workspace = _get_workspace_or_404(pk)
    workspace.subscription.set_free()
    messages.success(request, _("Foydalanuvchi bepul tarifga o'tkazildi."))
    return _redirect_user_detail(workspace)


@superadmin_required
@require_POST
def superadmin_set_limit(request, pk):
    workspace = _get_workspace_or_404(pk)
    subscription = workspace.subscription
    try:
        limit = int(request.POST.get("free_question_limit", ""))
    except ValueError:
        limit = -1
    if limit < 0:
        messages.error(request, _("Noto'g'ri limit kiritildi."))
        return _redirect_user_detail(workspace)
    subscription.free_question_limit = limit
    subscription.save(update_fields=["free_question_limit"])
    messages.success(request, _("Bepul savollar limiti: %(limit)s") % {"limit": limit})
    return _redirect_user_detail(workspace)


@superadmin_required
@require_POST
def superadmin_toggle(request, pk):
    """Foydalanuvchini bloklash/faollashtirish: AI to'xtaydi va u panelga kira olmaydi."""
    workspace = _get_workspace_or_404(pk)
    owner = workspace.owner
    if owner.is_superuser:
        messages.error(request, _("Super admin hisobini bloklab bo'lmaydi."))
        return _redirect_user_detail(workspace)
    subscription = workspace.subscription
    subscription.is_active = not subscription.is_active
    subscription.save(update_fields=["is_active"])
    owner.is_active = subscription.is_active
    owner.save(update_fields=["is_active"])
    messages.success(
        request,
        _("Foydalanuvchi faollashtirildi.") if subscription.is_active else _("Foydalanuvchi bloklandi."),
    )
    return _redirect_user_detail(workspace)


@superadmin_required
@require_POST
def superadmin_set_model(request, pk):
    workspace = _get_workspace_or_404(pk)
    subscription = workspace.subscription
    model_name = request.POST.get("llm_model")
    valid_models = dict(settings.AVAILABLE_LLM_MODELS)
    if model_name in valid_models:
        subscription.llm_model = model_name
        subscription.save(update_fields=["llm_model"])
        messages.success(
            request,
            _("AI modeli o'zgartirildi: %(model)s") % {"model": valid_models[model_name]},
        )
    else:
        messages.error(request, _("Noto'g'ri model tanlandi."))
    return _redirect_user_detail(workspace)


@superadmin_required
@require_POST
def superadmin_set_password(request, pk):
    workspace = _get_workspace_or_404(pk)
    password = request.POST.get("new_password", "")
    if len(password) < 8:
        messages.error(request, _("Parol kamida 8 belgidan iborat bo'lishi kerak."))
        return _redirect_user_detail(workspace)
    workspace.owner.set_password(password)
    workspace.owner.save(update_fields=["password"])
    messages.success(request, _("Yangi parol o'rnatildi."))
    return _redirect_user_detail(workspace)


@superadmin_required
@require_POST
def superadmin_user_delete(request, pk):
    workspace = _get_workspace_or_404(pk)
    owner = workspace.owner
    if workspace.is_main or owner.is_superuser:
        messages.error(request, _("Asosiy ish maydoni yoki super admin hisobini o'chirib bo'lmaydi."))
        return _redirect_user_detail(workspace)
    connection = TelegramAccountConnection.objects.filter(workspace=workspace).first()
    if connection:
        _disconnect_telegram_account(connection)
    for doc in Document.objects.filter(workspace=workspace):
        doc.file.delete(save=False)
    username = owner.get_username()
    owner.delete()  # CASCADE: ish maydoni va unga tegishli barcha ma'lumotlar ham o'chadi
    messages.success(request, _("Foydalanuvchi o'chirildi: %(user)s") % {"user": username})
    return redirect("assistant:superadmin_users")


# ---------------------------------------------------------------------------
# Telegram AKKAUNT (userbot) ulash. Har bir ish maydoni o'z akkauntini ulaydi;
# super admin panelidagi sahifa asosiy (Saidex) ish maydonining akkauntini boshqaradi.
# ---------------------------------------------------------------------------

def _telethon_client(session_string: str = ""):
    return TelegramClient(
        StringSession(session_string),
        int(settings.TELEGRAM_API_ID),
        settings.TELEGRAM_API_HASH,
    )


def _main_workspace(request) -> Workspace:
    """Super admin paneli boshqaradigan ish maydoni — asosiy (Saidex), bo'lmasa super adminning o'zi."""
    return Workspace.main() or _workspace(request)


@superadmin_required
def telegram_account(request):
    connection = _main_workspace(request).telegram_connection
    api_configured = bool(settings.TELEGRAM_API_ID and settings.TELEGRAM_API_HASH)
    return render(request, "assistant/telegram_account.html", {
        "connection": connection,
        "api_configured": api_configured,
    })


def _reset_connection(connection):
    connection.status = "disconnected"
    connection.phone_number = ""
    connection.session_string = ""
    connection.phone_code_hash = ""
    connection.connected_username = ""
    connection.connected_first_name = ""
    connection.connected_user_id = None
    connection.connected_at = None
    connection.save()


def _complete_telegram_login(request, client, connection):
    """Kod/2FA tasdiqlangandan keyingi yakuniy qadam. Bitta Telegram akkaunt faqat
    BITTA hisobga ulanishi mumkin — u allaqachon boshqa hisobga ulangan bo'lsa,
    yangi sessiya darhol yopiladi va ulanish rad etiladi."""
    me = client.get_me()
    taken = (
        TelegramAccountConnection.objects.filter(status="connected", connected_user_id=me.id)
        .exclude(pk=connection.pk).exists()
    )
    if taken:
        try:
            client.log_out()
        except Exception:  # noqa: BLE001 - sessiya baribir tashlab yuboriladi
            pass
        _reset_connection(connection)
        messages.error(request, _("Bu Telegram akkaunt boshqa hisobga allaqachon ulangan."))
        return

    connection.session_string = client.session.save()
    connection.connected_username = me.username or ""
    connection.connected_first_name = me.first_name or ""
    connection.connected_user_id = me.id
    connection.status = "connected"
    connection.connected_at = timezone.now()
    connection.phone_code_hash = ""
    connection.save()
    messages.success(
        request,
        _("Ulandi: %(name)s") % {"name": me.first_name or connection.phone_number},
    )


def _send_code_logic(request, connection):
    """Telefon raqamiga tasdiqlash kodi yuborish — super admin va biznes admin
    ikkalasi ham ishlatadigan umumiy mantiq (faqat keyingi redirect manzili
    chaqiruvchi view'da farqlanadi)."""
    raw_phone = request.POST.get("phone_number", "").strip()
    phone = normalize_phone(raw_phone) or raw_phone

    if not (settings.TELEGRAM_API_ID and settings.TELEGRAM_API_HASH):
        messages.error(
            request,
            _("Avval .env faylida TELEGRAM_API_ID va TELEGRAM_API_HASH to'ldiring (my.telegram.org)."),
        )
        return

    if connection.is_connected:
        messages.error(request, _("Avval joriy akkauntni uzing, keyin yangisini ulang."))
        return

    if not phone:
        messages.error(request, _("Telefon raqamini kiriting (masalan +998901234567)."))
        return

    if TelegramAccountConnection.objects.filter(status="connected", phone_number=phone).exclude(pk=connection.pk).exists():
        messages.error(request, _("Bu raqam boshqa hisobga allaqachon ulangan."))
        return

    client = _telethon_client()
    try:
        client.connect()
        sent = client.send_code_request(phone)
        connection.phone_number = phone
        connection.session_string = client.session.save()
        connection.phone_code_hash = sent.phone_code_hash
        connection.status = "pending_code"
        connection.save()
        messages.success(
            request,
            _("Tasdiqlash kodi %(phone)s raqamiga (Telegram orqali) yuborildi.") % {"phone": phone},
        )
    except Exception as exc:  # noqa: BLE001
        messages.error(request, _("Xatolik: %(error)s") % {"error": exc})
    finally:
        client.disconnect()


def _verify_code_logic(request, connection):
    """Yuborilgan kodni tasdiqlash — ikkala panel uchun umumiy mantiq.
    Agar 2FA kerak bo'lsa, ("pending_password", None) qaytaradi, aks holda
    (holat, xabar) emas — chaqiruvchi view natijani status orqali biladi."""
    code = request.POST.get("code", "").strip()

    if connection.status != "pending_code":
        messages.error(request, _("Avval telefon raqamni kiriting."))
        return

    client = _telethon_client(connection.session_string)
    try:
        client.connect()
        try:
            client.sign_in(connection.phone_number, code, phone_code_hash=connection.phone_code_hash)
        except SessionPasswordNeededError:
            connection.session_string = client.session.save()
            connection.status = "pending_password"
            connection.save()
            messages.info(request, _("Bu akkauntda 2 bosqichli tasdiqlash (2FA) yoqilgan — parolni kiriting."))
            return

        _complete_telegram_login(request, client, connection)
    except Exception as exc:  # noqa: BLE001
        messages.error(request, _("Xatolik: %(error)s") % {"error": exc})
    finally:
        client.disconnect()


def _verify_password_logic(request, connection):
    """2FA parolini tasdiqlash — ikkala panel uchun umumiy mantiq."""
    password = request.POST.get("password", "")

    if connection.status != "pending_password":
        messages.error(request, _("Kutilmagan holat, qaytadan urinib ko'ring."))
        return

    client = _telethon_client(connection.session_string)
    try:
        client.connect()
        client.sign_in(password=password)
        _complete_telegram_login(request, client, connection)
    except Exception as exc:  # noqa: BLE001
        messages.error(
            request,
            _("Xatolik: parol noto'g'ri bo'lishi mumkin (%(error)s)") % {"error": exc},
        )
    finally:
        client.disconnect()


@superadmin_required
@require_POST
def telegram_send_code(request):
    _send_code_logic(request, _main_workspace(request).telegram_connection)
    return redirect("assistant:telegram_account")


@superadmin_required
@require_POST
def telegram_verify_code(request):
    _verify_code_logic(request, _main_workspace(request).telegram_connection)
    return redirect("assistant:telegram_account")


@superadmin_required
@require_POST
def telegram_verify_password(request):
    _verify_password_logic(request, _main_workspace(request).telegram_connection)
    return redirect("assistant:telegram_account")


def _cancel_pending_login(request, connection):
    """Kod yoki 2FA parol kutilayotgan (hali ulanmagan) holatni bekor qiladi — masalan
    noto'g'ri raqam kiritilgan bo'lsa, foydalanuvchi raqam kiritish bosqichiga qaytadi."""
    if connection.status in ("pending_code", "pending_password"):
        _reset_connection(connection)
        messages.info(request, _("Bekor qilindi. Telefon raqamini qaytadan kiriting."))


def _disconnect_telegram_account(connection):
    """Telethon sessiyasini tugatib, TelegramAccountConnection'ni tozalaydi.
    Ham super admin, ham biznes admin uzish tugmasi shu funksiyani ishlatadi."""

    if connection.session_string:
        try:
            client = _telethon_client(connection.session_string)
            client.connect()
            client.log_out()
            client.disconnect()
        except Exception:  # noqa: BLE001
            pass  # sessiya allaqachon yaroqsiz bo'lishi mumkin — baribir tozalaymiz

    _reset_connection(connection)


@superadmin_required
@require_POST
def telegram_cancel(request):
    _cancel_pending_login(request, _main_workspace(request).telegram_connection)
    return redirect("assistant:telegram_account")


@superadmin_required
@require_POST
def telegram_disconnect(request):
    _disconnect_telegram_account(_main_workspace(request).telegram_connection)
    messages.success(request, _("Telegram akkaunt uzildi."))
    return redirect("assistant:telegram_account")


# ---------------------------------------------------------------------------
# Telegram akkaunt — biznes admin panelida ham to'liq ishlaydi (holat, ulash
# va uzish). Mantiq super admin bilan bir xil (_send_code_logic va h.k.),
# faqat ruxsat darajasi (@login_required) va redirect manzili farqlanadi.
# Har bir foydalanuvchi faqat o'z ish maydonining akkauntini ulaydi/uzadi.
# ---------------------------------------------------------------------------

@login_required
def telegram_status(request):
    connection = _workspace(request).telegram_connection
    api_configured = bool(settings.TELEGRAM_API_ID and settings.TELEGRAM_API_HASH)
    return render(request, "assistant/telegram_status.html", {
        "connection": connection,
        "api_configured": api_configured,
    })


@login_required
@require_POST
def telegram_send_code_business(request):
    _send_code_logic(request, _workspace(request).telegram_connection)
    return redirect("assistant:telegram_status")


@login_required
@require_POST
def telegram_verify_code_business(request):
    _verify_code_logic(request, _workspace(request).telegram_connection)
    return redirect("assistant:telegram_status")


@login_required
@require_POST
def telegram_verify_password_business(request):
    _verify_password_logic(request, _workspace(request).telegram_connection)
    return redirect("assistant:telegram_status")


@login_required
@require_POST
def telegram_cancel_business(request):
    _cancel_pending_login(request, _workspace(request).telegram_connection)
    return redirect("assistant:telegram_status")


@login_required
@require_POST
def telegram_disconnect_business(request):
    _disconnect_telegram_account(_workspace(request).telegram_connection)
    messages.success(request, _("Telegram akkaunt uzildi."))
    return redirect("assistant:telegram_status")
