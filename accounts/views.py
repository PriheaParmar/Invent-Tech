from django.db import transaction
import json
from .forms import DashboardProfileForm, FirmForm
from io import BytesIO
from django import forms
from decimal import Decimal, InvalidOperation
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.db.models import Q, Prefetch, Sum
from .forms import ReadyPurchaseOrderForm
from .models import ReadyPurchaseOrder
from datetime import timedelta
from decimal import Decimal
from calendar import monthcalendar
from django.contrib import messages
from zoneinfo import ZoneInfo
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.paginator import Paginator

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
    GreigePurchaseOrderForm,
    GreigePOInwardForm,
    DyeingPurchaseOrderForm,
    DyeingPOInwardForm,
    JobberForm,
    JobberTypeForm,
    LocationForm,
    CategoryForm,    
    BOMForm,    
    ProgramForm,
    ProgramJobberItemFormSet,
    ProgramSizeDetailFormSet,
    BOMMaterialItemFormSet,
    BOMJobberItemFormSet,
    BOMProcessItemFormSet,
    BOMExpenseItemFormSet,
    MaterialForm,
    MaterialShadeForm,
    MaterialSubTypeForm,
    MaterialTypeForm,
    PartyForm,
    MainCategoryForm,
    PatternTypeForm,
    VendorForm,
    CatalogueForm,
    ExpenseForm,
    BrandForm,
    YarnPOInwardForm,
    YarnPOReviewForm,
    YarnPurchaseOrderForm,
    YarnPurchaseOrderItemFormSet,
    ReadyPurchaseOrderForm,
    ReadyPOInwardForm,
    MaterialUnitForm,
)

from .models import (
    Firm,
    GreigePurchaseOrder,
    GreigePurchaseOrderItem,
    GreigePOInward,
    GreigePOInwardItem,
    DyeingPurchaseOrder,
    DyeingPurchaseOrderItem,
    BOM,
    BOMMaterialItem,
    BOMJobberItem,
    BOMProcessItem,
    BOMExpenseItem,
    DyeingPOInward,
    Catalogue,
    DyeingPOInwardItem,
    Jobber,
    Expense,
    JobberType,
    Category,    
    Program,
    ProgramJobberItem,
    ProgramSizeDetail,
    Location,
    Material,
    MaterialShade,
    MaterialSubType,
    MaterialType,
    Party,
    MainCategory,
    PatternType,
    UserExtra,
    Vendor,
    Brand,
    YarnPOInward,
    YarnPOInwardItem,
    YarnPurchaseOrder,
    YarnPurchaseOrderItem,
    ReadyPurchaseOrder,
    ReadyPurchaseOrderItem,
    ReadyPOInward,
    ReadyPOInwardItem,
    MaterialUnit,
)

def _first_form_error(form):
    for field_name, errors in form.errors.items():
        if errors:
            label = field_name
            try:
                if field_name != "__all__":
                    label = form.fields[field_name].label or field_name.replace("_", " ").title()
            except Exception:
                label = field_name.replace("_", " ").title()

            return {
                "field": field_name,
                "label": label,
                "message": str(errors[0]),
            }

    return {
        "field": "",
        "label": "",
        "message": "Please check the form.",
    }

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


def _next_greige_inward_number() -> str:
    last = GreigePOInward.objects.order_by("-id").first()
    next_id = (last.id + 1) if last else 1
    return f"GIN-{next_id:04d}"


def _next_dyeing_po_number() -> str:
    last = DyeingPurchaseOrder.objects.order_by("-id").first()
    next_id = (last.id + 1) if last else 1
    return f"DPO-{next_id:04d}"

