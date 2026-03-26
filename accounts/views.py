import json
from datetime import timedelta
from decimal import Decimal
from calendar import monthcalendar
from zoneinfo import ZoneInfo

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.forms import modelformset_factory
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST, require_http_methods

from .forms import (
    FirmForm,
    JobberForm,
    JobberTypeForm,
    LocationForm,
    MaterialForm,
    MaterialShadeForm,
    MaterialTypeForm,
    PartyForm,
    VendorForm,
    YarnPurchaseOrderForm,
    YarnPurchaseOrderItemFormSet,
)
from .models import (
    Firm,
    Jobber,
    JobberType,
    Location,
    Material,
    MaterialShade,
    MaterialType,
    Party,
    UserExtra,
    Vendor,
    YarnPurchaseOrder,
    YarnPurchaseOrderItem,
)


def _is_embed(request) -> bool:
    return (
        request.GET.get("embed") == "1"
        or request.POST.get("embed") == "1"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )


def _next_yarn_po_number() -> str:
    last = YarnPurchaseOrder.objects.order_by("-id").first()
    next_id = (last.id + 1) if last else 1
    return f"YPO-{next_id:04d}"


def _firm_address(firm):
    if not firm:
        return ""
    parts = [firm.address_line, firm.city, firm.state, firm.pincode]
    return ", ".join([p for p in parts if p])


def _recalculate_yarn_po(po: YarnPurchaseOrder):
    subtotal = Decimal("0")
    total_weight = Decimal("0")

    for item in po.items.all():
        qty = item.quantity or Decimal("0")
        rate = item.rate or Decimal("0")
        if not item.final_amount:
            item.final_amount = qty * rate
            item.save(update_fields=["final_amount"])
        subtotal += item.final_amount or Decimal("0")
        total_weight += qty

    discount_percent = po.discount_percent or Decimal("0")
    others = po.others or Decimal("0")
    cgst_percent = po.cgst_percent or Decimal("0")
    sgst_percent = po.sgst_percent or Decimal("0")

    after_discount_value = subtotal - (subtotal * discount_percent / Decimal("100"))
    tax_value = after_discount_value * (cgst_percent + sgst_percent) / Decimal("100")
    grand_total = after_discount_value + others + tax_value

    po.total_weight = total_weight
    po.subtotal = subtotal
    po.after_discount_value = after_discount_value
    po.grand_total = grand_total
    if not po.system_number:
        po.system_number = _next_yarn_po_number()
    po.save(
        update_fields=[
            "system_number",
            "total_weight",
            "subtotal",
            "after_discount_value",
            "grand_total",
            "updated_at",
        ]
    )


def _can_review_yarn_po(user):
    return bool(
        user.is_superuser
        or user.is_staff
        or user.username.lower() == "admin"
    )


@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    error = None

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")

        if not username or not email or not password:
            error = "Username, email and password are required."
        elif password != password2:
            error = "Passwords do not match."
        elif User.objects.filter(username=username).exists():
            error = "Username already taken."
        elif User.objects.filter(email=email).exists():
            error = "Email already registered."
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            return redirect("accounts:dashboard")

    return render(request, "accounts/signup.html", {"error": error})


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    error = None

    if request.method == "POST":
        identifier = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        remember_me = request.POST.get("remember_me")

        username = identifier
        if "@" in identifier:
            user_obj = User.objects.filter(email__iexact=identifier).first()
            username = user_obj.username if user_obj else None

        user = authenticate(request, username=username, password=password) if username else None

        if user is not None:
            login(request, user)

            if remember_me:
                request.session.set_expiry(60 * 60 * 24 * 14)
            else:
                request.session.set_expiry(0)

            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)

            return redirect("accounts:dashboard")

        error = "Invalid username/email or password."

    return render(request, "accounts/login.html", {"error": error})


@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


