import json
from io import BytesIO
from decimal import Decimal, InvalidOperation
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.db.models import Q, Prefetch, Sum

from datetime import timedelta
from decimal import Decimal
from calendar import monthcalendar
from zoneinfo import ZoneInfo
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .navigation import UTILITIES_GROUPS
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
    YarnPOInwardForm,
    YarnPOReviewForm,
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
    YarnPOInward,
    YarnPOInwardItem,
    YarnPurchaseOrder,
    YarnPurchaseOrderItem,
    GreigePurchaseOrder,
GreigePurchaseOrderItem,
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

def _next_greige_po_number() -> str:
    last = GreigePurchaseOrder.objects.order_by("-id").first()
    next_id = (last.id + 1) if last else 1
    return f"GPO-{next_id:04d}"

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
    form_data = {
        "username": "",
        "email": "",
    }

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")

        form_data.update({
            "username": username,
            "email": email,
        })

        if not username or not email or not password or not password2:
            error = "Username, email, password, and confirm password are required."
        elif password != password2:
            error = "Passwords do not match."
        elif User.objects.filter(username__iexact=username).exists():
            error = "Username already taken."
        elif User.objects.filter(email__iexact=email).exists():
            error = "Email already registered."
        else:
            try:
                validate_email(email)
                temp_user = User(username=username, email=email)
                validate_password(password, user=temp_user)
            except ValidationError as exc:
                error = " ".join(exc.messages)
            else:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )
                login(request, user)
                return redirect("accounts:dashboard")

    return render(
        request,
        "accounts/signup.html",
        {
            "error": error,
            "form_data": form_data,
        },
    )


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
    return render(
        request,
        "accounts/utilities.html",
        {
            "utility_groups": UTILITIES_GROUPS,
        },
    )


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
def _can_access_yarn_po(user, po):
    return bool(_can_review_yarn_po(user) or po.owner_id == user.id)


def _next_yarn_inward_number() -> str:
    last = YarnPOInward.objects.order_by("-id").first()
    next_id = (last.id + 1) if last else 1
    return f"YIN-{next_id:04d}"


def _attach_yarn_po_metrics(po):
    return po