def _next_ready_po_number() -> str:
    last = ReadyPurchaseOrder.objects.order_by("-id").first()
    next_id = (last.id + 1) if last else 1
    return f"RPO-{next_id:04d}"

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
        "password": "",
        "password2": "",
    }

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")

        form_data.update({
            "username": username,
            "email": email,
            "password": password,
            "password2": password2,
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
    form = DashboardProfileForm(request.POST)
    if not form.is_valid():
        first_error = _first_form_error(form)
        return JsonResponse(
            {
                "ok": False,
                "message": f"{first_error['label']}: {first_error['message']}" if first_error["label"] else first_error["message"],
                "field": first_error["field"],
                "errors": form.errors,
            },
            status=400,
        )

    u = request.user
    u.first_name = form.cleaned_data["first_name"]
    u.last_name = form.cleaned_data["last_name"]
    u.email = form.cleaned_data["email"]
    u.save(update_fields=["first_name", "last_name", "email"])

    extra, _ = UserExtra.objects.get_or_create(user=u)
    extra.phone = form.cleaned_data["phone"]
    extra.address = form.cleaned_data["address"]
    extra.save(update_fields=["phone", "address"])

    return JsonResponse({"ok": True, "message": "Profile saved ✅"})


# ==========================
# JOBBERS (embed supported)
# ==========================
@login_required
def jobber_list(request):
    q = (request.GET.get("q") or "").strip()
    qs = Jobber.objects.filter(owner=request.user).select_related("jobber_type")

    if q:
        search_terms = [term for term in q.split() if term]

        for term in search_terms:
            phone_term = "".join(ch for ch in term if ch.isdigit())
            term_filter = (
                Q(name__icontains=term)
                | Q(phone__icontains=term)
                | Q(email__icontains=term)
                | Q(role__icontains=term)
                | Q(jobber_type__name__icontains=term)
                | Q(address__icontains=term)
            )

            if phone_term and phone_term != term:
                term_filter |= Q(phone__icontains=phone_term)

            qs = qs.filter(term_filter)

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
def _party_list_url(request):
    url = reverse("accounts:party_list")
    if _is_embed(request):
        url += "?embed=1"
    return url


@login_required
def party_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = Party.objects.all().order_by("party_name")

    if q:
        qs = qs.filter(
            Q(party_name__icontains=q)
            | Q(phone_number__icontains=q)
            | Q(gst_number__icontains=q)
            | Q(pan_number__icontains=q)
            | Q(email__icontains=q)
        )

    template = "accounts/parties/list_embed.html" if _is_embed(request) else "accounts/parties/list.html"
    return render(
        request,
        template,
        {
            "parties": qs,
            "q": q,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def party_create(request):
    form = PartyForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()

        url = _party_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = "accounts/parties/form_embed.html" if _is_embed(request) else "accounts/parties/form.html"
    return render(
        request,
        template,
        {
            "form": form,
            "mode": "add",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def party_update(request, pk):
    party = get_object_or_404(Party, pk=pk)
    form = PartyForm(request.POST or None, instance=party)

    if request.method == "POST" and form.is_valid():
        form.save()

        url = _party_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = "accounts/parties/form_embed.html" if _is_embed(request) else "accounts/parties/form.html"
    return render(
        request,
        template,
        {
            "form": form,
            "mode": "edit",
            "party": party,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def party_delete(request, pk):
    party = get_object_or_404(Party, pk=pk)

    if request.method == "POST":
        party.delete()
        url = _party_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = "accounts/parties/embed_confirm_delete.html" if _is_embed(request) else "accounts/parties/confirm_delete.html"
    return render(
        request,
        template,
        {
            "party": party,
        },
    )
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
            | Q(address_line_1__icontains=q)
            | Q(address_line_2__icontains=q)
            | Q(landmark__icontains=q)
            | Q(city__icontains=q)
            | Q(state__icontains=q)
            | Q(pincode__icontains=q)
        )

    ctx = {"locations": qs, "q": q}
    tpl = "accounts/locations/list_embed.html" if _is_embed(request) else "accounts/locations/list.html"
    return render(request, tpl, ctx)


@login_required
@require_http_methods(["GET", "POST"])
def location_create(request):
    form = LocationForm(request.POST or None, user=request.user)

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
    form = LocationForm(request.POST or None, instance=loc, user=request.user)

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
            | Q(material_kind__icontains=q)
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
def _materialsubtype_list_url(request):
    url = reverse("accounts:materialsubtype_list")
    if _is_embed(request):
        url += "?embed=1"
    return url


@login_required
def materialsubtype_list(request):
    q = (request.GET.get("q") or "").strip()
    selected_kind = (request.GET.get("kind") or "").strip()

    qs = (
        MaterialSubType.objects
        .filter(owner=request.user)
        .select_related("material_type")
        .order_by("material_type__name", "name")
    )

    if selected_kind:
        qs = qs.filter(material_kind=selected_kind)

    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(material_type__name__icontains=q)
        )

    ctx = {
        "sub_types": qs,
        "q": q,
        "selected_kind": selected_kind,
        "kind_choices": Material.MATERIAL_KIND_CHOICES,
    }
    tpl = "accounts/material_sub_types/list_embed.html" if _is_embed(request) else "accounts/material_sub_types/list.html"
    return render(request, tpl, ctx)


@login_required
@require_http_methods(["GET", "POST"])
def materialsubtype_create(request):
    form = MaterialSubTypeForm(request.POST or None, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _materialsubtype_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    tpl = "accounts/material_sub_types/form_embed.html" if _is_embed(request) else "accounts/material_sub_types/form.html"
    return render(request, tpl, {"form": form, "mode": "add"})


@login_required
@require_http_methods(["GET", "POST"])
def materialsubtype_update(request, pk: int):
    sub_type = get_object_or_404(MaterialSubType, pk=pk, owner=request.user)
    form = MaterialSubTypeForm(request.POST or None, instance=sub_type, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _materialsubtype_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    tpl = "accounts/material_sub_types/form_embed.html" if _is_embed(request) else "accounts/material_sub_types/form.html"
    return render(request, tpl, {"form": form, "mode": "edit", "material_sub_type": sub_type})


@login_required
@require_POST
def materialsubtype_delete(request, pk: int):
    sub_type = get_object_or_404(MaterialSubType, pk=pk, owner=request.user)
    sub_type.delete()

    url = _materialsubtype_list_url(request)
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
        from html import escape

        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return HttpResponse(
            "ReportLab is required for PDF generation. Install it with: pip install reportlab",
            status=500,
        )

    def text_or_dash(value):
        value = "" if value is None else str(value).strip()
        return value if value else "-"

    def html_text(value):
        return escape(text_or_dash(value)).replace("\n", "<br/>")

    def fmt_money(value):
        try:
            return f"₹{float(value or 0):,.2f}"
        except Exception:
            return f"₹{value or '0.00'}"

    def fmt_qty(value):
        try:
            return f"{float(value or 0):,.2f}".rstrip("0").rstrip(".")
        except Exception:
            return text_or_dash(value)

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

    base_style = ParagraphStyle(
        "POBase",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#1f1f1f"),
        spaceAfter=0,
    )

    firm_name_style = ParagraphStyle(
        "POFirmName",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.black,
        alignment=TA_LEFT,
    )

    title_style = ParagraphStyle(
        "POTitle",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#444444"),
        alignment=TA_LEFT,
    )

    meta_style = ParagraphStyle(
        "POMeta",
        parent=base_style,
        fontName="Helvetica",
        fontSize=10,
        leading=16,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#222222"),
    )

    label_style = ParagraphStyle(
        "POLabel",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        alignment=TA_LEFT,
    )

    block_text_style = ParagraphStyle(
        "POBlockText",
        parent=base_style,
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        alignment=TA_LEFT,
    )

    table_head_style = ParagraphStyle(
        "POTableHead",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#2a2a2a"),
    )

    item_no_style = ParagraphStyle(
        "POItemNo",
        parent=base_style,
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
    )

    desc_style = ParagraphStyle(
        "PODesc",
        parent=base_style,
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        alignment=TA_LEFT,
    )

    qty_style = ParagraphStyle(
        "POQty",
        parent=base_style,
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
    )

    money_style = ParagraphStyle(
        "POMoney",
        parent=base_style,
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        alignment=TA_RIGHT,
    )

    total_label_style = ParagraphStyle(
        "POTotalLabel",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        alignment=TA_LEFT,
    )

    total_amount_style = ParagraphStyle(
        "POTotalAmount",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        alignment=TA_RIGHT,
    )

    notes_label_style = ParagraphStyle(
        "PONotesLabel",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        alignment=TA_LEFT,
    )

    footer_style = ParagraphStyle(
        "POFooter",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4b5563"),
    )

    story = []

    firm_name = po.firm.firm_name if po.firm else "YOUR FIRM NAME"
    po_date = po.po_date.strftime("%d-%m-%Y") if po.po_date else "-"
    order_number = po.po_number or po.system_number or "-"

    header_table = Table(
        [[
            Paragraph(escape(firm_name), firm_name_style),
            Paragraph(
                f"<b>DATE</b>&nbsp;&nbsp;&nbsp;{escape(po_date)}<br/>"
                f"<b>ORDER No</b>&nbsp;&nbsp;&nbsp;{escape(order_number)}",
                meta_style,
            ),
        ]],
        colWidths=[112 * mm, 64 * mm],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 2))

    story.append(Paragraph("YARN PURCHASE ORDER", title_style))
    story.append(Spacer(1, 10))

    vendor = po.vendor
    info_rows = [
        [Paragraph("NAME", label_style), Paragraph(html_text(vendor.name if vendor else "-"), block_text_style)],
        [Paragraph("ADDRESS", label_style), Paragraph(html_text(vendor.address if vendor else "-"), block_text_style)],
        [Paragraph("PHONE", label_style), Paragraph(html_text(vendor.phone if vendor else "-"), block_text_style)],
        [Paragraph("E-MAIL", label_style), Paragraph(html_text(vendor.email if vendor else "-"), block_text_style)],
    ]

    info_table = Table(info_rows, colWidths=[28 * mm, 148 * mm])
    info_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#222222")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 12))

    item_rows = [[
        Paragraph("ITEM", table_head_style),
        Paragraph("DESCRIPTION", table_head_style),
        Paragraph("QTY", table_head_style),
        Paragraph("PRICE", table_head_style),
        Paragraph("AMOUNT", table_head_style),
    ]]

    po_items = list(po.items.all())

    for index, item in enumerate(po_items, start=1):
        material_name = "-"
        if item.material_type:
            material_name = item.material_type.name
        elif item.material:
            material_name = str(item.material)

        detail_parts = []
        if item.count:
            detail_parts.append(f"Count: {item.count}")
        if item.dia:
            detail_parts.append(f"Dia: {item.dia}")
        if item.gauge:
            detail_parts.append(f"Gauge: {item.gauge}")
        if item.gsm:
            detail_parts.append(f"GSM: {item.gsm}")
        if item.sl:
            detail_parts.append(f"SL: {item.sl}")
        if item.rolls:
            detail_parts.append(f"Rolls: {item.rolls}")
        if item.hsn_code:
            detail_parts.append(f"HSN: {item.hsn_code}")
        if item.remark:
            detail_parts.append(f"Remark: {item.remark}")

        desc_html = f"<b>{escape(text_or_dash(material_name))}</b>"
        if detail_parts:
            desc_html += "<br/>" + escape(" | ".join(detail_parts))

        item_rows.append([
            Paragraph(str(index), item_no_style),
            Paragraph(desc_html, desc_style),
            Paragraph(f"{fmt_qty(item.quantity)} {escape(item.unit or '')}".strip(), qty_style),
            Paragraph(fmt_money(item.rate), money_style),
            Paragraph(fmt_money(item.final_amount), money_style),
        ])

    min_visual_rows = 8
    blank_needed = max(0, min_visual_rows - len(po_items))
    for _ in range(blank_needed):
        item_rows.append([
            Paragraph("", item_no_style),
            Paragraph("", desc_style),
            Paragraph("", qty_style),
            Paragraph("", money_style),
            Paragraph("", money_style),
        ])

    item_rows.append([
        Paragraph("TOTAL", total_label_style),
        "",
        "",
        "",
        Paragraph(fmt_money(po.grand_total), total_amount_style),
    ])

    items_table = Table(
        item_rows,
        colWidths=[18 * mm, 76 * mm, 24 * mm, 27 * mm, 31 * mm],
        repeatRows=1,
    )
    items_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#222222")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f4dddd")),
        ("BACKGROUND", (-1, -1), (-1, -1), colors.HexColor("#f7e6e6")),
        ("SPAN", (0, -1), (3, -1)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 14))

    note_parts = []
    if po.remarks:
        note_parts.append(f"<b>Remarks:</b> {html_text(po.remarks)}")
    if po.terms_conditions:
        note_parts.append(f"<b>Terms:</b> {html_text(po.terms_conditions)}")
    if po.shipping_address:
        note_parts.append(f"<b>Shipping Address:</b> {html_text(po.shipping_address)}")
    if po.cancel_date:
        note_parts.append(f"<b>Cancel Date:</b> {escape(po.cancel_date.strftime('%d-%m-%Y'))}")

    notes_html = "<br/><br/>".join(note_parts) if note_parts else "&nbsp;"

    story.append(Paragraph("NOTES:", notes_label_style))
    story.append(Spacer(1, 4))

    notes_table = Table(
        [[Paragraph(notes_html, block_text_style)]],
        colWidths=[176 * mm],
        rowHeights=[28 * mm],
    )
    notes_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3dede")),
        ("BOX", (0, 0), (-1, -1), 0, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(notes_table)
    story.append(Spacer(1, 14))

    footer_lines = []
    if po.firm:
        footer_lines.append(f"<b>{escape(po.firm.firm_name)}</b>")
        address_parts = [po.firm.address_line, po.firm.city, po.firm.state, po.firm.pincode]
        clean_address = ", ".join([str(part).strip() for part in address_parts if str(part).strip()])
        if clean_address:
            footer_lines.append(escape(clean_address))

        contact_bits = []
        if po.firm.phone:
            contact_bits.append(f"Phone: {escape(po.firm.phone)}")
        if po.firm.email:
            contact_bits.append(f"E-mail: {escape(po.firm.email)}")
        if po.firm.website:
            contact_bits.append(f"Web: {escape(po.firm.website)}")
        if contact_bits:
            footer_lines.append(escape(" | ".join(contact_bits)))

    if footer_lines:
        story.append(Paragraph("<br/>".join(footer_lines), footer_style))

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{po.system_number or "yarn_po"}.pdf"'
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


def _bind_yarnpo_item_formset(request, instance=None, user=None):
    effective_user = user or request.user

    kwargs = {
        "instance": instance,
        "prefix": "items",
        "form_kwargs": {"user": effective_user},
    }

    if request.method == "POST":
        formset = YarnPurchaseOrderItemFormSet(request.POST, **kwargs)
    else:
        formset = YarnPurchaseOrderItemFormSet(**kwargs)

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

        if default_firm:
            po.firm = default_firm

        po.po_date = timezone.localdate()

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
        YarnPurchaseOrder.objects.select_related("vendor", "firm", "owner"),
        pk=pk,
    )

    if not _can_access_yarn_po(request.user, po):
        raise PermissionDenied("You do not have access to this Yarn PO.")

    po_owner = po.owner
    default_firm = Firm.objects.filter(owner=po_owner).first()
    display_firm = po.firm or default_firm

    if request.method == "GET" and display_firm and not po.firm:
        po.firm = display_firm
        if not po.shipping_address:
            po.shipping_address = _firm_address(display_firm)

    form = YarnPurchaseOrderForm(request.POST or None, user=po_owner, instance=po)
    formset = _bind_yarnpo_item_formset(request, instance=po, user=po_owner)

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        po = form.save(commit=False)

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
            inward.owner = po.owner
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
            "next_inward_number_preview": _next_yarn_inward_number(),
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
            Prefetch(
                "greige_pos",
                queryset=GreigePurchaseOrder.objects.prefetch_related("items").order_by("-id"),
            ),
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

        greige_po = po.greige_pos.first()

        inward_entries = []
        for inward in po.inwards.all():
            inward_items = []
            for inward_item in inward.items.all():
                po_item = inward_item.po_item
                inward_items.append({
                    "inward_item": inward_item,
                    "po_item": po_item,
                    "fabric_name": po_item.material.name if po_item and po_item.material else "Yarn Item",
                    "ordered_qty": po_item.quantity if po_item else 0,
                    "inward_qty": inward_item.quantity,
                    "unit": po_item.unit if po_item else "",
                })

            inward_entries.append({
                "inward": inward,
                "items": inward_items,
            })

        greige_items = []
        if greige_po:
            for item in greige_po.items.all():
                greige_items.append(item)

        rows.append({
            "po": po,
            "greige_po": greige_po,
            "greige_started": bool(greige_po),
            "inward_entries": inward_entries,
            "greige_items": greige_items,
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
def generate_greige_po_from_yarn(request, pk: int):
    yarn_po = get_object_or_404(
        YarnPurchaseOrder.objects.select_related("owner"),
        pk=pk,
    )

    if not _can_access_yarn_po(request.user, yarn_po):
        raise PermissionDenied("You do not have access to this Yarn PO.")

    return redirect("accounts:greigepo_add_from_yarn", yarn_po_id=pk)


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
@login_required
@require_POST
def firm_save(request):
    firm = Firm.objects.filter(owner=request.user).first()
    if firm is None:
        firm = Firm(owner=request.user)

    form = FirmForm(request.POST, instance=firm)
    if not form.is_valid():
        first_error = _first_form_error(form)
        return JsonResponse(
            {
                "ok": False,
                "message": f"{first_error['label']}: {first_error['message']}" if first_error["label"] else first_error["message"],
                "field": first_error["field"],
                "errors": form.errors,
            },
            status=400,
        )

    firm = form.save(commit=False)
    firm.owner = request.user
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


def _can_access_greige_po(user, po):
    return bool(_can_review_yarn_po(user) or po.owner_id == user.id)


def _can_access_dyeing_po(user, po):
    return bool(_can_review_yarn_po(user) or po.owner_id == user.id)

def _can_access_ready_po(user, po):
    return bool(_can_review_yarn_po(user) or po.owner_id == user.id)

def _greige_source_queryset():
    return (
        YarnPurchaseOrder.objects
        .select_related("vendor", "firm", "owner")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=YarnPurchaseOrderItem.objects.select_related("material", "material_type").prefetch_related("inward_items"),
            ),
            Prefetch(
                "inwards",
                queryset=YarnPOInward.objects.prefetch_related("items__po_item__material", "items__po_item__material_type"),
            ),
        )
    )


def _greige_po_queryset():
    return (
        GreigePurchaseOrder.objects
        .select_related("vendor", "firm", "source_yarn_po", "owner")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=GreigePurchaseOrderItem.objects.select_related("source_yarn_po_item").prefetch_related("inward_items"),
            ),
            Prefetch(
                "inwards",
                queryset=GreigePOInward.objects.prefetch_related("items__po_item"),
            ),
            Prefetch(
                "dyeing_pos",
                queryset=DyeingPurchaseOrder.objects.prefetch_related("items").order_by("-id"),
            ),
        )
        .order_by("-id")
    )


def _dyeing_po_queryset():
    return (
        DyeingPurchaseOrder.objects
        .select_related("vendor", "firm", "source_greige_po", "owner")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=DyeingPurchaseOrderItem.objects.select_related("source_greige_po_item").prefetch_related("inward_items"),
            ),
            Prefetch(
                "inwards",
                queryset=DyeingPOInward.objects.prefetch_related("items__po_item"),
            ),
            Prefetch(
            "ready_pos",
            queryset=ReadyPurchaseOrder.objects.prefetch_related("items").order_by("-id"),
            ),
        )
        .order_by("-id")
    )

def _ready_po_queryset():
    return (
        ReadyPurchaseOrder.objects
        .select_related("vendor", "firm", "source_dyeing_po", "owner")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=ReadyPurchaseOrderItem.objects.select_related("source_dyeing_po_item").prefetch_related("inward_items"),
            ),
            Prefetch(
                "inwards",
                queryset=ReadyPOInward.objects.prefetch_related("items__po_item"),
            ),
        )
        .order_by("-id")
    )
    