from calendar import monthcalendar
from zoneinfo import ZoneInfo
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def dashboard_view(request):
    dashboard_tz = ZoneInfo("Asia/Kolkata")
    now_local = timezone.now().astimezone(dashboard_tz)
    hour = now_local.hour

    if 5 <= hour < 12:
        greeting = "Good morning"
    elif 12 <= hour < 17:
        greeting = "Good afternoon"
    elif 17 <= hour < 21:
        greeting = "Good evening"
    else:
        greeting = "Good night"

    month_weeks = monthcalendar(now_local.year, now_local.month)
    calendar_weeks = []

    for week in month_weeks:
        calendar_weeks.append([
            {
                "day": day,
                "is_current_day": day == now_local.day,
                "is_empty": day == 0,
            }
            for day in week
        ])

    return render(
        request,
        "accounts/dashboard.html",
        {
            "greeting": greeting,
            "current_month_label": now_local.strftime("%B %Y"),
            "current_date_label": now_local.strftime("%d %b %Y"),
            "current_time_label": now_local.strftime("%I:%M %p"),
            "calendar_weeks": calendar_weeks,
        },
    )


@login_required
def utilities_view(request):
    return render(request, "accounts/utilities.html")


@login_required
def users_list_view(request):
    q = (request.GET.get("q") or "").strip()
    qs = User.objects.select_related("userextra").all().order_by("-date_joined")

    if q:
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(userextra__phone__icontains=q)
            | Q(userextra__designation__icontains=q)
        )

    return render(request, "accounts/users_list.html", {"users": qs, "q": q})


@login_required
def developer_stats_view(request):
    now = timezone.now()

    total_users = User.objects.count()

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    new_today = User.objects.filter(date_joined__gte=today_start).count()

    week_start = now - timedelta(days=7)
    new_7_days = User.objects.filter(date_joined__gte=week_start).count()

    active_24h = User.objects.filter(last_login__gte=now - timedelta(hours=24)).count()
    active_7d = User.objects.filter(last_login__gte=now - timedelta(days=7)).count()

    return render(
        request,
        "accounts/developer_stats.html",
        {
            "total_users": total_users,
            "new_today": new_today,
            "new_7_days": new_7_days,
            "active_24h": active_24h,
            "active_7d": active_7d,
        },
    )


@login_required
@require_POST
def profile_save(request):
    u = request.user

    u.first_name = request.POST.get("first_name", "").strip()
    u.last_name = request.POST.get("last_name", "").strip()
    u.email = request.POST.get("email", "").strip()
    u.save()

    extra, _ = UserExtra.objects.get_or_create(user=u)
    extra.phone = request.POST.get("phone", "").strip()
    extra.address = request.POST.get("address", "").strip()
    extra.save()

    return JsonResponse({"ok": True, "message": "Profile saved ✅"})


# ==========================
# JOBBERS (embed supported)
# ==========================
@login_required
def jobber_list(request):
    q = (request.GET.get("q") or "").strip()
    qs = Jobber.objects.filter(owner=request.user).select_related("jobber_type")

    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(phone__icontains=q)
            | Q(email__icontains=q)
            | Q(role__icontains=q)
            | Q(jobber_type__name__icontains=q)
        )

    qs = qs.order_by("name")

    all_jobbers = Jobber.objects.filter(owner=request.user)
    stats = {
        "total": all_jobbers.count(),
        "active": all_jobbers.filter(is_active=True).count(),
        "inactive": all_jobbers.filter(is_active=False).count(),
        "types": JobberType.objects.filter(owner=request.user).count(),
    }

    template = "accounts/jobbers/embed_list.html" if _is_embed(request) else "accounts/jobbers/list.html"
    return render(request, template, {
        "jobbers": qs,
        "q": q,
        "stats": stats,
    })

@login_required
@require_http_methods(["GET", "POST"])
def jobber_delete(request, pk):
    jobber = get_object_or_404(Jobber, pk=pk, owner=request.user)

    if request.method == "POST":
        jobber.delete()
        url = reverse("accounts:jobber_list")
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = "accounts/jobbers/confirm_delete.html"
    return render(request, template, {"jobber": jobber})