def _build_yarn_po_pdf_response(po):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return HttpResponse(
            "ReportLab is required for PDF generation. Install it with: pip install reportlab",
            status=500,
        )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Yarn Purchase Order - {po.system_number}", styles["Title"]))
    story.append(Spacer(1, 8))

    meta_rows = [
        ["System No", po.system_number],
        ["PO Number", po.po_number or "-"],
        ["PO Date", po.po_date.strftime("%d-%m-%Y") if po.po_date else "-"],
        ["Cancel Date", po.cancel_date.strftime("%d-%m-%Y") if po.cancel_date else "-"],
        ["Vendor", po.vendor.name if po.vendor else "-"],
        ["Firm", po.firm.firm_name if po.firm else "-"],
        ["Shipping Address", po.shipping_address or "-"],
        ["Status", po.get_approval_status_display()],
    ]

    meta_table = Table(meta_rows, colWidths=[38 * mm, 130 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#dbe4ee")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    item_rows = [["Material", "Quantity", "UOM", "Rate", "Final Amount"]]
    for item in po.items.all():
        item_rows.append([
            item.material.name if item.material else "-",
            str(item.quantity or "0.00"),
            item.unit or "-",
            f"₹{item.rate or '0.00'}",
            f"₹{item.final_amount or '0.00'}",
        ])

    items_table = Table(item_rows, colWidths=[70 * mm, 28 * mm, 22 * mm, 28 * mm, 35 * mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#dbe4ee")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 12))

    summary_rows = [
        ["Sub Total", f"₹{po.subtotal or '0.00'}"],
        ["Discount (%)", str(po.discount_percent or '0')],
        ["After Discount", f"₹{po.after_discount_value or '0.00'}"],
        ["Others", f"₹{po.others or '0.00'}"],
        ["CGST (%)", str(po.cgst_percent or '0')],
        ["SGST (%)", str(po.sgst_percent or '0')],
        ["Grand Total", f"₹{po.grand_total or '0.00'}"],
    ]
    summary_table = Table(summary_rows, colWidths=[48 * mm, 42 * mm], hAlign="RIGHT")
    summary_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#dbe4ee")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)

    if po.remarks:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Remarks", styles["Heading4"]))
        story.append(Paragraph(po.remarks, styles["BodyText"]))

    if po.terms_conditions:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Terms & Conditions", styles["Heading4"]))
        story.append(Paragraph(po.terms_conditions.replace("\n", "<br/>"), styles["BodyText"]))

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{po.system_number}.pdf"'
    return response


@login_required
def yarnpo_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = (
        YarnPurchaseOrder.objects
        .select_related("vendor", "firm", "reviewed_by", "owner")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=YarnPurchaseOrderItem.objects.select_related("material").prefetch_related("inward_items"),
            ),
            Prefetch(
                "inwards",
                queryset=YarnPOInward.objects.prefetch_related("items"),
            ),
        )
    )

    if not _can_review_yarn_po(request.user):
        qs = qs.filter(owner=request.user)

    if q:
        qs = qs.filter(
            Q(system_number__icontains=q)
            | Q(po_number__icontains=q)
            | Q(vendor__name__icontains=q)
            | Q(firm__firm_name__icontains=q)
            | Q(items__material__name__icontains=q)
        ).distinct()

    orders = [_attach_yarn_po_metrics(po) for po in qs.order_by("-id")]

    return render(
        request,
        "accounts/yarn_po/list.html",
        {
            "orders": orders,
            "q": q,
            "can_review_yarn_po": _can_review_yarn_po(request.user),
        },
    )


def _bind_yarnpo_item_formset(request, instance=None):
    if request.method == "POST":
        formset = YarnPurchaseOrderItemFormSet(request.POST, instance=instance, prefix="items")
    else:
        formset = YarnPurchaseOrderItemFormSet(instance=instance, prefix="items")

    yarn_type_qs = MaterialType.objects.filter(
        owner=request.user,
        material_kind="yarn",
    ).order_by("name")

    def type_label(obj):
        return obj.name

    for form in formset.forms:
        if "material_type" in form.fields:
            form.fields["material_type"].queryset = yarn_type_qs
            form.fields["material_type"].label_from_instance = type_label
            form.fields["material_type"].empty_label = "Select Yarn Type"

    if hasattr(formset, "empty_form") and "material_type" in formset.empty_form.fields:
        formset.empty_form.fields["material_type"].queryset = yarn_type_qs
        formset.empty_form.fields["material_type"].label_from_instance = type_label
        formset.empty_form.fields["material_type"].empty_label = "Select Yarn Type"

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
def yarnpo_pdf(request, pk: int):
    po = get_object_or_404(
        YarnPurchaseOrder.objects
        .select_related("vendor", "firm", "owner")
        .prefetch_related(
            Prefetch("items", queryset=YarnPurchaseOrderItem.objects.select_related("material"))
        ),
        pk=pk,
    )

    if not _can_access_yarn_po(request.user, po):
        raise PermissionDenied("You do not have access to this PO.")

    return _build_yarn_po_pdf_response(po)


@login_required
@require_http_methods(["GET", "POST"])
def yarnpo_inward(request, pk: int):
    po = get_object_or_404(
        YarnPurchaseOrder.objects
        .select_related("vendor", "firm", "owner")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=YarnPurchaseOrderItem.objects.select_related("material").prefetch_related("inward_items"),
            ),
            Prefetch(
                "inwards",
                queryset=YarnPOInward.objects.prefetch_related("items__po_item__material"),
            ),
        ),
        pk=pk,
    )

    if not _can_access_yarn_po(request.user, po):
        raise PermissionDenied("You do not have access to this PO.")

    po = _attach_yarn_po_metrics(po)
    item_errors = {}
    line_inputs = {}
    inward_form = YarnPOInwardForm(request.POST or None)

    if request.method == "POST" and inward_form.is_valid():
        line_payload = []

        for item in po.items.all():
            raw_qty = (request.POST.get(f"qty_{item.id}") or "").strip()
            remark = (request.POST.get(f"remark_{item.id}") or "").strip()

            line_inputs[item.id] = {
                "qty": raw_qty,
                "remark": remark,
            }

            if not raw_qty:
                continue

            try:
                qty = Decimal(raw_qty)
            except InvalidOperation:
                item_errors[item.id] = "Enter a valid quantity."
                continue

            if qty <= 0:
                continue

            if qty > item.remaining_qty_total:
                item_errors[item.id] = "Entered quantity is greater than remaining quantity."
                continue

            line_payload.append((item, qty, remark))

        if not line_payload:
            inward_form.add_error(None, "Enter at least one inward quantity.")

        if not inward_form.errors and not item_errors:
            inward = inward_form.save(commit=False)
            inward.owner = request.user
            inward.po = po
            inward.inward_number = _next_yarn_inward_number()
            inward.save()

            bulk_rows = []
            for item, qty, remark in line_payload:
                bulk_rows.append(
                    YarnPOInwardItem(
                        inward=inward,
                        po_item=item,
                        quantity=qty,
                        remark=remark,
                    )
                )
            YarnPOInwardItem.objects.bulk_create(bulk_rows)
            return redirect("accounts:yarnpo_inward", pk=po.pk)

    existing_inwards = po.inwards.all().order_by("-inward_date", "-id")

    return render(
        request,
        "accounts/yarn_po/inward.html",
        {
            "po": po,
            "inward_form": inward_form,
            "item_errors": item_errors,
            "line_inputs": line_inputs,
            "existing_inwards": existing_inwards,
        },
    )

