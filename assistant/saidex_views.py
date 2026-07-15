"""
Admin panelning "Saidex" bo'limi — ochiq (public) landing page kontentini
(tariflar, qilingan ishlar, mijozlar fikri, sayt sozlamalari) boshqarish.
Barchasi document_list/leads_list bilan bir xil oddiy andoza: ro'yxat +
qo'shish formasi + o'chirish tugmasi.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from landing.models import LandingSettings, Tariff, PortfolioItem, Testimonial
from landing.forms import LandingSettingsForm, TariffForm, PortfolioItemForm, TestimonialForm


@login_required
def saidex_settings(request):
    settings_obj = LandingSettings.get_solo()
    if request.method == "POST":
        form = LandingSettingsForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, _("Sayt sozlamalari saqlandi."))
            return redirect("assistant:saidex_settings")
    else:
        form = LandingSettingsForm(instance=settings_obj)
    return render(request, "assistant/saidex_settings.html", {"form": form})


@login_required
def saidex_tariffs(request):
    if request.method == "POST":
        form = TariffForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Tarif qo'shildi."))
            return redirect("assistant:saidex_tariffs")
    else:
        form = TariffForm()
    tariffs = Tariff.objects.all()
    return render(request, "assistant/saidex_tariffs.html", {"tariffs": tariffs, "form": form})


@login_required
@require_POST
def saidex_tariff_delete(request, pk):
    get_object_or_404(Tariff, pk=pk).delete()
    messages.success(request, _("Tarif o'chirildi."))
    return redirect("assistant:saidex_tariffs")


@login_required
def saidex_portfolio(request):
    if request.method == "POST":
        form = PortfolioItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("Ish qo'shildi."))
            return redirect("assistant:saidex_portfolio")
    else:
        form = PortfolioItemForm()
    items = PortfolioItem.objects.all()
    return render(request, "assistant/saidex_portfolio.html", {"items": items, "form": form})


@login_required
@require_POST
def saidex_portfolio_delete(request, pk):
    item = get_object_or_404(PortfolioItem, pk=pk)
    item.image.delete(save=False)
    item.delete()
    messages.success(request, _("Ish o'chirildi."))
    return redirect("assistant:saidex_portfolio")


@login_required
def saidex_testimonials(request):
    if request.method == "POST":
        form = TestimonialForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("Mijoz fikri qo'shildi."))
            return redirect("assistant:saidex_testimonials")
    else:
        form = TestimonialForm()
    testimonials = Testimonial.objects.all()
    return render(request, "assistant/saidex_testimonials.html", {"testimonials": testimonials, "form": form})


@login_required
@require_POST
def saidex_testimonial_delete(request, pk):
    t = get_object_or_404(Testimonial, pk=pk)
    t.avatar.delete(save=False)
    t.delete()
    messages.success(request, _("Mijoz fikri o'chirildi."))
    return redirect("assistant:saidex_testimonials")