@login_required
@require_http_methods(["GET", "POST"])
def jobber_create(request):
    form = JobberForm(request.POST or None)
    if "jobber_type" in form.fields:
        form.fields["jobber_type"].queryset = JobberType.objects.filter(owner=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = reverse("accounts:jobber_list")
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = "accounts/jobbers/embed_form.html" if _is_embed(request) else "accounts/jobbers/form.html"
    return render(request, template, {"form": form, "mode": "add"})


@login_required
@require_http_methods(["GET", "POST"])
def jobber_update(request, pk):
    jobber = get_object_or_404(Jobber, pk=pk, owner=request.user)
    form = JobberForm(request.POST or None, instance=jobber)
    if "jobber_type" in form.fields:
        form.fields["jobber_type"].queryset = JobberType.objects.filter(owner=request.user)

    if request.method == "POST" and form.is_valid():
        form.save()

        url = reverse("accounts:jobber_list")
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = "accounts/jobbers/embed_form.html" if _is_embed(request) else "accounts/jobbers/form.html"
    return render(request, template, {"form": form, "mode": "edit", "jobber": jobber})


@login_required
@require_http_methods(["GET", "POST"])
def jobber_delete(request, pk):
    jobber = get_object_or_404(Jobber, pk=pk, owner=request.user)

    if request.method == "POST":
        jobber.delete()
        url = reverse("accounts:jobber_list")
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = "accounts/jobbers/embed_confirm_delete.html" if _is_embed(request) else "accounts/jobbers/confirm_delete.html"
    return render(request, template, {"jobber": jobber})


@login_required
@require_http_methods(["GET", "POST"])
def jobbertype_list_create(request):
    types = (
        JobberType.objects
        .filter(owner=request.user)
        .annotate(jobber_count=Count("jobber"))
        .order_by("name")
    )

    if request.method == "POST":
        form = JobberTypeForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()

            url = reverse("accounts:jobbertype_list")
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)
    else:
        form = JobberTypeForm()

    context = {
        "types": types,
        "form": form,
        "type_stats": {
            "total_types": JobberType.objects.filter(owner=request.user).count(),
            "linked_jobbers": Jobber.objects.filter(owner=request.user, jobber_type__isnull=False).count(),
        }
    }

    template = "accounts/jobbers/embed_types.html" if _is_embed(request) else "accounts/jobbers/types.html"
    return render(request, template, context)


# ==========================
# MATERIALS (embed supported)
# ==========================
@login_required
def material_kind_picker(request):
    ctx = {
        "kind_choices": Material.MATERIAL_KIND_CHOICES,
    }
    tpl = (
        "accounts/materials/kind_picker_embed.html"
        if _is_embed(request)
        else "accounts/materials/kind_picker_page.html"
    )
    return render(request, tpl, ctx)


@login_required
@require_http_methods(["GET", "POST"])
def material_create(request):
    allowed_kinds = {value for value, _ in Material.MATERIAL_KIND_CHOICES}
    selected_kind = (
        request.GET.get("kind")
        or request.POST.get("material_kind")
        or ""
    ).strip()

    if request.method == "GET" and selected_kind not in allowed_kinds:
        ctx = {"kind_choices": Material.MATERIAL_KIND_CHOICES}
        tpl = (
            "accounts/materials/kind_picker_embed.html"
            if _is_embed(request)
            else "accounts/materials/kind_picker_page.html"
        )
        return render(request, tpl, ctx)

    if request.method == "POST":
        form = MaterialForm(
            request.POST,
            request.FILES,
            user=request.user,
            initial_kind=selected_kind,
        )

        if form.is_valid():
            form.save()
            url = reverse("accounts:material_list")
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)
    else:
        form = MaterialForm(
            user=request.user,
            initial_kind=selected_kind,
            initial={"material_kind": selected_kind},
        )

    ctx = {
        "form": form,
        "mode": "create",
        "selected_kind": selected_kind,
    }
    tpl = "accounts/materials/form_embed.html" if _is_embed(request) else "accounts/materials/form_page.html"
    return render(request, tpl, ctx)


@login_required
@require_http_methods(["GET", "POST"])
def material_edit(request, pk: int):
    material = get_object_or_404(
        Material.objects.select_related("yarn", "greige", "finished", "trim"),
        pk=pk,
    )

    if request.method == "POST":
        form = MaterialForm(
            request.POST,
            request.FILES,
            instance=material,
            user=request.user,
            initial_kind=material.material_kind,
        )

        if form.is_valid():
            form.save()
            url = reverse("accounts:material_list")
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)
    else:
        form = MaterialForm(
            instance=material,
            user=request.user,
            initial_kind=material.material_kind,
        )

    ctx = {
        "form": form,
        "mode": "edit",
        "material": material,
        "selected_kind": material.material_kind,
    }
    tpl = "accounts/materials/form_embed.html" if _is_embed(request) else "accounts/materials/form_page.html"
    return render(request, tpl, ctx)