def _sync_greige_po_items_from_source(greige_po):
    yarn_po = (
        _greige_source_queryset()
        .filter(pk=greige_po.source_yarn_po_id)
        .first()
    )
    if yarn_po is None:
        return Decimal("0")

    item_rows = []
    total_weight = Decimal("0")

    for yarn_item in yarn_po.items.all():
        inward_qty = yarn_item.inward_qty_total or Decimal("0")
        if inward_qty <= 0:
            continue

        yarn_name = (
            yarn_item.material_type.name
            if yarn_item.material_type
            else (yarn_item.material.name if yarn_item.material else "Yarn Item")
        )

        item_rows.append(
            GreigePurchaseOrderItem(
                po=greige_po,
                source_yarn_po_item=yarn_item,
                fabric_name=yarn_name,
                yarn_name=yarn_name,
                unit=yarn_item.unit or "",
                quantity=inward_qty,
                remark=f"Generated from Yarn inward of {yarn_po.system_number}",
            )
        )
        total_weight += inward_qty

    GreigePurchaseOrderItem.objects.filter(po=greige_po).delete()
    if item_rows:
        GreigePurchaseOrderItem.objects.bulk_create(item_rows)

    greige_po.total_weight = total_weight
    greige_po.available_qty = total_weight
    greige_po.save(update_fields=["total_weight", "available_qty", "updated_at"])
    return total_weight


def _sync_dyeing_po_items_from_source(dyeing_po):
    greige_po = (
        _greige_po_queryset()
        .filter(pk=dyeing_po.source_greige_po_id)
        .first()
    )
    if greige_po is None:
        return Decimal("0")

    item_rows = []
    total_weight = Decimal("0")

    for greige_item in greige_po.items.all():
        inward_qty = greige_item.inward_qty_total or Decimal("0")
        if inward_qty <= 0:
            continue

        greige_name = greige_item.fabric_name or "Greige Item"

        item_rows.append(
            DyeingPurchaseOrderItem(
                po=dyeing_po,
                source_greige_po_item=greige_item,
                fabric_name=greige_name,
                greige_name=greige_name,
                unit=greige_item.unit or "",
                quantity=inward_qty,
                remark=f"Generated from Greige inward of {greige_po.system_number}",
            )
        )
        total_weight += inward_qty

    DyeingPurchaseOrderItem.objects.filter(po=dyeing_po).delete()
    if item_rows:
        DyeingPurchaseOrderItem.objects.bulk_create(item_rows)

    dyeing_po.total_weight = total_weight
    dyeing_po.available_qty = total_weight
    dyeing_po.save(update_fields=["total_weight", "available_qty", "updated_at"])
    return total_weight

def _sync_ready_po_items_from_source(ready_po):
    dyeing_po = (
        _dyeing_po_queryset()
        .filter(pk=ready_po.source_dyeing_po_id)
        .first()
    )
    if dyeing_po is None:
        return Decimal("0")

    item_rows = []
    total_weight = Decimal("0")

    for dyeing_item in dyeing_po.items.all():
        inward_qty = dyeing_item.inward_qty_total or Decimal("0")
        if inward_qty <= 0:
            continue

        dyeing_name = dyeing_item.fabric_name or "Dyeing Item"

        item_rows.append(
            ReadyPurchaseOrderItem(
                po=ready_po,
                source_dyeing_po_item=dyeing_item,
                fabric_name=dyeing_name,
                dyeing_name=dyeing_name,
                unit=dyeing_item.unit or "",
                quantity=inward_qty,
                remark=f"Generated from Dyeing inward of {dyeing_po.system_number}",
            )
        )
        total_weight += inward_qty

    ReadyPurchaseOrderItem.objects.filter(po=ready_po).delete()
    if item_rows:
        ReadyPurchaseOrderItem.objects.bulk_create(item_rows)

    ready_po.total_weight = total_weight
    ready_po.available_qty = total_weight
    ready_po.save(update_fields=["total_weight", "available_qty", "updated_at"])
    return total_weight

@login_required
def po_home(request):
    return render(request, "accounts/po/index.html")