@login_required
def yarn_inward_tracker(request):
    q = (request.GET.get("q") or "").strip()

    qs = (
        YarnPurchaseOrder.objects
        .select_related("vendor", "firm", "owner")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=YarnPurchaseOrderItem.objects.select_related("material").prefetch_related("inward_items"),
            ),
            Prefetch(
                "inwards",
                queryset=YarnPOInward.objects.prefetch_related("items__po_item__material"),
            ),
            "greige_pos",
        )
        .filter(inwards__isnull=False)
        .distinct()
        .order_by("-id")
    )

    if not _can_review_yarn_po(request.user):
        qs = qs.filter(owner=request.user)

    if q:
        qs = qs.filter(
            Q(system_number__icontains=q)
            | Q(po_number__icontains=q)
            | Q(vendor__name__icontains=q)
            | Q(firm__firm_name__icontains=q)
        ).distinct()

    rows = []
    for po in qs:
        po = _attach_yarn_po_metrics(po)

        greige_po = po.greige_pos.order_by("-id").first()

        rows.append({
            "po": po,
            "greige_po": greige_po,
            "greige_started": bool(greige_po),
        })

    return render(
        request,
        "accounts/yarn_po/inward_tracker.html",
        {
            "rows": rows,
            "q": q,
        },
    )


@login_required
@require_http_methods(["POST"])
def generate_greige_po_from_yarn(request, pk: int):
    yarn_po = get_object_or_404(
        YarnPurchaseOrder.objects
        .select_related("vendor", "firm", "owner")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=YarnPurchaseOrderItem.objects.select_related("material").prefetch_related("inward_items")
            )
        ),
        pk=pk,
    )

    if not _can_access_yarn_po(request.user, yarn_po):
        raise PermissionDenied("You do not have access to this Yarn PO.")

    if yarn_po.greige_pos.exists():
        return redirect("accounts:yarn_inward_tracker")

    if yarn_po.total_inward_qty <= 0:
        return redirect("accounts:yarn_inward_tracker")

    greige_po = GreigePurchaseOrder.objects.create(
        owner=request.user,
        system_number=_next_greige_po_number(),
        po_number=yarn_po.po_number or "",
        po_date=timezone.localdate(),
        source_yarn_po=yarn_po,
        vendor=yarn_po.vendor,
        firm=yarn_po.firm,
        remarks=f"Generated from Yarn PO {yarn_po.system_number}",
        total_weight=Decimal("0"),
    )

    total_weight = Decimal("0")
    item_rows = []

    for yarn_item in yarn_po.items.all():
        inward_qty = yarn_item.inward_qty_total or Decimal("0")
        if inward_qty <= 0:
            continue

        yarn_name = yarn_item.material.name if yarn_item.material else "Yarn Item"

        item_rows.append(
            GreigePurchaseOrderItem(
                po=greige_po,
                source_yarn_po_item=yarn_item,
                fabric_name=yarn_name,
                yarn_name=yarn_name,
                unit=yarn_item.unit or "",
                quantity=inward_qty,
                remark=f"Generated from inward qty of {yarn_po.system_number}",
            )
        )
        total_weight += inward_qty

    if not item_rows:
        greige_po.delete()
        return redirect("accounts:yarn_inward_tracker")

    GreigePurchaseOrderItem.objects.bulk_create(item_rows)
    greige_po.total_weight = total_weight
    greige_po.save(update_fields=["total_weight", "updated_at"])

    return redirect("accounts:greigepo_list")


@login_required
def greigepo_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = (
        GreigePurchaseOrder.objects
        .select_related("vendor", "firm", "source_yarn_po", "owner")
        .prefetch_related("items")
        .order_by("-id")
    )

    if not _can_review_yarn_po(request.user):
        qs = qs.filter(owner=request.user)

    if q:
        qs = qs.filter(
            Q(system_number__icontains=q)
            | Q(po_number__icontains=q)
            | Q(vendor__name__icontains=q)
            | Q(source_yarn_po__system_number__icontains=q)
            | Q(firm__firm_name__icontains=q)
        ).distinct()

    return render(
        request,
        "accounts/greige_po/list.html",
        {
            "orders": qs,
            "q": q,
        },
    )