@login_required
def material_list(request):
    q = (request.GET.get("q") or "").strip()
    selected_type = (request.GET.get("type") or "").strip()

    qs = Material.objects.all().order_by("-id").select_related("yarn", "greige", "finished", "trim")

    if selected_type.isdigit():
        qs = qs.filter(material_type_id=int(selected_type))

    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(remarks__icontains=q)
        )

    ctx = {
        "materials": qs,
        "q": q,
        "selected_type": selected_type,
        "type_choices": MaterialType.objects.filter(owner=request.user).order_by("name"),
    }

    tpl = "accounts/materials/list_embed.html" if _is_embed(request) else "accounts/materials/list_page.html"
    return render(request, tpl, ctx)


@login_required
@require_POST
def material_delete(request, pk: int):
    material = get_object_or_404(Material, pk=pk)
    material.delete()

    url = reverse("accounts:material_list")
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)


# ==========================
# PARTIES (embed supported)
# ==========================
@login_required
def party_list(request):
    parties = Party.objects.all().order_by("-id")
    tpl = "accounts/parties/list_embed.html" if _is_embed(request) else "accounts/parties/list.html"
    return render(request, tpl, {"parties": parties})


@login_required
@require_http_methods(["GET", "POST"])
def party_create(request):
    form = PartyForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        url = reverse("accounts:party_list")
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    tpl = "accounts/parties/form_embed.html" if _is_embed(request) else "accounts/parties/form.html"
    return render(request, tpl, {"form": form, "mode": "add"})


@login_required
@require_http_methods(["GET", "POST"])
def party_update(request, pk):
    party = get_object_or_404(Party, pk=pk)
    form = PartyForm(request.POST or None, instance=party)

    if request.method == "POST" and form.is_valid():
        form.save()
        url = reverse("accounts:party_list")
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    tpl = "accounts/parties/form_embed.html" if _is_embed(request) else "accounts/parties/form.html"
    return render(request, tpl, {"form": form, "mode": "edit", "party": party})


@login_required
@require_POST
def party_delete(request, pk):
    party = get_object_or_404(Party, pk=pk)
    party.delete()

    url = reverse("accounts:party_list")
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)


# ==========================
# LOCATIONS (embed supported)
# ==========================
@login_required
def location_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = Location.objects.filter(owner=request.user)
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(city__icontains=q)
            | Q(state__icontains=q)
            | Q(address__icontains=q)
            | Q(pincode__icontains=q)
        )

    ctx = {"locations": qs, "q": q}
    tpl = "accounts/locations/list_embed.html" if _is_embed(request) else "accounts/locations/list.html"
    return render(request, tpl, ctx)


@login_required
@require_http_methods(["GET", "POST"])
def location_create(request):
    form = LocationForm(request.POST or None)

    if request.method == "POST":
        form.instance.owner = request.user

        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()

            url = reverse("accounts:location_list")
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)

    tpl = "accounts/locations/form_embed.html" if _is_embed(request) else "accounts/locations/form.html"
    return render(request, tpl, {"form": form, "mode": "add"})


@login_required
@require_http_methods(["GET", "POST"])
def location_update(request, pk: int):
    loc = get_object_or_404(Location, pk=pk, owner=request.user)
    form = LocationForm(request.POST or None, instance=loc)

    if request.method == "POST" and form.is_valid():
        form.save()

        url = reverse("accounts:location_list")
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    ctx = {"form": form, "mode": "edit", "location": loc}
    tpl = "accounts/locations/form_embed.html" if _is_embed(request) else "accounts/locations/form.html"
    return render(request, tpl, ctx)


@login_required
@require_POST
def location_delete(request, pk: int):
    loc = get_object_or_404(Location, pk=pk, owner=request.user)
    loc.delete()

    url = reverse("accounts:location_list")
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)


# ==========================
# FIRM (single per user)
# ==========================
@login_required
def firm_list(request):
    firm = Firm.objects.filter(owner=request.user).first()
    firms = [firm] if firm else []

    tpl = "accounts/firms/list_embed.html" if _is_embed(request) else "accounts/firms/list.html"
    return render(request, tpl, {"firms": firms})