@login_required
def greigepo_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = _greige_po_queryset()
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
@require_http_methods(["GET", "POST"])
def greigepo_create(request, yarn_po_id=None):
    source_yarn_po = None
    if yarn_po_id is not None:
        source_yarn_po = get_object_or_404(_greige_source_queryset(), pk=yarn_po_id)
        if not _can_access_yarn_po(request.user, source_yarn_po):
            raise PermissionDenied("You do not have access to this Yarn PO.")

    if request.method == "POST":
        form = GreigePurchaseOrderForm(
            request.POST,
            user=request.user,
            source_yarn_po=source_yarn_po,
            lock_source=bool(source_yarn_po),
        )

        if form.is_valid():
            selected_source = source_yarn_po or form.cleaned_data["source_yarn_po"]
            if not _can_access_yarn_po(request.user, selected_source):
                raise PermissionDenied("You do not have access to this Yarn PO.")

            if not selected_source.inwards.exists():
                form.add_error("source_yarn_po", "Selected Yarn PO has no inward entries yet.")
            elif selected_source.greige_pos.exists():
                form.add_error("source_yarn_po", "Greige PO already exists for this Yarn PO.")
            else:
                greige_po = form.save(commit=False)
                greige_po.owner = selected_source.owner
                greige_po.system_number = _next_greige_po_number()
                greige_po.source_yarn_po = selected_source
                if greige_po.firm and not greige_po.shipping_address:
                    greige_po.shipping_address = _firm_address(greige_po.firm)
                greige_po.save()
                _sync_greige_po_items_from_source(greige_po)
                return redirect("accounts:greigepo_list")
    else:
        initial = {}
        if source_yarn_po is not None:
            initial = {
                "po_number": source_yarn_po.po_number or "",
                "po_date": timezone.localdate(),
                "available_qty": source_yarn_po.total_inward_qty or Decimal("0"),
                "vendor": source_yarn_po.vendor_id,
                "firm": source_yarn_po.firm_id if source_yarn_po.firm else None,
                "shipping_address": _firm_address(source_yarn_po.firm) if source_yarn_po.firm else "",
                "remarks": f"Generated from Yarn PO {source_yarn_po.system_number}",
            }

        form = GreigePurchaseOrderForm(
            initial=initial,
            user=request.user,
            source_yarn_po=source_yarn_po,
            lock_source=bool(source_yarn_po),
        )

    source_inwards = list(source_yarn_po.inwards.all()) if source_yarn_po else []
    existing_po = source_yarn_po.greige_pos.order_by("-id").first() if source_yarn_po else None

    return render(
        request,
        "accounts/greige_po/form.html",
        {
            "form": form,
            "mode": "add",
            "po_obj": None,
            "source_yarn_po": source_yarn_po,
            "source_inwards": source_inwards,
            "existing_po": existing_po,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def greigepo_update(request, pk: int):
    po = get_object_or_404(_greige_po_queryset(), pk=pk)
    if not _can_access_greige_po(request.user, po):
        raise PermissionDenied("You do not have access to this Greige PO.")

    form = GreigePurchaseOrderForm(
        request.POST or None,
        user=request.user,
        instance=po,
        source_yarn_po=po.source_yarn_po,
        lock_source=True,
    )

    if request.method == "POST" and form.is_valid():
        po = form.save(commit=False)
        if po.firm and not po.shipping_address:
            po.shipping_address = _firm_address(po.firm)
        po.save()
        return redirect("accounts:greigepo_list")

    return render(
        request,
        "accounts/greige_po/form.html",
        {
            "form": form,
            "mode": "edit",
            "po_obj": po,
            "source_yarn_po": po.source_yarn_po,
            "source_inwards": list(po.source_yarn_po.inwards.all()) if po.source_yarn_po else [],
            "existing_po": None,
        },
    )


@login_required
def greigepo_detail(request, pk: int):
    po = get_object_or_404(_greige_po_queryset(), pk=pk)
    if not _can_access_greige_po(request.user, po):
        raise PermissionDenied("You do not have access to this Greige PO.")

    return render(
        request,
        "accounts/greige_po/detail.html",
        {
            "po": po,
            "source_yarn_po": po.source_yarn_po,
            "source_inwards": list(po.source_yarn_po.inwards.all()) if po.source_yarn_po else [],
            "existing_dyeing_po": po.dyeing_pos.first(),
            "greige_inwards": list(po.inwards.all()),
        },
    )


@login_required
@require_POST
def greigepo_delete(request, pk: int):
    po = get_object_or_404(GreigePurchaseOrder, pk=pk, owner=request.user)
    po.delete()
    return redirect("accounts:greigepo_list")


@login_required
@require_http_methods(["GET", "POST"])
def greigepo_inward(request, pk: int):
    po = get_object_or_404(_greige_po_queryset(), pk=pk)
    if not _can_access_greige_po(request.user, po):
        raise PermissionDenied("You do not have access to this Greige PO.")

    item_errors = {}
    line_inputs = {}
    inward_form = GreigePOInwardForm(request.POST or None)

    if request.method == "POST" and inward_form.is_valid():
        line_payload = []

        for item in po.items.all():
            raw_qty = (request.POST.get(f"qty_{item.id}") or "").strip()
            remark = (request.POST.get(f"remark_{item.id}") or "").strip()

            line_inputs[item.id] = {"qty": raw_qty, "remark": remark}

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
            inward.owner = po.owner
            inward.po = po
            inward.inward_number = _next_greige_inward_number()
            inward.save()

            GreigePOInwardItem.objects.bulk_create([
                GreigePOInwardItem(
                    inward=inward,
                    po_item=item,
                    quantity=qty,
                    remark=remark,
                )
                for item, qty, remark in line_payload
            ])
            return redirect("accounts:greigepo_inward", pk=po.pk)

    line_rows = [
        {
            "item": item,
            "qty_value": line_inputs.get(item.id, {}).get("qty", ""),
            "remark_value": line_inputs.get(item.id, {}).get("remark", ""),
            "error": item_errors.get(item.id, ""),
        }
        for item in po.items.all()
    ]

    return render(
        request,
        "accounts/greige_po/inward.html",
        {
            "po": po,
            "inward_form": inward_form,
            "line_rows": line_rows,
            "existing_inwards": po.inwards.all().order_by("-inward_date", "-id"),
        },
    )


@login_required
def greige_inward_tracker(request):
    q = (request.GET.get("q") or "").strip()

    qs = _greige_po_queryset().filter(inwards__isnull=False).distinct()
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

    rows = []
    for po in qs:
        dyeing_po = po.dyeing_pos.first()

        inward_entries = []
        for inward in po.inwards.all():
            inward_entries.append({
                "inward": inward,
                "items": [
                    {
                        "inward_item": inward_item,
                        "po_item": inward_item.po_item,
                        "fabric_name": inward_item.po_item.fabric_name if inward_item.po_item else "Greige Item",
                        "ordered_qty": inward_item.po_item.quantity if inward_item.po_item else 0,
                        "inward_qty": inward_item.quantity,
                        "unit": inward_item.po_item.unit if inward_item.po_item else "",
                    }
                    for inward_item in inward.items.all()
                ],
            })

        rows.append({
            "po": po,
            "dyeing_po": dyeing_po,
            "dyeing_started": bool(dyeing_po),
            "inward_entries": inward_entries,
            "dyeing_items": list(dyeing_po.items.all()) if dyeing_po else [],
        })

    return render(
        request,
        "accounts/greige_po/inward_tracker.html",
        {
            "rows": rows,
            "q": q,
        },
    )


@login_required
def generate_dyeing_po_from_greige(request, pk: int):
    greige_po = get_object_or_404(_greige_po_queryset(), pk=pk)
    if not _can_access_greige_po(request.user, greige_po):
        raise PermissionDenied("You do not have access to this Greige PO.")
    return redirect("accounts:dyeingpo_add_from_greige", greige_po_id=pk)

@login_required
def generate_ready_po_from_dyeing(request, pk: int):
    dyeing_po = get_object_or_404(_dyeing_po_queryset(), pk=pk)
    if not _can_access_dyeing_po(request.user, dyeing_po):
        raise PermissionDenied("You do not have access to this Dyeing PO.")
    return redirect("accounts:readypo_add_from_dyeing", dyeing_po_id=pk)

@login_required
def dyeingpo_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = _dyeing_po_queryset()
    if not _can_review_yarn_po(request.user):
        qs = qs.filter(owner=request.user)

    if q:
        qs = qs.filter(
            Q(system_number__icontains=q)
            | Q(po_number__icontains=q)
            | Q(vendor__name__icontains=q)
            | Q(source_greige_po__system_number__icontains=q)
            | Q(firm__firm_name__icontains=q)
        ).distinct()

    return render(
        request,
        "accounts/dyeing_po/list.html",
        {
            "orders": qs,
            "q": q,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def dyeingpo_create(request, greige_po_id=None):
    source_greige_po = None
    if greige_po_id is not None:
        source_greige_po = get_object_or_404(_greige_po_queryset(), pk=greige_po_id)
        if not _can_access_greige_po(request.user, source_greige_po):
            raise PermissionDenied("You do not have access to this Greige PO.")

    if request.method == "POST":
        form = DyeingPurchaseOrderForm(
            request.POST,
            user=request.user,
            source_greige_po=source_greige_po,
            lock_source=bool(source_greige_po),
        )

        if form.is_valid():
            selected_source = source_greige_po or form.cleaned_data["source_greige_po"]
            if not _can_access_greige_po(request.user, selected_source):
                raise PermissionDenied("You do not have access to this Greige PO.")

            if not selected_source.inwards.exists():
                form.add_error("source_greige_po", "Selected Greige PO has no inward entries yet.")
            elif selected_source.dyeing_pos.exists():
                form.add_error("source_greige_po", "Dyeing PO already exists for this Greige PO.")
            else:
                dyeing_po = form.save(commit=False)
                dyeing_po.owner = selected_source.owner
                dyeing_po.system_number = _next_dyeing_po_number()
                dyeing_po.source_greige_po = selected_source
                if dyeing_po.firm and not dyeing_po.shipping_address:
                    dyeing_po.shipping_address = _firm_address(dyeing_po.firm)
                dyeing_po.save()
                _sync_dyeing_po_items_from_source(dyeing_po)
                return redirect("accounts:dyeingpo_list")
    else:
        initial = {}
        if source_greige_po is not None:
            initial = {
                "po_number": source_greige_po.po_number or "",
                "po_date": timezone.localdate(),
                "available_qty": source_greige_po.total_inward_qty or Decimal("0"),
                "vendor": source_greige_po.vendor_id,
                "firm": source_greige_po.firm_id if source_greige_po.firm else None,
                "shipping_address": _firm_address(source_greige_po.firm) if source_greige_po.firm else "",
                "remarks": f"Generated from Greige PO {source_greige_po.system_number}",
            }

        form = DyeingPurchaseOrderForm(
            initial=initial,
            user=request.user,
            source_greige_po=source_greige_po,
            lock_source=bool(source_greige_po),
        )

    return render(
        request,
        "accounts/dyeing_po/form.html",
        {
            "form": form,
            "mode": "add",
            "po_obj": None,
            "source_greige_po": source_greige_po,
            "source_inwards": list(source_greige_po.inwards.all()) if source_greige_po else [],
            "existing_po": source_greige_po.dyeing_pos.order_by("-id").first() if source_greige_po else None,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def dyeingpo_update(request, pk: int):
    po = get_object_or_404(_dyeing_po_queryset(), pk=pk)
    if not _can_access_dyeing_po(request.user, po):
        raise PermissionDenied("You do not have access to this Dyeing PO.")

    form = DyeingPurchaseOrderForm(
        request.POST or None,
        user=request.user,
        instance=po,
        source_greige_po=po.source_greige_po,
        lock_source=True,
    )

    if request.method == "POST" and form.is_valid():
        po = form.save(commit=False)
        if po.firm and not po.shipping_address:
            po.shipping_address = _firm_address(po.firm)
        po.save()
        return redirect("accounts:dyeingpo_list")

    return render(
        request,
        "accounts/dyeing_po/form.html",
        {
            "form": form,
            "mode": "edit",
            "po_obj": po,
            "source_greige_po": po.source_greige_po,
            "source_inwards": list(po.source_greige_po.inwards.all()) if po.source_greige_po else [],
            "existing_po": None,
        },
    )


@login_required
def dyeingpo_detail(request, pk: int):
    po = get_object_or_404(_dyeing_po_queryset(), pk=pk)
    if not _can_access_dyeing_po(request.user, po):
        raise PermissionDenied("You do not have access to this Dyeing PO.")

    return render(
        request,
        "accounts/dyeing_po/detail.html",
        {
            "po": po,
            "source_greige_po": po.source_greige_po,
            "source_inwards": list(po.source_greige_po.inwards.all()) if po.source_greige_po else [],
            "dyeing_inwards": list(po.inwards.all()),
            "existing_ready_po": po.ready_pos.order_by("-id").first(),
        },
    )

def _next_dyeing_inward_number() -> str:
    last = DyeingPOInward.objects.order_by("-id").first()
    next_id = (last.id + 1) if last else 1
    return f"DIN-{next_id:04d}"


def _next_ready_inward_number() -> str:
    last = ReadyPOInward.objects.order_by("-id").first()
    next_id = (last.id + 1) if last else 1
    return f"RIN-{next_id:04d}"

@login_required
@require_POST
def dyeingpo_delete(request, pk: int):
    po = get_object_or_404(DyeingPurchaseOrder, pk=pk, owner=request.user)
    po.delete()
    return redirect("accounts:dyeingpo_list")


@login_required
@require_http_methods(["GET", "POST"])
def dyeingpo_inward(request, pk: int):
    po = get_object_or_404(_dyeing_po_queryset(), pk=pk)
    if not _can_access_dyeing_po(request.user, po):
        raise PermissionDenied("You do not have access to this Dyeing PO.")

    item_errors = {}
    line_inputs = {}
    inward_form = DyeingPOInwardForm(request.POST or None)

    if request.method == "POST" and inward_form.is_valid():
        line_payload = []

        for item in po.items.all():
            raw_qty = (request.POST.get(f"qty_{item.id}") or "").strip()
            remark = (request.POST.get(f"remark_{item.id}") or "").strip()

            line_inputs[item.id] = {"qty": raw_qty, "remark": remark}

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
            inward.owner = po.owner
            inward.po = po
            inward.inward_number = _next_dyeing_inward_number()
            inward.save()

            DyeingPOInwardItem.objects.bulk_create([
                DyeingPOInwardItem(
                    inward=inward,
                    po_item=item,
                    quantity=qty,
                    remark=remark,
                )
                for item, qty, remark in line_payload
            ])
            return redirect("accounts:dyeingpo_inward", pk=po.pk)

    line_rows = [
        {
            "item": item,
            "qty_value": line_inputs.get(item.id, {}).get("qty", ""),
            "remark_value": line_inputs.get(item.id, {}).get("remark", ""),
            "error": item_errors.get(item.id, ""),
        }
        for item in po.items.all()
    ]

    return render(
        request,
        "accounts/dyeing_po/inward.html",
        {
            "po": po,
            "inward_form": inward_form,
            "line_rows": line_rows,
            "existing_inwards": po.inwards.all().order_by("-inward_date", "-id"),
            "existing_ready_po": po.ready_pos.order_by("-id").first(),
        },
    )



def _normalize_stock_lot_search_value(value: str) -> str:
    return (value or "").strip().lower()


def _build_stock_lot_rows_for_user(user):
    rows = []

    dyeing_inward_items = (
        DyeingPOInwardItem.objects
        .select_related(
            "inward",
            "po_item__po__vendor",
            "po_item__po__firm",
        )
        .filter(inward__owner=user)
        .order_by("-inward__inward_date", "-id")
    )

    for inward_item in dyeing_inward_items:
        inward = inward_item.inward
        po_item = inward_item.po_item
        po = po_item.po if po_item else None

        material_name = "Ready / Dyeing Item"
        if po_item:
            material_name = (
                po_item.fabric_name
                or getattr(po_item, "greige_name", "")
                or "Ready / Dyeing Item"
            )

        vendor_name = po.vendor.name if po and po.vendor else "-"
        firm_name = po.firm.firm_name if po and po.firm else "-"
        quantity = inward_item.quantity or Decimal("0")
        unit = po_item.unit if po_item and po_item.unit else "KG"

        rows.append({
            "stage": "dyeing",
            "stage_label": "Dyeing",
            "lot_number": inward.inward_number or f"DYEING-{inward.pk}",
            "lot_date": inward.inward_date,
            "material_name": material_name,
            "material_key": _normalize_stock_lot_search_value(material_name),
            "vendor_name": vendor_name,
            "firm_name": firm_name,
            "source_number": po.system_number if po and po.system_number else (po.po_number if po else "-"),
            "quantity": quantity,
            "used_quantity": None,
            "final_stock": quantity,
            "unit": unit,
            "remark": inward_item.remark or "",
            "detail_url": reverse("accounts:dyeingpo_inward", args=[po.pk]) if po else "",
            "detail_label": "Open Dyeing Inward",
            "pk": inward_item.pk,
        })

    rows.sort(
        key=lambda row: (
            row["lot_date"] or timezone.datetime.min.date(),
            row["pk"],
        ),
        reverse=True,
    )
    return rows


@login_required
def stock_lot_wise(request):
    q = (request.GET.get("q") or "").strip()
    selected_material = (request.GET.get("material") or "").strip()

    all_rows = _build_stock_lot_rows_for_user(request.user)

    material_choices = sorted(
        {
            row["material_name"]
            for row in all_rows
            if row["material_name"] and row["material_name"] != "-"
        },
        key=lambda value: value.lower(),
    )

    rows = all_rows

    if selected_material:
        material_key = _normalize_stock_lot_search_value(selected_material)
        rows = [
            row for row in rows
            if row["material_key"] == material_key
        ]

    if q:
        q_key = _normalize_stock_lot_search_value(q)
        filtered_rows = []

        for row in rows:
            haystack = " ".join([
                row.get("lot_number", ""),
                row.get("material_name", ""),
                row.get("vendor_name", ""),
                row.get("firm_name", ""),
                row.get("source_number", ""),
                row.get("remark", ""),
            ]).lower()

            if q_key in haystack:
                filtered_rows.append(row)

        rows = filtered_rows

    total_lots = len(rows)
    total_quantity = sum((row["quantity"] for row in rows), Decimal("0"))
    total_final_stock = sum((row["final_stock"] for row in rows), Decimal("0"))

    paginator = Paginator(rows, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "rows": page_obj.object_list,
        "page_obj": page_obj,
        "q": q,
        "selected_material": selected_material,
        "material_choices": material_choices,
        "summary": {
            "total_lots": total_lots,
            "total_quantity": total_quantity,
            "total_final_stock": total_final_stock,
        },
    }

    return render(request, "accounts/inventory/stock_lot_wise.html", context)


@login_required
def dyeing_inward_tracker(request):
    q = (request.GET.get("q") or "").strip()

    qs = _dyeing_po_queryset().filter(inwards__isnull=False).distinct()
    if not _can_review_yarn_po(request.user):
        qs = qs.filter(owner=request.user)

    if q:
        qs = qs.filter(
            Q(system_number__icontains=q)
            | Q(po_number__icontains=q)
            | Q(vendor__name__icontains=q)
            | Q(source_greige_po__system_number__icontains=q)
            | Q(firm__firm_name__icontains=q)
        ).distinct()

    rows = []
    for po in qs:
        inward_entries = []
        for inward in po.inwards.all():
            inward_entries.append({
                "inward": inward,
                "items": [
                    {
                        "inward_item": inward_item,
                        "po_item": inward_item.po_item,
                        "fabric_name": inward_item.po_item.fabric_name if inward_item.po_item else "Dyeing Item",
                        "ordered_qty": inward_item.po_item.quantity if inward_item.po_item else 0,
                        "inward_qty": inward_item.quantity,
                        "unit": inward_item.po_item.unit if inward_item.po_item else "",
                    }
                    for inward_item in inward.items.all()
                ],
            })

        rows.append({
            "po": po,
            "inward_entries": inward_entries,
            "ready_po": po.ready_pos.order_by("-id").first(),
        })

    return render(
        request,
        "accounts/dyeing_po/inward_tracker.html",
        {
            "rows": rows,
            "q": q,
        },
    )


@login_required
def readypo_create(request, dyeing_po_id=None):
    source_dyeing_po = None
    existing_po = None

    if dyeing_po_id is not None:
        source_dyeing_po = get_object_or_404(_dyeing_po_queryset(), pk=dyeing_po_id)
        if not _can_access_dyeing_po(request.user, source_dyeing_po):
            raise PermissionDenied("You do not have access to this Dyeing PO.")

        existing_po = source_dyeing_po.ready_pos.order_by("-id").first()
        if existing_po and request.method == "GET":
            messages.info(request, "Ready PO already exists for this Dyeing PO.")
            return redirect("accounts:readypo_detail", pk=existing_po.pk)

    if request.method == "POST":
        form = ReadyPurchaseOrderForm(
            request.POST,
            user=request.user,
            source_dyeing_po=source_dyeing_po,
            lock_source=bool(source_dyeing_po),
        )

        if form.is_valid():
            selected_source = source_dyeing_po or form.cleaned_data.get("source_dyeing_po")

            if selected_source is None:
                form.add_error("source_dyeing_po", "Please select source Dyeing PO.")
            elif not _can_access_dyeing_po(request.user, selected_source):
                raise PermissionDenied("You do not have access to this Dyeing PO.")
            elif selected_source.ready_pos.exists():
                existing_po = selected_source.ready_pos.order_by("-id").first()
                form.add_error("source_dyeing_po", "Ready PO already exists for this Dyeing PO.")
            else:
                po = form.save(commit=False)
                po.owner = selected_source.owner
                po.system_number = _next_ready_po_number()
                po.source_dyeing_po = selected_source
                po.save()

                _sync_ready_po_items_from_source(po)

                messages.success(request, "Ready PO created successfully.")
                return redirect("accounts:readypo_detail", pk=po.pk)
    else:
        form = ReadyPurchaseOrderForm(
            user=request.user,
            source_dyeing_po=source_dyeing_po,
            lock_source=bool(source_dyeing_po),
        )

    source_inwards = []
    if source_dyeing_po is not None:
        source_inwards = source_dyeing_po.inwards.prefetch_related("items__po_item").all()

    return render(
        request,
        "accounts/ready_po/form.html",
        {
            "form": form,
            "mode": "create",
            "po_obj": None,
            "source_dyeing_po": source_dyeing_po,
            "source_inwards": source_inwards,
            "existing_po": existing_po,
        },
    )

@login_required
def readypo_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = _ready_po_queryset()
    if not _can_review_yarn_po(request.user):
        qs = qs.filter(owner=request.user)

    if q:
        qs = qs.filter(
            Q(system_number__icontains=q)
            | Q(po_number__icontains=q)
            | Q(vendor__name__icontains=q)
            | Q(source_dyeing_po__system_number__icontains=q)
            | Q(firm__firm_name__icontains=q)
        ).distinct()

    return render(
        request,
        "accounts/ready_po/list.html",
        {
            "orders": qs,
            "q": q,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def readypo_update(request, pk: int):
    po = get_object_or_404(_ready_po_queryset(), pk=pk)
    if not _can_access_ready_po(request.user, po):
        raise PermissionDenied("You do not have access to this Ready PO.")

    form = ReadyPurchaseOrderForm(
        request.POST or None,
        user=request.user,
        instance=po,
        source_dyeing_po=po.source_dyeing_po,
        lock_source=True,
    )

    if request.method == "POST" and form.is_valid():
        po = form.save(commit=False)
        if po.firm and not po.shipping_address:
            po.shipping_address = _firm_address(po.firm)
        po.save()
        return redirect("accounts:readypo_list")

    return render(
        request,
        "accounts/ready_po/form.html",
        {
            "form": form,
            "mode": "edit",
            "po_obj": po,
            "source_dyeing_po": po.source_dyeing_po,
            "source_inwards": list(po.source_dyeing_po.inwards.all()) if po.source_dyeing_po else [],
            "existing_po": None,
        },
    )


@login_required
def readypo_detail(request, pk: int):
    po = get_object_or_404(_ready_po_queryset(), pk=pk)
    if not _can_access_ready_po(request.user, po):
        raise PermissionDenied("You do not have access to this Ready PO.")

    return render(
        request,
        "accounts/ready_po/detail.html",
        {
            "po": po,
            "source_dyeing_po": po.source_dyeing_po,
            "source_inwards": list(po.source_dyeing_po.inwards.all()) if po.source_dyeing_po else [],
            "ready_inwards": list(po.inwards.all()),
        },
    )


@login_required
@require_POST
def readypo_delete(request, pk: int):
    po = get_object_or_404(ReadyPurchaseOrder, pk=pk, owner=request.user)
    po.delete()
    return redirect("accounts:readypo_list")


@login_required
@require_http_methods(["GET", "POST"])
def readypo_inward(request, pk: int):
    po = get_object_or_404(_ready_po_queryset(), pk=pk)
    if not _can_access_ready_po(request.user, po):
        raise PermissionDenied("You do not have access to this Ready PO.")

    item_errors = {}
    line_inputs = {}
    inward_form = ReadyPOInwardForm(request.POST or None)

    if request.method == "POST" and inward_form.is_valid():
        line_payload = []

        for item in po.items.all():
            raw_qty = (request.POST.get(f"qty_{item.id}") or "").strip()
            remark = (request.POST.get(f"remark_{item.id}") or "").strip()

            line_inputs[item.id] = {"qty": raw_qty, "remark": remark}

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
            inward.owner = po.owner
            inward.po = po
            inward.inward_number = _next_ready_inward_number()
            inward.save()

            ReadyPOInwardItem.objects.bulk_create([
                ReadyPOInwardItem(
                    inward=inward,
                    po_item=item,
                    quantity=qty,
                    remark=remark,
                )
                for item, qty, remark in line_payload
            ])
            return redirect("accounts:readypo_inward", pk=po.pk)

    line_rows = [
        {
            "item": item,
            "qty_value": line_inputs.get(item.id, {}).get("qty", ""),
            "remark_value": line_inputs.get(item.id, {}).get("remark", ""),
            "error": item_errors.get(item.id, ""),
        }
        for item in po.items.all()
    ]

    return render(
        request,
        "accounts/ready_po/inward.html",
        {
            "po": po,
            "inward_form": inward_form,
            "line_rows": line_rows,
            "existing_inwards": po.inwards.all().order_by("-inward_date", "-id"),
        },
    )


@login_required
def ready_inward_tracker(request):
    q = (request.GET.get("q") or "").strip()

    qs = _ready_po_queryset().filter(inwards__isnull=False).distinct()
    if not _can_review_yarn_po(request.user):
        qs = qs.filter(owner=request.user)

    if q:
        qs = qs.filter(
            Q(system_number__icontains=q)
            | Q(po_number__icontains=q)
            | Q(vendor__name__icontains=q)
            | Q(source_dyeing_po__system_number__icontains=q)
            | Q(firm__firm_name__icontains=q)
        ).distinct()

    rows = []
    for po in qs:
        inward_entries = []
        for inward in po.inwards.all():
            inward_entries.append({
                "inward": inward,
                "items": [
                    {
                        "inward_item": inward_item,
                        "po_item": inward_item.po_item,
                        "fabric_name": inward_item.po_item.fabric_name if inward_item.po_item else "Ready Item",
                        "ordered_qty": inward_item.po_item.quantity if inward_item.po_item else 0,
                        "inward_qty": inward_item.quantity,
                        "unit": inward_item.po_item.unit if inward_item.po_item else "",
                    }
                    for inward_item in inward.items.all()
                ],
            })

        rows.append({
            "po": po,
            "inward_entries": inward_entries,
        })

    return render(
        request,
        "accounts/ready_po/inward_tracker.html",
        {
            "rows": rows,
            "q": q,
        },
    )
# ==========================
# BRANDS (embed supported)
# ==========================
@login_required
def brand_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = Brand.objects.filter(owner=request.user)
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
        )

    ctx = {"brands": qs.order_by("name"), "q": q}
    tpl = "accounts/brands/list_embed.html" if _is_embed(request) else "accounts/brands/list.html"
    return render(request, tpl, ctx)


@login_required
@require_http_methods(["GET", "POST"])
def brand_create(request):
    form = BrandForm(request.POST or None, user=request.user)

    if request.method == "POST":
        form.instance.owner = request.user

        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()

            url = reverse("accounts:brand_list")
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)

    tpl = "accounts/brands/form_embed.html" if _is_embed(request) else "accounts/brands/form.html"
    return render(request, tpl, {"form": form, "mode": "add"})


@login_required
@require_http_methods(["GET", "POST"])
def brand_update(request, pk: int):
    brand = get_object_or_404(Brand, pk=pk, owner=request.user)
    form = BrandForm(request.POST or None, instance=brand, user=request.user)

    if request.method == "POST" and form.is_valid():
        form.save()

        url = reverse("accounts:brand_list")
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    tpl = "accounts/brands/form_embed.html" if _is_embed(request) else "accounts/brands/form.html"
    return render(request, tpl, {"form": form, "mode": "edit", "brand": brand})


@login_required
@require_POST
def brand_delete(request, pk: int):
    brand = get_object_or_404(Brand, pk=pk, owner=request.user)
    brand.delete()

    url = reverse("accounts:brand_list")
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)

def _materialunit_list_url(request):
    url = reverse("accounts:materialunit_list")
    if _is_embed(request):
        url += "?embed=1"
    return url


@login_required
@require_http_methods(["GET", "POST"])
def materialunit_list_create(request):
    q = (request.GET.get("q") or "").strip()

    units = MaterialUnit.objects.filter(owner=request.user).order_by("name")
    if q:
        units = units.filter(name__icontains=q)

    if request.method == "POST":
        form = MaterialUnitForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()

            url = _materialunit_list_url(request)
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)
    else:
        form = MaterialUnitForm(user=request.user)

    template = "accounts/material_units/list_embed.html" if _is_embed(request) else "accounts/material_units/list.html"
    return render(
        request,
        template,
        {
            "units": units,
            "form": form,
            "q": q,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def materialunit_edit(request, pk: int):
    unit = get_object_or_404(MaterialUnit, pk=pk, owner=request.user)
    form = MaterialUnitForm(request.POST or None, instance=unit, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _materialunit_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = "accounts/material_units/edit_embed.html" if _is_embed(request) else "accounts/material_units/edit.html"
    return render(
        request,
        template,
        {
            "form": form,
            "unit": unit,
        },
    )


@login_required
@require_POST
def materialunit_delete(request, pk: int):
    unit = get_object_or_404(MaterialUnit, pk=pk, owner=request.user)
    unit.delete()

    url = _materialunit_list_url(request)
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)

def _category_list_url(request):
    url = reverse("accounts:category_list")
    if _is_embed(request):
        url += "?embed=1"
    return url

def _expense_list_url(request):
    url = reverse("accounts:expense_list")
    if _is_embed(request):
        url += "?embed=1"
    return url


@login_required
@require_http_methods(["GET", "POST"])
def expense_list_create(request):
    q = (request.GET.get("q") or "").strip()

    expenses = Expense.objects.filter(owner=request.user).order_by("name")
    if q:
        expenses = expenses.filter(name__icontains=q)

    if request.method == "POST":
        form = ExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()

            url = _expense_list_url(request)
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)
    else:
        form = ExpenseForm(user=request.user)

    template = (
        "accounts/expenses/list_embed.html"
        if _is_embed(request)
        else "accounts/expenses/list.html"
    )
    return render(
        request,
        template,
        {
            "expenses": expenses,
            "form": form,
            "q": q,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def expense_edit(request, pk: int):
    expense = get_object_or_404(Expense, pk=pk, owner=request.user)
    form = ExpenseForm(request.POST or None, instance=expense, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _expense_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = (
        "accounts/expenses/edit_embed.html"
        if _is_embed(request)
        else "accounts/expenses/edit.html"
    )
    return render(
        request,
        template,
        {
            "form": form,
            "expense": expense,
        },
    )


@login_required
@require_POST
def expense_delete(request, pk: int):
    expense = get_object_or_404(Expense, pk=pk, owner=request.user)
    expense.delete()

    url = _expense_list_url(request)
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)
# ==========================
# CATEGORIES (embed supported)
# ==========================
@login_required
def category_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = Category.objects.filter(owner=request.user).order_by("name")
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
        )

    ctx = {
        "categories": qs,
        "q": q,
    }
    tpl = "accounts/categories/list_embed.html" if _is_embed(request) else "accounts/categories/list.html"
    return render(request, tpl, ctx)


@login_required
@require_http_methods(["GET", "POST"])
def category_create(request):
    form = CategoryForm(request.POST or None, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _category_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    tpl = "accounts/categories/form_embed.html" if _is_embed(request) else "accounts/categories/form.html"
    return render(request, tpl, {"form": form, "mode": "add"})


@login_required
@require_http_methods(["GET", "POST"])
def category_update(request, pk: int):
    category = get_object_or_404(Category, pk=pk, owner=request.user)
    form = CategoryForm(request.POST or None, instance=category, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _category_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    ctx = {
        "form": form,
        "mode": "edit",
        "category": category,
    }
    tpl = "accounts/categories/form_embed.html" if _is_embed(request) else "accounts/categories/form.html"
    return render(request, tpl, ctx)


@login_required
@require_POST
def category_delete(request, pk: int):
    category = get_object_or_404(Category, pk=pk, owner=request.user)
    category.delete()

    url = _category_list_url(request)
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)

def _maincategory_list_url(request):
    url = reverse("accounts:maincategory_list")
    if _is_embed(request):
        url += "?embed=1"
    return url


@login_required
def maincategory_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = MainCategory.objects.filter(owner=request.user).order_by("name")
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )

    template = (
        "accounts/main_categories/list_embed.html"
        if _is_embed(request)
        else "accounts/main_categories/list.html"
    )
    return render(
        request,
        template,
        {
            "categories": qs,
            "q": q,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def maincategory_create(request):
    form = MainCategoryForm(request.POST or None, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _maincategory_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = (
        "accounts/main_categories/form_embed.html"
        if _is_embed(request)
        else "accounts/main_categories/form.html"
    )
    return render(
        request,
        template,
        {
            "form": form,
            "mode": "add",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def maincategory_edit(request, pk: int):
    category = get_object_or_404(MainCategory, pk=pk, owner=request.user)
    form = MainCategoryForm(request.POST or None, instance=category, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _maincategory_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = (
        "accounts/main_categories/form_embed.html"
        if _is_embed(request)
        else "accounts/main_categories/form.html"
    )
    return render(
        request,
        template,
        {
            "form": form,
            "mode": "edit",
            "category": category,
        },
    )


@login_required
@require_POST
def maincategory_delete(request, pk: int):
    category = get_object_or_404(MainCategory, pk=pk, owner=request.user)
    category.delete()

    url = _maincategory_list_url(request)
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)

def _patterntype_list_url(request):
    url = reverse("accounts:patterntype_list")
    if _is_embed(request):
        url += "?embed=1"
    return url

@login_required
@require_http_methods(["GET", "POST"])
def patterntype_list_create(request):
    q = (request.GET.get("q") or "").strip()

    pattern_types = PatternType.objects.filter(owner=request.user).order_by("name")
    if q:
        pattern_types = pattern_types.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )

    if request.method == "POST":
        form = PatternTypeForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()

            url = _patterntype_list_url(request)
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)
    else:
        form = PatternTypeForm(user=request.user)

    template = (
        "accounts/pattern_types/list_embed.html"
        if _is_embed(request)
        else "accounts/pattern_types/list.html"
    )
    return render(
        request,
        template,
        {
            "pattern_types": pattern_types,
            "form": form,
            "q": q,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def patterntype_edit(request, pk: int):
    pattern_type = get_object_or_404(PatternType, pk=pk, owner=request.user)
    form = PatternTypeForm(request.POST or None, instance=pattern_type, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _patterntype_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = (
        "accounts/pattern_types/edit_embed.html"
        if _is_embed(request)
        else "accounts/pattern_types/edit.html"
    )
    return render(
        request,
        template,
        {
            "form": form,
            "pattern_type": pattern_type,
        },
    )


@login_required
@require_POST
def patterntype_delete(request, pk: int):
    pattern_type = get_object_or_404(PatternType, pk=pk, owner=request.user)
    pattern_type.delete()

    url = _patterntype_list_url(request)
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)

# ==========================
# CATALOGUES (embed supported)
# ==========================
@login_required
def catalogue_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = Catalogue.objects.filter(owner=request.user)
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(wear_type__icontains=q)
            | Q(description__icontains=q)
        )

    ctx = {"catalogues": qs.order_by("name"), "q": q}
    tpl = "accounts/catalogues/list_embed.html" if _is_embed(request) else "accounts/catalogues/list.html"
    return render(request, tpl, ctx)


@login_required
@require_http_methods(["GET", "POST"])
def catalogue_create(request):
    form = CatalogueForm(request.POST or None, user=request.user)

    if request.method == "POST":
        form.instance.owner = request.user

        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()

            url = reverse("accounts:catalogue_list")
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)

    tpl = "accounts/catalogues/form_embed.html" if _is_embed(request) else "accounts/catalogues/form.html"
    return render(request, tpl, {"form": form, "mode": "add"})


@login_required
@require_http_methods(["GET", "POST"])
def catalogue_update(request, pk: int):
    catalogue = get_object_or_404(Catalogue, pk=pk, owner=request.user)
    form = CatalogueForm(request.POST or None, instance=catalogue, user=request.user)

    if request.method == "POST" and form.is_valid():
        form.save()

        url = reverse("accounts:catalogue_list")
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    tpl = "accounts/catalogues/form_embed.html" if _is_embed(request) else "accounts/catalogues/form.html"
    return render(request, tpl, {"form": form, "mode": "edit", "catalogue": catalogue})


@login_required
@require_POST
def catalogue_delete(request, pk: int):
    catalogue = get_object_or_404(Catalogue, pk=pk, owner=request.user)
    catalogue.delete()

    url = reverse("accounts:catalogue_list")
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)

def _build_bom_formsets(request, instance=None):
    bind = request.method == "POST"
    data = request.POST if bind else None

    material_formset = BOMMaterialItemFormSet(
        data=data,
        instance=instance,
        prefix="materials",
        form_kwargs={"user": request.user},
    )

    jobber_formset = BOMJobberItemFormSet(
        data=data,
        instance=instance,
        prefix="jobbers",
        form_kwargs={"user": request.user},
    )

    process_formset = BOMProcessItemFormSet(
        data=data,
        instance=instance,
        prefix="processes",
        form_kwargs={"user": request.user},
    )

    expense_formset = BOMExpenseItemFormSet(
        data=data,
        instance=instance,
        prefix="expenses",
    )

    return material_formset, jobber_formset, process_formset, expense_formset


def _bom_has_at_least_one_material(material_formset):
    for form in material_formset.forms:
        cleaned = getattr(form, "cleaned_data", None) or {}
        if cleaned and not cleaned.get("DELETE") and cleaned.get("material"):
            return True
    return False


@login_required
def bom_list(request):
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()

    qs = (
        BOM.objects.filter(owner=request.user)
        .select_related("brand", "category", "main_category", "pattern_type")
        .prefetch_related(
            Prefetch(
                "material_items",
                queryset=BOMMaterialItem.objects.select_related("material", "unit").order_by("sort_order", "id"),
            ),
            "jobber_items__jobber",
            "jobber_items__jobber_type",
            "process_items__jobber_type",
            "expense_items",
        )
        .order_by("-id")
    )

    if q:
        qs = qs.filter(
            Q(bom_code__icontains=q)
            | Q(sku_code__icontains=q)
            | Q(product_name__icontains=q)
            | Q(catalogue_name__icontains=q)
            | Q(sub_category__icontains=q)
            | Q(character_name__icontains=q)
            | Q(license_name__icontains=q)
            | Q(brand__name__icontains=q)
            | Q(category__name__icontains=q)
            | Q(main_category__name__icontains=q)
            | Q(material_items__material__name__icontains=q)
        ).distinct()

    if status == "active":
        qs = qs.filter(is_discontinued=False)
    elif status == "discontinued":
        qs = qs.filter(is_discontinued=True)

    ctx = {
        "boms": qs,
        "q": q,
        "status": status,
    }
    tpl = "accounts/boms/list_embed.html" if _is_embed(request) else "accounts/boms/list.html"
    return render(request, tpl, ctx)


@login_required
@require_http_methods(["GET", "POST"])
def bom_create(request):
    form = BOMForm(request.POST or None, request.FILES or None, user=request.user)
    material_formset, jobber_formset, process_formset, expense_formset = _build_bom_formsets(request)

    if request.method == "POST":
        is_valid = (
            form.is_valid()
            and material_formset.is_valid()
            and jobber_formset.is_valid()
            and process_formset.is_valid()
            and expense_formset.is_valid()
        )

        if is_valid and not _bom_has_at_least_one_material(material_formset):
            material_formset._non_form_errors = material_formset.error_class(
                ["Add at least one material / fabric / accessory row."]
            )
            is_valid = False

        if is_valid:
            with transaction.atomic():
                bom = form.save(commit=False)
                bom.owner = request.user
                bom.save()

                material_formset.instance = bom
                jobber_formset.instance = bom
                process_formset.instance = bom
                expense_formset.instance = bom

                material_formset.save()
                jobber_formset.save()
                process_formset.save()
                expense_formset.save()

            url = reverse("accounts:bom_list")
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)

    tpl = "accounts/boms/form_embed.html" if _is_embed(request) else "accounts/boms/form.html"
    return render(
        request,
        tpl,
        {
            "form": form,
            "material_formset": material_formset,
            "jobber_formset": jobber_formset,
            "process_formset": process_formset,
            "expense_formset": expense_formset,
            "mode": "add",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def bom_update(request, pk: int):
    bom = get_object_or_404(BOM, pk=pk, owner=request.user)
    form = BOMForm(request.POST or None, request.FILES or None, instance=bom, user=request.user)
    material_formset, jobber_formset, process_formset, expense_formset = _build_bom_formsets(request, instance=bom)

    if request.method == "POST":
        is_valid = (
            form.is_valid()
            and material_formset.is_valid()
            and jobber_formset.is_valid()
            and process_formset.is_valid()
            and expense_formset.is_valid()
        )

        if is_valid and not _bom_has_at_least_one_material(material_formset):
            material_formset._non_form_errors = material_formset.error_class(
                ["Add at least one material / fabric / accessory row."]
            )
            is_valid = False

        if is_valid:
            with transaction.atomic():
                form.save()
                material_formset.save()
                jobber_formset.save()
                process_formset.save()
                expense_formset.save()

            url = reverse("accounts:bom_list")
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)

    tpl = "accounts/boms/form_embed.html" if _is_embed(request) else "accounts/boms/form.html"
    return render(
        request,
        tpl,
        {
            "form": form,
            "material_formset": material_formset,
            "jobber_formset": jobber_formset,
            "process_formset": process_formset,
            "expense_formset": expense_formset,
            "mode": "edit",
            "bom": bom,
        },
    )


@login_required
@require_POST
def bom_delete(request, pk: int):
    bom = get_object_or_404(BOM, pk=pk, owner=request.user)
    bom.delete()

    url = reverse("accounts:bom_list")
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)

# ==========================
# PROGRAMS
# ==========================
PROGRAM_DEFAULT_SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL", "5XL"]


def _program_list_url(request):
    url = reverse("accounts:program_list")
    if _is_embed(request):
        url += "?embed=1"
    return url


def _program_queryset(user):
    return (
        Program.objects
        .filter(owner=user)
        .select_related(
            "firm",
            "bom",
            "bom__brand",
            "bom__category",
            "bom__main_category",
            "bom__pattern_type",
        )
        .prefetch_related(
            Prefetch(
                "jobber_items",
                queryset=ProgramJobberItem.objects.select_related("jobber", "jobber_type").order_by("sort_order", "id"),
            ),
            Prefetch(
                "size_details",
                queryset=ProgramSizeDetail.objects.order_by("id"),
            ),
            Prefetch(
                "bom__material_items",
                queryset=BOMMaterialItem.objects.select_related("material", "unit").order_by("sort_order", "id"),
            ),
            Prefetch(
                "bom__jobber_items",
                queryset=BOMJobberItem.objects.select_related("jobber", "jobber_type").order_by("sort_order", "id"),
            ),
        )
        .order_by("-program_date", "-id")
    )


def _build_program_formsets(request, instance=None):
    bind = request.method == "POST"
    data = request.POST if bind else None

    jobber_formset = ProgramJobberItemFormSet(
        data=data,
        instance=instance,
        prefix="jobbers",
        form_kwargs={"user": request.user},
    )

    size_initial = None
    if not bind and (instance is None or not instance.pk or not instance.size_details.exists()):
        size_initial = [{"size": size} for size in PROGRAM_DEFAULT_SIZES]

    size_formset = ProgramSizeDetailFormSet(
        data=data,
        instance=instance,
        prefix="sizes",
        initial=size_initial,
    )

    return jobber_formset, size_formset


def _program_has_jobber_rows(formset):
    for form in formset.forms:
        cleaned = getattr(form, "cleaned_data", None) or {}
        if cleaned and not cleaned.get("DELETE") and (cleaned.get("jobber") or cleaned.get("jobber_type")):
            return True
    return False


def _program_has_size_rows(formset):
    for form in formset.forms:
        cleaned = getattr(form, "cleaned_data", None) or {}
        if cleaned and not cleaned.get("DELETE") and cleaned.get("size"):
            return True
    return False


def _seed_program_jobbers_from_bom(program):
    if not program.bom_id or program.jobber_items.exists():
        return

    rows = []
    for index, bom_jobber in enumerate(program.bom.jobber_items.all(), start=1):
        rows.append(
            ProgramJobberItem(
                program=program,
                jobber=bom_jobber.jobber,
                jobber_type=bom_jobber.jobber_type,
                jobber_price=bom_jobber.price or Decimal("0"),
                issue_qty=Decimal("0"),
                inward_qty=Decimal("0"),
                sort_order=index,
            )
        )

    if rows:
        ProgramJobberItem.objects.bulk_create(rows)


def _seed_program_sizes(program):
    if program.size_details.exists():
        return

    ProgramSizeDetail.objects.bulk_create([
        ProgramSizeDetail(
            program=program,
            size=size,
            cq=Decimal("0"),
            fq=Decimal("0"),
            dq=Decimal("0"),
            fq_dq=Decimal("0"),
            tp=Decimal("0"),
        )
        for size in PROGRAM_DEFAULT_SIZES
    ])


@login_required
def program_list(request):
    q = (request.GET.get("q") or "").strip()
    sku = (request.GET.get("sku") or "").strip()
    from_date = (request.GET.get("from_date") or "").strip()
    to_date = (request.GET.get("to_date") or "").strip()

    qs = _program_queryset(request.user)

    if from_date:
        qs = qs.filter(program_date__gte=from_date)

    if to_date:
        qs = qs.filter(program_date__lte=to_date)

    if q:
        qs = qs.filter(
            Q(program_no__icontains=q)
            | Q(bom__sku_code__icontains=q)
            | Q(bom__product_name__icontains=q)
            | Q(firm__firm_name__icontains=q)
        ).distinct()

    if sku:
        qs = qs.filter(
            Q(bom__sku_code__icontains=sku)
            | Q(bom__product_name__icontains=sku)
        ).distinct()

    month_groups = []
    current_label = None

    for program in qs:
        label = program.program_date.strftime("%B %Y") if program.program_date else "Programs"

        if label != current_label:
            month_groups.append({
                "label": label,
                "items": [],
            })
            current_label = label

        month_groups[-1]["items"].append(program)

    template = "accounts/programs/list_embed.html" if _is_embed(request) else "accounts/programs/list.html"
    return render(
        request,
        template,
        {
            "month_groups": month_groups,
            "q": q,
            "sku": sku,
            "from_date": from_date,
            "to_date": to_date,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def program_create(request):
    form = ProgramForm(request.POST or None, user=request.user)
    jobber_formset, size_formset = _build_program_formsets(request)

    if request.method == "POST":
        is_valid = form.is_valid() and jobber_formset.is_valid() and size_formset.is_valid()

        if is_valid:
            with transaction.atomic():
                program = form.save(commit=False)
                program.owner = request.user
                program.save()

                jobber_formset.instance = program
                size_formset.instance = program

                if _program_has_jobber_rows(jobber_formset):
                    jobber_formset.save()
                else:
                    _seed_program_jobbers_from_bom(program)

                if _program_has_size_rows(size_formset):
                    size_formset.save()
                else:
                    _seed_program_sizes(program)

            url = _program_list_url(request)
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)

    template = "accounts/programs/form_embed.html" if _is_embed(request) else "accounts/programs/form.html"
    return render(
        request,
        template,
        {
            "form": form,
            "jobber_formset": jobber_formset,
            "size_formset": size_formset,
            "mode": "add",
            "program": None,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def program_update(request, pk: int):
    program = get_object_or_404(_program_queryset(request.user), pk=pk)

    form = ProgramForm(request.POST or None, instance=program, user=request.user)
    jobber_formset, size_formset = _build_program_formsets(request, instance=program)

    if request.method == "POST":
        is_valid = form.is_valid() and jobber_formset.is_valid() and size_formset.is_valid()

        if is_valid:
            with transaction.atomic():
                form.save()
                jobber_formset.save()

                if _program_has_size_rows(size_formset):
                    size_formset.save()
                elif not program.size_details.exists():
                    _seed_program_sizes(program)

            url = _program_list_url(request)
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)

    if request.method == "GET":
        if not program.jobber_items.exists():
            _seed_program_jobbers_from_bom(program)
            program = get_object_or_404(_program_queryset(request.user), pk=pk)
            jobber_formset, size_formset = _build_program_formsets(request, instance=program)

        if not program.size_details.exists():
            _seed_program_sizes(program)
            program = get_object_or_404(_program_queryset(request.user), pk=pk)
            jobber_formset, size_formset = _build_program_formsets(request, instance=program)

    template = "accounts/programs/form_embed.html" if _is_embed(request) else "accounts/programs/form.html"
    return render(
        request,
        template,
        {
            "form": form,
            "jobber_formset": jobber_formset,
            "size_formset": size_formset,
            "mode": "edit",
            "program": program,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def program_delete(request, pk: int):
    program = get_object_or_404(Program, pk=pk, owner=request.user)

    if request.method == "POST":
        program.delete()
        url = _program_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = "accounts/programs/confirm_delete.html" if _is_embed(request) else "accounts/programs/confirm_delete.html"
    return render(
        request,
        template,
        {
            "program": program,
        },
    )


@login_required
def program_bom_summary(request, bom_id: int):
    bom = get_object_or_404(
        BOM.objects
        .filter(owner=request.user)
        .select_related("brand", "category", "main_category", "pattern_type")
        .prefetch_related(
            Prefetch(
                "material_items",
                queryset=BOMMaterialItem.objects.select_related("material", "unit").order_by("sort_order", "id"),
            ),
            Prefetch(
                "jobber_items",
                queryset=BOMJobberItem.objects.select_related("jobber", "jobber_type").order_by("sort_order", "id"),
            ),
        ),
        pk=bom_id,
    )

    data = {
        "sku_name": bom.display_sku_name,
        "sku_code": bom.sku_code,
        "product_name": bom.product_name,
        "linked_fabric_names": bom.linked_fabric_names,
        "linked_accessory_names": bom.linked_accessory_names,
        "brand_name": bom.display_brand_name,
        "gender": bom.get_gender_display(),
        "main_category_name": bom.display_main_category_name,
        "category_name": bom.display_category_name,
        "sub_category_name": bom.sub_category,
        "pattern_type_name": bom.display_pattern_type_name,
        "license_name": bom.license_name,
        "character_name": bom.character_name,
        "mrp": str(bom.selling_price or Decimal("0")),
        "color_drawcord_tie_dye_price": str(bom.color_price or Decimal("0")),
        "accessories_price": str(bom.accessories_price or Decimal("0")),
        "product_image_url": bom.product_image.url if bom.product_image else "",
        "jobbers": [
            {
                "jobber_id": item.jobber_id,
                "jobber_name": item.jobber.name if item.jobber else "",
                "jobber_type_id": item.jobber_type_id,
                "jobber_type_name": item.jobber_type.name if item.jobber_type else "",
                "jobber_price": str(item.price or Decimal("0")),
            }
            for item in bom.jobber_items.all()
        ],
    }
    return JsonResponse(data)