@login_required
@require_POST
def yarnpo_delete(request, pk: int):
    po = get_object_or_404(YarnPurchaseOrder, pk=pk, owner=request.user)
    po.delete()
    return redirect("accounts:yarnpo_list")

def _build_yarn_po_pdf_response(po):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return HttpResponse(
            "ReportLab is required for PDF generation. Install it with: pip install reportlab",
            status=500,
        )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Yarn Purchase Order - {po.system_number}", styles["Title"]))
    story.append(Spacer(1, 8))

    meta_rows = [
        ["System No", po.system_number or "-"],
        ["PO Number", po.po_number or "-"],
        ["PO Date", po.po_date.strftime("%d-%m-%Y") if po.po_date else "-"],
        ["Cancel Date", po.cancel_date.strftime("%d-%m-%Y") if po.cancel_date else "-"],
        ["Vendor", po.vendor.name if po.vendor else "-"],
        ["Firm", po.firm.firm_name if po.firm else "-"],
        ["Shipping Address", po.shipping_address or "-"],
        ["Status", po.get_approval_status_display() if hasattr(po, "get_approval_status_display") else "-"],
    ]

    meta_table = Table(meta_rows, colWidths=[40 * mm, 130 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#dbe4ee")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    item_rows = [["Material", "Quantity", "UOM", "Rate", "Final Amount"]]
    for item in po.items.all():
        item_rows.append([
            item.material_type.name if item.material_type else (item.material.name if item.material else "-"),
            str(item.quantity or "0.00"),
            item.unit or "-",
            f"₹{item.rate or '0.00'}",
            f"₹{item.final_amount or '0.00'}",
        ])

    items_table = Table(item_rows, colWidths=[72 * mm, 28 * mm, 22 * mm, 28 * mm, 35 * mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#dbe4ee")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 12))

    summary_rows = [
        ["Sub Total", f"₹{po.subtotal or '0.00'}"],
        ["Discount (%)", str(po.discount_percent or '0')],
        ["After Discount", f"₹{po.after_discount_value or '0.00'}"],
        ["Others", f"₹{po.others or '0.00'}"],
        ["CGST (%)", str(po.cgst_percent or '0')],
        ["SGST (%)", str(po.sgst_percent or '0')],
        ["Grand Total", f"₹{po.grand_total or '0.00'}"],
    ]
    summary_table = Table(summary_rows, colWidths=[50 * mm, 42 * mm], hAlign="RIGHT")
    summary_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#dbe4ee")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)

    if po.remarks:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Remarks", styles["Heading4"]))
        story.append(Paragraph(po.remarks, styles["BodyText"]))

    if po.terms_conditions:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Terms & Conditions", styles["Heading4"]))
        story.append(Paragraph(po.terms_conditions.replace("\n", "<br/>"), styles["BodyText"]))

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{po.system_number}.pdf"'
    return response

@login_required
@require_http_methods(["GET", "POST"])
def yarnpo_review(request, pk: int):
    po = get_object_or_404(
        YarnPurchaseOrder.objects
        .select_related("vendor", "firm", "reviewed_by", "owner")
        .prefetch_related(
            Prefetch("items", queryset=YarnPurchaseOrderItem.objects.select_related("material"))
        ),
        pk=pk,
    )

    if not _can_access_yarn_po(request.user, po):
        raise PermissionDenied("You do not have access to this PO.")

    review_form = YarnPOReviewForm(request.POST or None)

    if request.method == "POST":
        if not _can_review_yarn_po(request.user):
            return HttpResponseForbidden("You are not allowed to review this PO.")

        if review_form.is_valid():
            decision = review_form.cleaned_data["decision"]

            if decision == "approve":
                po.approval_status = YarnPurchaseOrder.ApprovalStatus.APPROVED
                po.rejection_reason = ""
            else:
                po.approval_status = YarnPurchaseOrder.ApprovalStatus.REJECTED
                po.rejection_reason = review_form.cleaned_data["rejection_reason"].strip()

            po.reviewed_by = request.user
            po.reviewed_at = timezone.now()
            po.save(update_fields=[
                "approval_status",
                "rejection_reason",
                "reviewed_by",
                "reviewed_at",
            ])
            return redirect("accounts:yarnpo_list")

    return render(
        request,
        "accounts/yarn_po/review.html",
        {
            "po": po,
            "review_form": review_form,
            "can_review_yarn_po": _can_review_yarn_po(request.user),
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