@login_required
@require_http_methods(["GET", "POST"])
def firm_create(request):
    existing = Firm.objects.filter(owner=request.user).first()

    if existing:
        url = reverse("accounts:firm_edit", args=[existing.id])
        if request.GET.get("embed") == "1":
            url += "?embed=1"
        return redirect(url)

    form = FirmForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        if _is_embed(request):
            return JsonResponse({"ok": True, "url": reverse("accounts:firm_list")})
        return redirect("accounts:firm_list")

    tpl = "accounts/firms/form_embed.html" if _is_embed(request) else "accounts/firms/form.html"
    return render(request, tpl, {"form": form, "mode": "add"})


@login_required
@require_http_methods(["GET", "POST"])
def firm_update(request, pk: int):
    firm = get_object_or_404(Firm, pk=pk, owner=request.user)
    form = FirmForm(request.POST or None, instance=firm)

    if request.method == "POST" and form.is_valid():
        form.save()

        if _is_embed(request):
            return JsonResponse({"ok": True, "url": reverse("accounts:firm_list")})
        return redirect("accounts:firm_list")

    tpl = "accounts/firms/form_embed.html" if _is_embed(request) else "accounts/firms/form.html"
    return render(request, tpl, {"form": form, "mode": "edit", "firm": firm})


@login_required
@require_POST
def firm_delete(request, pk: int):
    firm = get_object_or_404(Firm, pk=pk, owner=request.user)
    firm.delete()

    if _is_embed(request):
        return JsonResponse({"ok": True, "url": reverse("accounts:firm_list")})
    return redirect("accounts:firm_list")


@login_required
@require_http_methods(["GET", "POST"])
def firm_view(request):
    firm = Firm.objects.filter(owner=request.user).first()
    if firm is None:
        firm = Firm(owner=request.user)

    form = FirmForm(request.POST or None, instance=firm)

    if request.method == "POST" and form.is_valid():
        form.save()

        if _is_embed(request):
            return JsonResponse({"ok": True, "url": reverse("accounts:firm")})
        return redirect("accounts:firm")

    template = "accounts/firm/form_embed.html" if _is_embed(request) else "accounts/firm/form.html"
    return render(request, template, {"form": form})


# ==========================
# MATERIAL SHADES (Utilities)
# ==========================
@login_required
def materialshade_list(request):
    q = (request.GET.get("q") or "").strip()
    selected_kind = (request.GET.get("kind") or "").strip()

    qs = MaterialShade.objects.filter(owner=request.user).order_by("name")

    if selected_kind:
        qs = qs.filter(material_kind=selected_kind)

    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(code__icontains=q)
            | Q(notes__icontains=q)
        )

    ctx = {
        "shades": qs,
        "q": q,
        "selected_kind": selected_kind,
        "kind_choices": Material.MATERIAL_KIND_CHOICES,
    }
    tpl = "accounts/material_shades/list_embed.html" if _is_embed(request) else "accounts/material_shades/list.html"
    return render(request, tpl, ctx)


def _shade_list_url(request):
    url = reverse("accounts:materialshade_list")
    if _is_embed(request):
        url += "?embed=1"
    return url


@login_required
@require_http_methods(["GET", "POST"])
def materialshade_create(request):
    form = MaterialShadeForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _shade_list_url(request)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "url": url})

        return redirect(url)

    tpl = "accounts/material_shades/form_embed.html" if _is_embed(request) else "accounts/material_shades/form.html"
    return render(request, tpl, {"form": form, "mode": "add"})


@login_required
@require_http_methods(["GET", "POST"])
def materialshade_update(request, pk: int):
    shade = get_object_or_404(MaterialShade, pk=pk, owner=request.user)
    form = MaterialShadeForm(request.POST or None, instance=shade)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _shade_list_url(request)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "url": url})

        return redirect(url)

    tpl = "accounts/material_shades/form_embed.html" if _is_embed(request) else "accounts/material_shades/form.html"
    return render(request, tpl, {"form": form, "mode": "edit", "shade": shade})


@login_required
@require_POST
def materialshade_delete(request, pk: int):
    shade = get_object_or_404(MaterialShade, pk=pk, owner=request.user)
    shade.delete()

    url = _shade_list_url(request)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "url": url})

    return redirect(url)


# ==========================
# MATERIAL TYPES (Utilities)
# ==========================
@login_required
def materialtype_list(request):
    q = (request.GET.get("q") or "").strip()
    selected_kind = (request.GET.get("kind") or "").strip()

    qs = MaterialType.objects.filter(owner=request.user).order_by("name")

    if selected_kind:
        qs = qs.filter(material_kind=selected_kind)

    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
        )

    ctx = {
        "types": qs,
        "q": q,
        "selected_kind": selected_kind,
        "kind_choices": Material.MATERIAL_KIND_CHOICES,
    }
    tpl = "accounts/material_types/list_embed.html" if _is_embed(request) else "accounts/material_types/list.html"
    return render(request, tpl, ctx)


@login_required
@require_http_methods(["GET", "POST"])
def materialtype_create(request):
    form = MaterialTypeForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = reverse("accounts:materialtype_list")
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    tpl = "accounts/material_types/form_embed.html" if _is_embed(request) else "accounts/material_types/form.html"
    return render(request, tpl, {"form": form, "mode": "add"})


@login_required
@require_http_methods(["GET", "POST"])
def materialtype_update(request, pk: int):
    mt = get_object_or_404(MaterialType, pk=pk, owner=request.user)
    form = MaterialTypeForm(request.POST or None, instance=mt)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = reverse("accounts:materialtype_list")
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    tpl = "accounts/material_types/form_embed.html" if _is_embed(request) else "accounts/material_types/form.html"
    return render(request, tpl, {"form": form, "mode": "edit", "material_type": mt})


@login_required
@require_POST
def materialtype_delete(request, pk: int):
    mt = get_object_or_404(MaterialType, pk=pk, owner=request.user)
    mt.delete()

    url = reverse("accounts:materialtype_list")
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)


# ==========================
# VENDORS (embed supported)
# ==========================
@login_required
def vendor_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = Vendor.objects.filter(owner=request.user)
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(contact_person__icontains=q)
            | Q(phone__icontains=q)
            | Q(email__icontains=q)
            | Q(gst_number__icontains=q)
        )

    ctx = {"vendors": qs.order_by("name"), "q": q}
    tpl = "accounts/vendors/list_embed.html" if _is_embed(request) else "accounts/vendors/list.html"
    return render(request, tpl, ctx)


@login_required
@require_http_methods(["GET", "POST"])
def vendor_create(request):
    default_firm = Firm.objects.filter(owner=request.user).first()

    form = VendorForm(request.POST or None)

    if "firm" in form.fields:
        form.fields["firm"].queryset = Firm.objects.filter(owner=request.user).order_by("firm_name")
        if request.method == "GET" and default_firm:
            form.fields["firm"].initial = default_firm.pk

    if request.method == "POST":
        form.instance.owner = request.user

        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user

            if hasattr(obj, "firm_id") and not obj.firm_id and default_firm:
                obj.firm = default_firm

            obj.save()
            url = reverse("accounts:vendor_list")
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)

    tpl = "accounts/vendors/form_embed.html" if _is_embed(request) else "accounts/vendors/form.html"
    return render(request, tpl, {"form": form, "mode": "add"})


@login_required
@require_http_methods(["GET", "POST"])
def vendor_update(request, pk: int):
    vendor = get_object_or_404(Vendor, pk=pk, owner=request.user)
    default_firm = Firm.objects.filter(owner=request.user).first()

    form = VendorForm(request.POST or None, instance=vendor)

    if "firm" in form.fields:
        form.fields["firm"].queryset = Firm.objects.filter(owner=request.user).order_by("firm_name")
        if request.method == "GET" and not getattr(vendor, "firm_id", None) and default_firm:
            form.fields["firm"].initial = default_firm.pk

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)

        if hasattr(obj, "firm_id") and not obj.firm_id and default_firm:
            obj.firm = default_firm

        obj.save()
        url = reverse("accounts:vendor_list")
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    tpl = "accounts/vendors/form_embed.html" if _is_embed(request) else "accounts/vendors/form.html"
    return render(request, tpl, {"form": form, "mode": "edit", "vendor": vendor})


@login_required
@require_POST
def vendor_delete(request, pk: int):
    vendor = get_object_or_404(Vendor, pk=pk, owner=request.user)
    vendor.delete()

    url = reverse("accounts:vendor_list")
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)


# ==========================
# YARN PURCHASE ORDERS
# ==========================
@login_required
def yarnpo_list(request):
    q = (request.GET.get("q") or "").strip()
    qs = (
        YarnPurchaseOrder.objects
        .filter(owner=request.user)
        .select_related("vendor", "firm", "reviewed_by")
        .prefetch_related("items__material")
    )

    if q:
        qs = qs.filter(
            Q(system_number__icontains=q)
            | Q(po_number__icontains=q)
            | Q(vendor__name__icontains=q)
            | Q(firm__firm_name__icontains=q)
            | Q(items__material__name__icontains=q)
        ).distinct()

    return render(
        request,
        "accounts/yarn_po/list.html",
        {
            "orders": qs.order_by("-id"),
            "q": q,
            "can_review_yarn_po": _can_review_yarn_po(request.user),
        },
    )


def _bind_yarnpo_item_formset(request, instance=None):
    if request.method == "POST":
        formset = YarnPurchaseOrderItemFormSet(request.POST, instance=instance, prefix="items")
    else:
        formset = YarnPurchaseOrderItemFormSet(instance=instance, prefix="items")

    yarn_qs = (
        Material.objects
        .filter(material_type__material_kind="yarn")
        .select_related("material_type", "material_shade")
        .order_by("material_type__name", "name")
    )

    def yarn_label(obj):
        type_name = obj.material_type.name if getattr(obj, "material_type", None) else "Yarn Type"
        shade_name = obj.material_shade.name if getattr(obj, "material_shade", None) else ""
        extra = f" · {shade_name}" if shade_name else ""
        return f"{type_name} — {obj.name}{extra}"

    for form in formset.forms:
        if "material" in form.fields:
            form.fields["material"].queryset = yarn_qs
            form.fields["material"].label_from_instance = yarn_label

    if hasattr(formset, "empty_form") and "material" in formset.empty_form.fields:
        formset.empty_form.fields["material"].queryset = yarn_qs
        formset.empty_form.fields["material"].label_from_instance = yarn_label

    return formset


@login_required
@require_http_methods(["GET", "POST"])
def yarnpo_create(request):
    default_firm = Firm.objects.filter(owner=request.user).first()

    po = YarnPurchaseOrder(owner=request.user)

    if request.method == "GET" and default_firm:
        po.firm = default_firm
        po.shipping_address = _firm_address(default_firm)

    form = YarnPurchaseOrderForm(request.POST or None, user=request.user, instance=po)
    formset = _bind_yarnpo_item_formset(request, instance=po)

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        po = form.save(commit=False)
        po.owner = request.user

        if default_firm:
            po.firm = default_firm

        if not po.system_number:
            po.system_number = _next_yarn_po_number()

        if po.firm and not po.shipping_address:
            po.shipping_address = _firm_address(po.firm)

        po.save()
        formset.instance = po
        formset.save()
        _recalculate_yarn_po(po)
        return redirect("accounts:yarnpo_list")

    return render(request, "accounts/yarn_po/form.html", {
        "form": form,
        "formset": formset,
        "mode": "add",
        "po_obj": po,
        "system_number_preview": po.system_number or _next_yarn_po_number(),
        "auto_firm_name": default_firm.firm_name if default_firm else "",
    })


@login_required
@require_http_methods(["GET", "POST"])
def yarnpo_update(request, pk: int):
    po = get_object_or_404(
        YarnPurchaseOrder.objects.select_related("vendor", "firm"),
        pk=pk,
        owner=request.user
    )

    default_firm = Firm.objects.filter(owner=request.user).first()
    display_firm = po.firm or default_firm

    if request.method == "GET" and display_firm and not po.firm:
        po.firm = display_firm
        if not po.shipping_address:
            po.shipping_address = _firm_address(display_firm)

    form = YarnPurchaseOrderForm(request.POST or None, user=request.user, instance=po)
    formset = _bind_yarnpo_item_formset(request, instance=po)

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        po = form.save(commit=False)
        po.owner = request.user

        if default_firm:
            po.firm = default_firm

        if po.firm and not po.shipping_address:
            po.shipping_address = _firm_address(po.firm)

        po.save()
        formset.instance = po
        formset.save()
        _recalculate_yarn_po(po)
        return redirect("accounts:yarnpo_list")

    return render(request, "accounts/yarn_po/form.html", {
        "form": form,
        "formset": formset,
        "mode": "edit",
        "po_obj": po,
        "system_number_preview": po.system_number,
        "auto_firm_name": display_firm.firm_name if display_firm else "",
    })


@login_required
@require_POST
def yarnpo_delete(request, pk: int):
    po = get_object_or_404(YarnPurchaseOrder, pk=pk, owner=request.user)
    po.delete()
    return redirect("accounts:yarnpo_list")


@login_required
@require_http_methods(["GET", "POST"])
def yarnpo_review(request, pk: int):
    po = get_object_or_404(
        YarnPurchaseOrder.objects
        .select_related("vendor", "firm", "reviewed_by")
        .prefetch_related("items__material"),
        pk=pk,
    )

    can_review = _can_review_yarn_po(request.user)

    if request.method == "POST":
        if not can_review:
            return HttpResponseForbidden("You are not allowed to review this PO.")

        action = (request.POST.get("action") or "").strip().lower()

        if action == "approve":
            po.approval_status = YarnPurchaseOrder.ApprovalStatus.APPROVED
        elif action == "reject":
            po.approval_status = YarnPurchaseOrder.ApprovalStatus.REJECTED
        else:
            return redirect("accounts:yarnpo_review", pk=po.pk)

        po.reviewed_by = request.user
        po.reviewed_at = timezone.now()
        po.save(update_fields=["approval_status", "reviewed_by", "reviewed_at"])

        return redirect("accounts:yarnpo_list")

    return render(
        request,
        "accounts/yarn_po/review.html",
        {
            "po": po,
            "can_review_yarn_po": can_review,
        },
    )


# ============================================
@login_required
@require_POST
def firm_save(request):
    firm = Firm.objects.filter(owner=request.user).first()
    if firm is None:
        firm = Firm(owner=request.user)

    firm_name = (request.POST.get("firm_name") or "").strip()
    firm_type = (request.POST.get("firm_type") or "").strip()

    if not firm_name:
        return JsonResponse({"ok": False, "message": "Firm Name is required."})
    if not firm_type:
        return JsonResponse({"ok": False, "message": "Firm Type is required."})

    firm.firm_name = firm_name
    firm.firm_type = firm_type

    reg = (request.POST.get("registration_number") or "").strip()
    if hasattr(firm, "registration_number"):
        firm.registration_number = reg
    elif hasattr(firm, "cin_number"):
        firm.cin_number = reg

    for key, model_field in [
        ("gst_number", "gst_number"),
        ("email", "email"),
        ("phone", "phone"),
        ("city", "city"),
        ("state", "state"),
        ("country", "country"),
    ]:
        if hasattr(firm, model_field):
            setattr(firm, model_field, (request.POST.get(key) or "").strip())

    addr = request.POST.get("address") or ""
    if hasattr(firm, "address_line"):
        firm.address_line = addr
    elif hasattr(firm, "address"):
        firm.address = addr

    firm.save()

    created_at_display = ""
    if hasattr(firm, "created_at") and firm.created_at:
        created_at_display = timezone.localtime(firm.created_at).strftime("%d %b %Y, %H:%M")

    return JsonResponse({
        "ok": True,
        "message": "Firm saved ✅",
        "firm_name": firm.firm_name,
        "created_at_display": created_at_display,
    })


# =================================================================
def _jobbertype_qs_for_user(request):
    qs = JobberType.objects.all()
    if hasattr(JobberType, "owner") and request.user.is_authenticated:
        qs = qs.filter(owner=request.user)
    return qs


@login_required
def jobbertype_edit(request, pk):
    jt = get_object_or_404(_jobbertype_qs_for_user(request), pk=pk)

    if request.method == "POST":
        form = JobberTypeForm(request.POST, instance=jt)
        if form.is_valid():
            obj = form.save(commit=False)
            if hasattr(obj, "owner_id") and not obj.owner_id:
                obj.owner = request.user
            obj.save()

            url = reverse("accounts:jobbertype_list")
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)
    else:
        form = JobberTypeForm(instance=jt)

    template = "accounts/jobbers/jobbertype_edit_embed.html" if _is_embed(request) else "accounts/jobbers/jobbertype_edit.html"
    return render(request, template, {
        "form": form,
        "obj": jt,
    })


@login_required
@require_POST
def jobbertype_delete(request, pk):
    jt = get_object_or_404(_jobbertype_qs_for_user(request), pk=pk)
    jt.delete()

    url = reverse("accounts:jobbertype_list")
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)


@login_required
def po_home(request):
    return render(request, "accounts/po/index.html")