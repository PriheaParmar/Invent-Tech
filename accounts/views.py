from django.db import transaction
import logging
from io import BytesIO
from decimal import Decimal, InvalidOperation
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.db.models import Q, Prefetch, Sum, Count

logger = logging.getLogger(__name__)
from datetime import timedelta
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
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_GET, require_POST

from .forms import (
    FirmForm,
    GreigePurchaseOrderForm,
    GreigePOInwardForm,
    DyeingPurchaseOrderForm,
    DyeingPOInwardForm,
    JobberForm,
    InwardTypeForm,
    DyeingOtherChargeForm,
    TermsConditionForm,
    JobberTypeForm,
    LocationForm,    MainCategoryForm,
    CategoryForm,    
    ClientForm,
    DashboardProfileForm,
    BOMForm,    
    ProgramForm,
    ProgramJobberItemFormSet,
    ProgramSizeDetailFormSet,
    BOMMaterialItemFormSet,
    BOMJobberItemFormSet,
    BOMProcessItemFormSet,
    BOMExpenseItemFormSet,
    BOMImageFormSet,
    MaterialForm,
    SubCategoryForm,
    MaterialShadeForm,
    MaterialSubTypeForm,
    MaterialTypeForm,
    PartyForm,
    MainCategoryForm,
    PatternTypeForm,
    VendorForm,
    CatalogueForm,
    ExpenseForm,
    BrandForm,    GreigePOReviewForm,
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
    Client,
    DyeingPurchaseOrder,
    DyeingPurchaseOrderItem,
    InwardType,
    BOM,
    BOMMaterialItem,
    BOMJobberItem,
    TermsCondition,
    DyeingOtherCharge,
    BOMProcessItem,
    BOMExpenseItem,
    BOMImage,
    DyeingPOInward,
    Catalogue,
    DyeingPOInwardItem,
    Jobber,
    SubCategory,
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
def _client_list_url(request):
    url = reverse("accounts:client_list")
    if _is_embed(request):
        url += "?embed=1"
    return url


@login_required
def client_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = Client.objects.filter(owner=request.user)
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(contact_person__icontains=q)
            | Q(phone__icontains=q)
            | Q(email__icontains=q)
            | Q(gst_number__icontains=q)
            | Q(pan_number__icontains=q)
            | Q(city__icontains=q)
        )

    ctx = {"clients": qs.order_by("name"), "q": q}
    tpl = "accounts/clients/list_embed.html" if _is_embed(request) else "accounts/clients/list.html"
    return render(request, tpl, ctx)


@login_required
@require_http_methods(["GET", "POST"])
def client_create(request):
    form = ClientForm(request.POST or None, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _client_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    tpl = "accounts/clients/form_embed.html" if _is_embed(request) else "accounts/clients/form.html"
    return render(request, tpl, {"form": form, "mode": "add"})


@login_required
@require_http_methods(["GET", "POST"])
def client_update(request, pk: int):
    client = get_object_or_404(Client, pk=pk, owner=request.user)
    form = ClientForm(request.POST or None, instance=client, user=request.user)

    if request.method == "POST" and form.is_valid():
        form.save()

        url = _client_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    tpl = "accounts/clients/form_embed.html" if _is_embed(request) else "accounts/clients/form.html"
    return render(request, tpl, {"form": form, "mode": "edit", "client": client})


@login_required
@require_POST
def client_delete(request, pk: int):
    client = get_object_or_404(Client, pk=pk, owner=request.user)
    client.delete()

    url = _client_list_url(request)
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)


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
        import os
        from pathlib import Path
        from html import escape

        from django.conf import settings
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.lib.utils import ImageReader
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return HttpResponse(
            "ReportLab is required for PDF generation. Install it with: pip install reportlab",
            status=500,
        )

    brand_pink = colors.HexColor("#ED2F8C")
    brand_orange = colors.HexColor("#F6A33B")
    brand_blue = colors.HexColor("#1976F3")
    brand_navy = colors.HexColor("#0F172A")
    ink = colors.HexColor("#1F2937")
    muted = colors.HexColor("#667085")
    border = colors.HexColor("#D0D5DD")
    soft_bg = colors.HexColor("#F8FAFC")
    white = colors.white

    def text_or_dash(value):
        value = "" if value is None else str(value).strip()
        return value if value else "-"

    def fmt_money(value):
        try:
            return f"{float(value or 0):,.2f}"
        except Exception:
            return f"{value or '0.00'}"

    def fmt_qty(value):
        try:
            return f"{float(value or 0):,.2f}".rstrip("0").rstrip(".")
        except Exception:
            return text_or_dash(value)

    def line_if(label, value):
        value = "" if value is None else str(value).strip()
        if not value:
            return ""
        return f"<b>{escape(label)}:</b> {escape(value)}"

    def join_parts(*parts):
        clean = [str(p).strip() for p in parts if str(p).strip()]
        return ", ".join(clean)

    def resolve_logo_path():
        if po.firm and getattr(po.firm, "logo", None):
            try:
                logo_path = po.firm.logo.path
                if logo_path and os.path.exists(logo_path):
                    return logo_path
            except Exception:
                pass

        fallback = Path(settings.BASE_DIR) / "Logo.jpeg"
        if fallback.exists():
            return str(fallback)

        return None

    logo_path = resolve_logo_path()

    def draw_branding(canvas, doc):
        page_w, page_h = A4
        canvas.saveState()

        canvas.setStrokeColor(colors.HexColor("#E4E7EC"))
        canvas.setLineWidth(0.8)
        canvas.roundRect(8 * mm, 8 * mm, page_w - 16 * mm, page_h - 16 * mm, 4 * mm, stroke=1, fill=0)

        usable_w = page_w - 16 * mm
        stripe_w = usable_w / 3.0
        stripe_y = page_h - 13 * mm
        stripe_h = 4.5 * mm

        canvas.setFillColor(brand_pink)
        canvas.rect(8 * mm, stripe_y, stripe_w, stripe_h, fill=1, stroke=0)

        canvas.setFillColor(brand_orange)
        canvas.rect(8 * mm + stripe_w, stripe_y, stripe_w, stripe_h, fill=1, stroke=0)

        canvas.setFillColor(brand_blue)
        canvas.rect(8 * mm + 2 * stripe_w, stripe_y, stripe_w, stripe_h, fill=1, stroke=0)

        if logo_path:
            try:
                img = ImageReader(logo_path)
                iw, ih = img.getSize()
                draw_w = 26 * mm
                draw_h = draw_w * (ih / float(iw)) if iw and ih else 26 * mm
                x = (page_w - draw_w) / 2.0
                y = 10 * mm

                try:
                    canvas.setFillAlpha(0.10)
                    canvas.setStrokeAlpha(0.10)
                except Exception:
                    pass

                canvas.drawImage(
                    img,
                    x,
                    y,
                    width=draw_w,
                    height=draw_h,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass

        canvas.restoreState()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    styles = getSampleStyleSheet()

    base_style = ParagraphStyle(
        "YPOBase",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=10.5,
        textColor=ink,
        spaceAfter=0,
    )

    header_left_style = ParagraphStyle(
        "YPOHeaderLeft",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8.4,
        leading=10.4,
        textColor=white,
        alignment=TA_LEFT,
    )

    header_title_style = ParagraphStyle(
        "YPOHeaderTitle",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=16,
        textColor=brand_navy,
        alignment=TA_RIGHT,
    )

    header_meta_style = ParagraphStyle(
        "YPOHeaderMeta",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8.3,
        leading=10.2,
        textColor=ink,
        alignment=TA_RIGHT,
    )

    section_head_left = ParagraphStyle(
        "YPOSectionHeadLeft",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=white,
        alignment=TA_LEFT,
    )

    section_value_style = ParagraphStyle(
        "YPOSectionValue",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8.2,
        leading=10.2,
        textColor=ink,
        alignment=TA_LEFT,
    )

    table_head_style = ParagraphStyle(
        "YPOTableHead",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=7.8,
        leading=9.5,
        textColor=white,
        alignment=TA_CENTER,
    )

    item_center_style = ParagraphStyle(
        "YPOItemCenter",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8,
        leading=9.6,
        alignment=TA_CENTER,
    )

    item_desc_style = ParagraphStyle(
        "YPOItemDesc",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8,
        leading=9.6,
        alignment=TA_LEFT,
    )

    money_style = ParagraphStyle(
        "YPOMoney",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8,
        leading=9.6,
        alignment=TA_RIGHT,
    )

    block_title_style = ParagraphStyle(
        "YPOBlockTitle",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=8.4,
        leading=10.5,
        textColor=brand_navy,
        alignment=TA_LEFT,
    )

    block_text_style = ParagraphStyle(
        "YPOBlockText",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8.1,
        leading=10.1,
        textColor=ink,
        alignment=TA_LEFT,
    )

    sign_style = ParagraphStyle(
        "YPOSign",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=ink,
        alignment=TA_LEFT,
    )

    total_label_style = ParagraphStyle(
        "YPOTotalLabel",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=8.2,
        leading=10.2,
        textColor=ink,
        alignment=TA_LEFT,
    )

    total_value_style = ParagraphStyle(
        "YPOTotalValue",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=8.2,
        leading=10.2,
        textColor=ink,
        alignment=TA_RIGHT,
    )

    footer_note_style = ParagraphStyle(
        "YPOFooterNote",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=7.6,
        leading=9.2,
        textColor=muted,
        alignment=TA_CENTER,
    )

    story = []

    firm = po.firm
    vendor = po.vendor
    po_items = list(po.items.all())

    firm_name = text_or_dash(firm.firm_name if firm else "InventTech")
    firm_type = ""
    if firm:
        try:
            firm_type = firm.get_firm_type_display()
        except Exception:
            firm_type = text_or_dash(getattr(firm, "firm_type", ""))

    firm_address = join_parts(
        getattr(firm, "address_line", ""),
        getattr(firm, "city", ""),
        getattr(firm, "state", ""),
        getattr(firm, "pincode", ""),
    )

    firm_contact_line = " | ".join([
        part for part in [
            line_if("Phone", getattr(firm, "phone", "")),
            line_if("Email", getattr(firm, "email", "")),
            line_if("GSTIN", getattr(firm, "gst_number", "")),
        ] if part
    ])

    firm_stat_line = " | ".join([
        part for part in [
            line_if("PAN", getattr(firm, "pan_number", "")),
            line_if("TAN", getattr(firm, "tan_number", "")),
            line_if("CIN", getattr(firm, "cin_number", "")),
        ] if part
    ])

    order_number = po.po_number or po.system_number or "-"
    po_date = po.po_date.strftime("%d-%m-%Y") if po.po_date else "-"
    cancel_date = po.cancel_date.strftime("%d-%m-%Y") if po.cancel_date else "-"
    approval_label = getattr(po, "get_approval_status_display", lambda: text_or_dash(po.approval_status))()

    firm_header_html = f"<font size='13'><b>{escape(firm_name)}</b></font>"
    if firm_type and firm_type != "-":
        firm_header_html += f"<br/>{escape(firm_type)}"
    if firm_address:
        firm_header_html += f"<br/>{escape(firm_address)}"
    if firm_contact_line:
        firm_header_html += f"<br/>{firm_contact_line}"
    if firm_stat_line:
        firm_header_html += f"<br/>{firm_stat_line}"

    po_meta_html = (
        f"<b>YARN PURCHASE ORDER</b><br/>"
        f"<b>PO No:</b> {escape(order_number)}<br/>"
        f"<b>PO Date:</b> {escape(po_date)}<br/>"
        f"<b>System No:</b> {escape(text_or_dash(po.system_number))}<br/>"
        f"<b>Status:</b> {escape(text_or_dash(approval_label))}"
    )
    if cancel_date != "-":
        po_meta_html += f"<br/><b>Cancel Date:</b> {escape(cancel_date)}"

    header_table = Table(
        [[
            Paragraph(firm_header_html, header_left_style),
            Table(
                [[
                    Paragraph("<b>YARN PURCHASE ORDER</b>", header_title_style),
                ], [
                    Paragraph(
                        f"<b>PO No:</b> {escape(order_number)}<br/>"
                        f"<b>PO Date:</b> {escape(po_date)}<br/>"
                        f"<b>System No:</b> {escape(text_or_dash(po.system_number))}<br/>"
                        f"<b>Status:</b> {escape(text_or_dash(approval_label))}"
                        + (f"<br/><b>Cancel Date:</b> {escape(cancel_date)}" if cancel_date != "-" else ""),
                        header_meta_style,
                    )
                ]],
                colWidths=[66 * mm],
            ),
        ]],
        colWidths=[124 * mm, 66 * mm],
    )
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), brand_navy),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F5F8FF")),
        ("BOX", (0, 0), (-1, -1), 0.9, border),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 9),
        ("RIGHTPADDING", (0, 0), (0, 0), 9),
        ("TOPPADDING", (0, 0), (0, 0), 9),
        ("BOTTOMPADDING", (0, 0), (0, 0), 9),
        ("LEFTPADDING", (1, 0), (1, 0), 0),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("TOPPADDING", (1, 0), (1, 0), 0),
        ("BOTTOMPADDING", (1, 0), (1, 0), 0),
    ]))
    header_table._argW[1] = 66 * mm
    inner_header = header_table._cellvalues[0][1]
    inner_header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F8FF")),
        ("BOX", (0, 0), (-1, -1), 0.9, brand_blue),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6))

    vendor_html = f"<b>{escape(text_or_dash(vendor.name if vendor else ''))}</b>"
    vendor_lines = [
        line_if("Contact", vendor.contact_person if vendor else ""),
        line_if("Phone", vendor.phone if vendor else ""),
        line_if("Email", vendor.email if vendor else ""),
        line_if("GSTIN", vendor.gst_number if vendor else ""),
        line_if("Address", vendor.address if vendor else ""),
    ]
    vendor_body = "<br/>".join([line for line in vendor_lines if line])
    if vendor_body:
        vendor_html += "<br/>" + vendor_body

    bill_to_html = f"<b>{escape(text_or_dash(firm_name if firm else ''))}</b>"
    bill_lines = [
        line_if("Address", firm_address),
        line_if("Phone", getattr(firm, "phone", "")),
        line_if("Email", getattr(firm, "email", "")),
        line_if("GSTIN", getattr(firm, "gst_number", "")),
        line_if("Ship To", po.shipping_address),
    ]
    bill_body = "<br/>".join([line for line in bill_lines if line])
    if bill_body:
        bill_to_html += "<br/>" + bill_body

    party_table = Table(
        [
            [
                Paragraph("VENDOR", section_head_left),
                Paragraph("BILL TO", section_head_left),
            ],
            [
                Paragraph(vendor_html, section_value_style),
                Paragraph(bill_to_html, section_value_style),
            ],
        ],
        colWidths=[95 * mm, 95 * mm],
    )
    party_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), brand_orange),
        ("BACKGROUND", (1, 0), (1, 0), brand_blue),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#FBFCFE")),
        ("BOX", (0, 0), (-1, -1), 0.9, border),
        ("INNERGRID", (0, 0), (-1, -1), 0.7, border),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(party_table)
    story.append(Spacer(1, 7))

    item_rows = [[
        Paragraph("Sr No", table_head_style),
        Paragraph("Description", table_head_style),
        Paragraph("Unit", table_head_style),
        Paragraph("Qty", table_head_style),
        Paragraph("Price (Rs.)", table_head_style),
        Paragraph("Amount (Rs.)", table_head_style),
    ]]

    for index, item in enumerate(po_items, start=1):
        material_name = "-"
        if item.material_type:
            material_name = item.material_type.name
        elif item.material:
            material_name = str(item.material)

        details = []
        if item.count:
            details.append(f"Count: {item.count}")
        if item.dia:
            details.append(f"Dia: {item.dia}")
        if item.gauge:
            details.append(f"Gauge: {item.gauge}")
        if item.gsm:
            details.append(f"GSM: {item.gsm}")
        if item.sl:
            details.append(f"SL: {item.sl}")
        if item.rolls:
            details.append(f"Rolls: {item.rolls}")
        if item.hsn_code:
            details.append(f"HSN: {item.hsn_code}")
        if item.remark:
            details.append(f"Remark: {item.remark}")

        description_html = f"<b>{escape(text_or_dash(material_name))}</b>"
        if details:
            description_html += "<br/>" + escape(" | ".join(details))

        item_rows.append([
            Paragraph(str(index), item_center_style),
            Paragraph(description_html, item_desc_style),
            Paragraph(escape(text_or_dash(item.unit)), item_center_style),
            Paragraph(escape(fmt_qty(item.quantity)), item_center_style),
            Paragraph(escape(fmt_money(item.rate)), money_style),
            Paragraph(escape(fmt_money(item.final_amount)), money_style),
        ])

    min_visual_rows = 5
    for _ in range(max(0, min_visual_rows - len(po_items))):
        item_rows.append([
            Paragraph("", item_center_style),
            Paragraph("", item_desc_style),
            Paragraph("", item_center_style),
            Paragraph("", item_center_style),
            Paragraph("", money_style),
            Paragraph("", money_style),
        ])

    items_table = Table(
        item_rows,
        colWidths=[13 * mm, 86 * mm, 18 * mm, 18 * mm, 26 * mm, 29 * mm],
        repeatRows=1,
    )
    items_table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), brand_navy),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("BOX", (0, 0), (-1, -1), 0.9, border),
        ("INNERGRID", (0, 0), (-1, -1), 0.55, border),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])

    for row_index in range(1, len(item_rows)):
        if row_index % 2 == 0:
            items_table_style.add("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#F9FAFB"))

    items_table.setStyle(items_table_style)
    story.append(items_table)
    story.append(Spacer(1, 8))

    notes_parts = []
    if po.remarks:
        notes_parts.append(f"<font color='#0F172A'><b>Remarks</b></font><br/>{escape(po.remarks).replace(chr(10), '<br/>')}")
    if po.terms_conditions:
        notes_parts.append(f"<font color='#0F172A'><b>Terms &amp; Conditions</b></font><br/>{escape(po.terms_conditions).replace(chr(10), '<br/>')}")
    if po.shipping_address:
        notes_parts.append(f"<font color='#0F172A'><b>Shipping Address</b></font><br/>{escape(po.shipping_address).replace(chr(10), '<br/>')}")

    if not notes_parts:
        notes_parts.append("<font color='#0F172A'><b>Notes</b></font><br/>Standard terms and conditions apply.")

    notes_html = "<br/><br/>".join(notes_parts)

    signature_table = Table(
        [[
            Paragraph("<b>AUTHORISED SIGNATORY</b><br/><br/>_________________________", sign_style),
            Paragraph(f"<b>DATE</b><br/><br/>{escape(po_date)}", sign_style),
        ]],
        colWidths=[68 * mm, 30 * mm],
    )
    signature_table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    left_block = Table(
        [
            [Paragraph("NOTES / TERMS", block_title_style)],
            [Paragraph(notes_html, block_text_style)],
            [signature_table],
        ],
        colWidths=[102 * mm],
    )
    left_block.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#FDF2F8")),
        ("BOX", (0, 0), (-1, -1), 0.9, border),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    discount_amount = Decimal(po.subtotal or 0) - Decimal(po.after_discount_value or 0)
    if discount_amount < 0:
        discount_amount = Decimal("0")

    taxable_amount = Decimal(po.after_discount_value or 0) + Decimal(po.others or 0)
    cgst_amount = taxable_amount * Decimal(po.cgst_percent or 0) / Decimal("100")
    sgst_amount = taxable_amount * Decimal(po.sgst_percent or 0) / Decimal("100")

    totals_rows = [
        [Paragraph("Sub Total", total_label_style), Paragraph(escape(fmt_money(po.subtotal)), total_value_style)],
        [Paragraph("Discount Amount", total_label_style), Paragraph(escape(fmt_money(discount_amount)), total_value_style)],
        [Paragraph("After Discount Amount", total_label_style), Paragraph(escape(fmt_money(po.after_discount_value)), total_value_style)],
        [Paragraph("Other Charges", total_label_style), Paragraph(escape(fmt_money(po.others)), total_value_style)],
        [Paragraph(f"CGST ({fmt_qty(po.cgst_percent)}%)", total_label_style), Paragraph(escape(fmt_money(cgst_amount)), total_value_style)],
        [Paragraph(f"SGST ({fmt_qty(po.sgst_percent)}%)", total_label_style), Paragraph(escape(fmt_money(sgst_amount)), total_value_style)],
        [Paragraph("Total Amount", total_label_style), Paragraph(escape(fmt_money(po.grand_total)), total_value_style)],
    ]

    totals_table = Table(totals_rows, colWidths=[49 * mm, 39 * mm])
    totals_table_style = TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.9, border),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FFF7ED")),
    ])
    for row_index in range(1, len(totals_rows) - 1):
        if row_index % 2 == 1:
            totals_table_style.add("BACKGROUND", (0, row_index), (-1, row_index), soft_bg)
    totals_table.setStyle(totals_table_style)

    lower_table = Table([[left_block, totals_table]], colWidths=[102 * mm, 88 * mm])
    lower_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(lower_table)
    story.append(Spacer(1, 8))

    footer_table = Table(
        [[Paragraph("THIS PO IS COMPUTER GENERATED, HENCE SIGNATURE IS NOT REQUIRED", footer_note_style)]],
        colWidths=[190 * mm],
    )
    footer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.9, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(footer_table)

    doc.build(story, onFirstPage=draw_branding, onLaterPages=draw_branding)
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

    if request.method == "POST":
        if form.is_valid() and formset.is_valid():
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

            messages.success(request, f"Yarn PO {po.system_number} saved successfully.")
            return redirect("accounts:yarnpo_list")

        form.add_error(None, "Yarn PO was not saved. Please fix the highlighted fields and try again.")

    return render(request, "accounts/yarn_po/form.html", {
        "form": form,
        "formset": formset,
        "mode": "add",
        "po_obj": po,
        "system_number_preview": po.system_number or _next_yarn_po_number(),
        "auto_firm_name": default_firm.firm_name if default_firm else "",
        "terms_condition_map": {str(obj.pk): obj.content for obj in form.fields["terms_template"].queryset},
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

    if request.method == "POST":
        if form.is_valid() and formset.is_valid():
            po = form.save(commit=False)

            if default_firm:
                po.firm = default_firm

            if po.firm and not po.shipping_address:
                po.shipping_address = _firm_address(po.firm)

            po.save()
            formset.instance = po
            formset.save()
            _recalculate_yarn_po(po)

            messages.success(request, f"Yarn PO {po.system_number} updated successfully.")
            return redirect("accounts:yarnpo_list")

        form.add_error(None, "Yarn PO was not updated. Please fix the highlighted fields and try again.")

    return render(request, "accounts/yarn_po/form.html", {
        "form": form,
        "formset": formset,
        "mode": "edit",
        "po_obj": po,
        "system_number_preview": po.system_number,
        "auto_firm_name": display_firm.firm_name if display_firm else "",
        "terms_condition_map": {str(obj.pk): obj.content for obj in form.fields["terms_template"].queryset},
    })
    
def _build_simple_yarn_po_pdf_response(po):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except ImportError:
        return HttpResponse(
            "ReportLab is required for PDF generation. Install it with: pip install reportlab",
            status=500,
        )

    def safe_text(value):
        value = "" if value is None else str(value).strip()
        return value if value else "-"

    def qty_text(value):
        try:
            return f"{float(value or 0):,.2f}".rstrip("0").rstrip(".")
        except Exception:
            return safe_text(value)

    def money_text(value):
        try:
            return f"{float(value or 0):,.2f}"
        except Exception:
            return safe_text(value)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    left = 15 * mm
    top = height - 18 * mm
    line_gap = 5.5 * mm

    def draw_line(label, value, y, bold=False):
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 9)
        pdf.drawString(left, y, f"{label}: {safe_text(value)}")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(left, top, safe_text(po.firm.firm_name if po.firm else "InventTech"))

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawRightString(width - 15 * mm, top, "YARN PURCHASE ORDER")

    y = top - 9 * mm
    draw_line("PO No", po.po_number or po.system_number, y)
    draw_line("PO Date", po.po_date.strftime("%d-%m-%Y") if po.po_date else "-", y - line_gap)
    draw_line("System No", po.system_number, y - (2 * line_gap))
    draw_line("Status", po.get_approval_status_display(), y - (3 * line_gap))

    y -= 28 * mm

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(left, y, "Vendor")
    pdf.drawString(width / 2, y, "Bill To")

    y -= 6 * mm
    pdf.setFont("Helvetica", 9)
    vendor_lines = [
        safe_text(po.vendor.name if po.vendor else ""),
        f"Phone: {safe_text(po.vendor.phone if po.vendor else '')}",
        f"Email: {safe_text(po.vendor.email if po.vendor else '')}",
        f"GSTIN: {safe_text(po.vendor.gst_number if po.vendor else '')}",
        f"Address: {safe_text(po.vendor.address if po.vendor else '')}",
    ]
    bill_lines = [
        safe_text(po.firm.firm_name if po.firm else ""),
        f"Phone: {safe_text(getattr(po.firm, 'phone', ''))}",
        f"Email: {safe_text(getattr(po.firm, 'email', ''))}",
        f"GSTIN: {safe_text(getattr(po.firm, 'gst_number', ''))}",
        f"Ship To: {safe_text(po.shipping_address)}",
    ]

    for idx in range(max(len(vendor_lines), len(bill_lines))):
        vendor_text = vendor_lines[idx] if idx < len(vendor_lines) else ""
        bill_text = bill_lines[idx] if idx < len(bill_lines) else ""
        pdf.drawString(left, y, vendor_text)
        pdf.drawString(width / 2, y, bill_text)
        y -= 5 * mm

    y -= 3 * mm

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(left, y, "Sr")
    pdf.drawString(left + 12 * mm, y, "Description")
    pdf.drawString(left + 98 * mm, y, "Unit")
    pdf.drawRightString(left + 128 * mm, y, "Qty")
    pdf.drawRightString(left + 158 * mm, y, "Price")
    pdf.drawRightString(width - 15 * mm, y, "Amount")

    y -= 4 * mm
    pdf.line(left, y, width - 15 * mm, y)
    y -= 6 * mm

    items = list(po.items.all())
    for index, item in enumerate(items, start=1):
        if y < 45 * mm:
            pdf.showPage()
            y = height - 20 * mm

        item_name = "-"
        if item.material_type:
            item_name = item.material_type.name
        elif item.material:
            item_name = str(item.material)

        detail_bits = []
        if item.count:
            detail_bits.append(f"Count: {item.count}")
        if item.dia:
            detail_bits.append(f"Dia: {item.dia}")
        if item.gauge:
            detail_bits.append(f"Gauge: {item.gauge}")
        if item.gsm:
            detail_bits.append(f"GSM: {item.gsm}")
        if item.rolls:
            detail_bits.append(f"Rolls: {item.rolls}")
        if item.hsn_code:
            detail_bits.append(f"HSN: {item.hsn_code}")

        desc = safe_text(item_name)
        if detail_bits:
            desc += " | " + " | ".join(detail_bits)

        pdf.setFont("Helvetica", 8.5)
        pdf.drawString(left, y, str(index))
        pdf.drawString(left + 12 * mm, y, desc[:70])
        pdf.drawString(left + 98 * mm, y, safe_text(item.unit))
        pdf.drawRightString(left + 128 * mm, y, qty_text(item.quantity))
        pdf.drawRightString(left + 158 * mm, y, money_text(item.rate))
        pdf.drawRightString(width - 15 * mm, y, money_text(item.final_amount))
        y -= 6 * mm

    y -= 4 * mm
    pdf.line(left, y, width - 15 * mm, y)
    y -= 8 * mm

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawRightString(left + 158 * mm, y, "Total Amount")
    pdf.drawRightString(width - 15 * mm, y, money_text(po.grand_total))

    y -= 12 * mm
    pdf.setFont("Helvetica", 8.5)
    pdf.drawString(left, y, "THIS PO IS COMPUTER GENERATED, HENCE SIGNATURE IS NOT REQUIRED")

    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    return response


@login_required
def yarnpo_pdf(request, pk: int):
    po = get_object_or_404(
        YarnPurchaseOrder.objects
        .select_related("vendor", "firm", "owner")
        .prefetch_related(
            Prefetch("items", queryset=YarnPurchaseOrderItem.objects.select_related("material", "material_type"))
        ),
        pk=pk,
    )

    if not _can_access_yarn_po(request.user, po):
        raise PermissionDenied("You do not have access to this PO.")

    try:
        response = _build_yarn_po_pdf_response(po)
    except Exception:
        logger.exception("Branded Yarn PO PDF generation failed for PO id=%s system_no=%s", po.pk, po.system_number)
        response = _build_simple_yarn_po_pdf_response(po)

    if response.status_code == 200 and response.get("Content-Type", "").startswith("application/pdf"):
        filename = f'{po.system_number or "yarn_po"}.pdf'
        disposition = "attachment" if request.GET.get("download") == "1" else "inline"
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        response["Cache-Control"] = "no-store"
        response["X-Content-Type-Options"] = "nosniff"
        try:
            response["Content-Length"] = str(len(response.content))
        except Exception:
            pass

    return response

def _build_yarn_inward_line_rows(po, line_inputs=None, item_errors=None):
    line_inputs = line_inputs or {}
    item_errors = item_errors or {}

    rows = []
    for item in po.items.all():
        row_input = line_inputs.get(item.id, {})
        rows.append({
            "item": item,
            "qty_value": row_input.get("qty", ""),
            "remark_value": row_input.get("remark", ""),
            "error": item_errors.get(item.id, ""),
        })
    return rows

@login_required
@require_http_methods(["GET", "POST"])
def yarnpo_inward(request, pk: int):
    po = get_object_or_404(
        YarnPurchaseOrder.objects
        .select_related("vendor", "firm", "owner")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=YarnPurchaseOrderItem.objects.select_related("material", "material_type").prefetch_related("inward_items"),
            ),
            Prefetch(
                "inwards",
                queryset=YarnPOInward.objects.select_related("vendor", "inward_type").prefetch_related("items__po_item__material"),
            ),
        ),
        pk=pk,
    )

    if not _can_access_yarn_po(request.user, po):
        raise PermissionDenied("You do not have access to this PO.")
    
    if not _is_po_approved_for_inward(po):
        messages.error(request, "Yarn PO must be approved before inward can be generated.")
        return redirect("accounts:yarnpo_list")

    po = _attach_yarn_po_metrics(po)
    item_errors = {}
    line_inputs = {}

    inward_form = YarnPOInwardForm(request.POST or None, user=po.owner)

    has_remaining_qty = any(
        (item.remaining_qty_total or Decimal("0")) > 0
        for item in po.items.all()
    )

    if request.method == "POST":
        if not has_remaining_qty:
            inward_form.is_valid()
            inward_form.add_error(None, "No quantity is remaining for inward in this Yarn PO.")
        elif inward_form.is_valid():
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

                if qty > (item.remaining_qty_total or Decimal("0")):
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

                tracker_url = reverse("accounts:yarn_inward_tracker")
                return redirect(f"{tracker_url}?inward={inward.pk}")

    existing_inwards = po.inwards.all().order_by("-inward_date", "-id")
    line_rows = _build_yarn_inward_line_rows(po, line_inputs=line_inputs, item_errors=item_errors)

    return render(
        request,
        "accounts/yarn_po/inward.html",
        {
            "po": po,
            "inward_form": inward_form,
            "item_errors": item_errors,
            "line_inputs": line_inputs,
            "line_rows": line_rows,
            "existing_inwards": existing_inwards,
            "next_inward_number_preview": _next_yarn_inward_number(),
            "has_remaining_qty": has_remaining_qty,
            "editing_inward": None,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def yarn_inward_update(request, pk: int):
    inward = get_object_or_404(
        YarnPOInward.objects
        .select_related("po__vendor", "po__firm", "po__owner", "vendor", "inward_type")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=YarnPOInwardItem.objects.select_related("po_item__material", "po_item__material_type"),
            ),
            "generated_greige_pos",
            Prefetch(
                "po__items",
                queryset=YarnPurchaseOrderItem.objects.select_related("material", "material_type").prefetch_related("inward_items"),
            ),
            Prefetch(
                "po__inwards",
                queryset=YarnPOInward.objects.select_related("vendor", "inward_type").prefetch_related("items__po_item__material"),
            ),
        ),
        pk=pk,
    )

    po = inward.po

    if not _can_access_yarn_po(request.user, po):
        raise PermissionDenied("You do not have access to this inward.")
    
    if not _is_po_approved_for_inward(po):
        messages.error(request, "Yarn PO must be approved before inward can be updated.")
        return redirect("accounts:yarnpo_list")

    if inward.generated_greige_pos.exists():
        messages.error(request, "This inward cannot be edited because a Greige PO has already been generated from it.")
        tracker_url = reverse("accounts:yarn_inward_tracker")
        return redirect(f"{tracker_url}?inward={inward.pk}")

    po = _attach_yarn_po_metrics(po)
    item_errors = {}
    existing_item_map = {
        row.po_item_id: {
            "qty": str(row.quantity or ""),
            "remark": row.remark or "",
        }
        for row in inward.items.all()
    }
    line_inputs = dict(existing_item_map)

    inward_form = YarnPOInwardForm(request.POST or None, instance=inward, user=po.owner)

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

            other_inward_qty = (
                item.inward_items.exclude(inward=inward).aggregate(total=Sum("quantity")).get("total")
                or Decimal("0")
            )
            max_editable_qty = (item.quantity or Decimal("0")) - other_inward_qty
            if max_editable_qty < 0:
                max_editable_qty = Decimal("0")

            if qty > max_editable_qty:
                item_errors[item.id] = f"Maximum allowed quantity is {max_editable_qty}."
                continue

            line_payload.append((item, qty, remark))

        if not line_payload:
            inward_form.add_error(None, "Enter at least one inward quantity.")

        if not inward_form.errors and not item_errors:
            inward = inward_form.save(commit=False)
            inward.owner = po.owner
            inward.po = po
            inward.save()

            inward.items.all().delete()

            YarnPOInwardItem.objects.bulk_create([
                YarnPOInwardItem(
                    inward=inward,
                    po_item=item,
                    quantity=qty,
                    remark=remark,
                )
                for item, qty, remark in line_payload
            ])

            messages.success(request, f"Inward {inward.inward_number} updated successfully.")
            tracker_url = reverse("accounts:yarn_inward_tracker")
            return redirect(f"{tracker_url}?inward={inward.pk}")

    line_rows = _build_yarn_inward_line_rows(po, line_inputs=line_inputs, item_errors=item_errors)

    return render(
        request,
        "accounts/yarn_po/inward.html",
        {
            "po": po,
            "inward_form": inward_form,
            "item_errors": item_errors,
            "line_inputs": line_inputs,
            "line_rows": line_rows,
            "existing_inwards": po.inwards.all().order_by("-inward_date", "-id"),
            "next_inward_number_preview": inward.inward_number,
            "has_remaining_qty": True,
            "editing_inward": inward,
        },
    )

@login_required
def yarn_inward_tracker(request):
    q = (request.GET.get("q") or "").strip()
    target_inward_id = (request.GET.get("inward") or "").strip()

    qs = (
        YarnPurchaseOrder.objects
        .select_related("vendor", "firm", "owner")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=YarnPurchaseOrderItem.objects.select_related("material", "material_type").prefetch_related("inward_items"),
            ),
            Prefetch(
                "inwards",
                queryset=YarnPOInward.objects.select_related("vendor").prefetch_related(
                    "items__po_item__material",
                    "items__po_item__material_type",
                    "generated_greige_pos__items",
                ),
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

        inward_entries = []
        greige_generated_count = 0

        for inward in po.inwards.all():
            linked_greige_po = inward.generated_greige_pos.order_by("-id").first()
            if linked_greige_po:
                greige_generated_count += 1

            inward_items = []
            for inward_item in inward.items.all():
                po_item = inward_item.po_item
                inward_items.append({
                    "inward_item": inward_item,
                    "po_item": po_item,
                    "fabric_name": (
                        po_item.material.name if po_item and po_item.material
                        else (po_item.material_type.name if po_item and po_item.material_type else "Yarn Item")
                    ),
                    "ordered_qty": po_item.quantity if po_item else 0,
                    "inward_qty": inward_item.quantity,
                    "unit": po_item.unit if po_item else "",
                })

            inward_entries.append({
                "inward": inward,
                "items": inward_items,
                "is_target": str(inward.id) == target_inward_id,
                "greige_po": linked_greige_po,
                "greige_started": bool(linked_greige_po),
                "greige_items_count": linked_greige_po.items.count() if linked_greige_po else 0,
            })

        rows.append({
            "po": po,
            "inward_entries": inward_entries,
            "greige_generated_count": greige_generated_count,
            "total_inwards": len(inward_entries),
        })

    return render(
        request,
        "accounts/yarn_po/inward_tracker.html",
        {
            "rows": rows,
            "q": q,
            "target_inward_id": target_inward_id,
        },
    )


@login_required
@require_POST
def generate_greige_po_from_yarn(request, pk: int):
    yarn_po = get_object_or_404(
        YarnPurchaseOrder.objects.select_related("owner"),
        pk=pk,
    )

    if not _can_access_yarn_po(request.user, yarn_po):
        raise PermissionDenied("You do not have access to this Yarn PO.")

    inward_id = (request.POST.get("inward_id") or "").strip()
    if not inward_id:
        return redirect("accounts:yarn_inward_tracker")

    yarn_inward = get_object_or_404(
        YarnPOInward.objects.select_related("po"),
        pk=inward_id,
        po=yarn_po,
    )

    return redirect(
        f"{reverse('accounts:greigepo_add_from_yarn', kwargs={'yarn_po_id': pk})}?inward={yarn_inward.pk}"
    )


@login_required
@require_POST
def generate_greige_po_from_yarn(request, pk: int):
    yarn_po = get_object_or_404(
        YarnPurchaseOrder.objects.select_related("owner"),
        pk=pk,
    )

    if not _can_access_yarn_po(request.user, yarn_po):
        raise PermissionDenied("You do not have access to this Yarn PO.")

    inward_id = (request.POST.get("inward_id") or "").strip()
    if not inward_id:
        return redirect("accounts:yarn_inward_tracker")

    yarn_inward = get_object_or_404(
        YarnPOInward.objects.select_related("po"),
        pk=inward_id,
        po=yarn_po,
    )

    return redirect(
        f"{reverse('accounts:greigepo_add_from_yarn', kwargs={'yarn_po_id': pk})}?inward={yarn_inward.pk}"
    )


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

    embed_mode = _is_embed(request)
    can_review = _can_review_yarn_po(request.user)

    review_form = YarnPOReviewForm(request.POST or None)

    review_checks = {
        "has_header": bool(po.vendor_id and po.po_date),
        "has_firm": bool(po.firm_id),
        "has_items": po.items.exists(),
        "has_shipping": bool((po.shipping_address or "").strip()),
    }
    review_ready_count = sum(1 for value in review_checks.values() if value)

    context = {
        "po": po,
        "review_form": review_form,
        "can_review_yarn_po": can_review,
        "embed_mode": embed_mode,
        "review_checks": review_checks,
        "review_ready_count": review_ready_count,
    }

    if request.method == "POST":
        if not can_review:
            return HttpResponseForbidden("You are not allowed to review this PO.")

        if review_form.is_valid():
            decision = review_form.cleaned_data["decision"]

            if decision == "approve":
                po.approval_status = "approved"
                po.rejection_reason = ""
            else:
                po.approval_status = "rejected"
                po.rejection_reason = review_form.cleaned_data["rejection_reason"].strip()

            po.reviewed_by = request.user
            po.reviewed_at = timezone.now()
            po.save(update_fields=[
                "approval_status",
                "rejection_reason",
                "reviewed_by",
                "reviewed_at",
            ])

            if embed_mode:
                return JsonResponse({
                    "ok": True,
                    "message": "Yarn PO reviewed successfully.",
                    "redirect_url": reverse("accounts:yarnpo_list"),
                })

            return redirect("accounts:yarnpo_list")

        if embed_mode:
            return render(
                request,
                "accounts/yarn_po/review_embed.html",
                context,
                status=400,
            )

    template_name = (
        "accounts/yarn_po/review_embed.html"
        if embed_mode
        else "accounts/yarn_po/review.html"
    )

    return render(request, template_name, context)

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
        .select_related("vendor", "source_yarn_po", "source_yarn_inward", "owner")
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
def _selected_greige_inward_total(source_greige_inward):
    if source_greige_inward is None:
        return Decimal("0")
    return source_greige_inward.items.aggregate(total=Sum("quantity")).get("total") or Decimal("0") 


def _dyeing_po_queryset():
    return (
        DyeingPurchaseOrder.objects
        .select_related("vendor", "firm", "source_greige_po", "source_greige_inward", "owner")
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
def _selected_yarn_inward_total(source_yarn_inward):
    if source_yarn_inward is None:
        return Decimal("0")
    return source_yarn_inward.items.aggregate(total=Sum("quantity")).get("total") or Decimal("0")

def _sync_greige_po_items_from_source(greige_po, source_inward=None):
    yarn_po = (
        _greige_source_queryset()
        .filter(pk=greige_po.source_yarn_po_id)
        .first()
    )
    if yarn_po is None:
        return Decimal("0")

    item_rows = []
    total_weight = Decimal("0")

    if source_inward is not None:
        inward_items = source_inward.items.select_related("po_item__material", "po_item__material_type")
        for inward_item in inward_items:
            yarn_item = inward_item.po_item
            inward_qty = inward_item.quantity or Decimal("0")
            if yarn_item is None or inward_qty <= 0:
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
                    remark=f"Generated from Yarn inward {source_inward.inward_number}",
                )
            )
            total_weight += inward_qty
    else:
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

    update_fields = ["updated_at"]

    if hasattr(greige_po, "available_qty"):
        greige_po.available_qty = total_weight
        update_fields.append("available_qty")

    if hasattr(greige_po, "total_weight"):
        greige_po.total_weight = total_weight
        update_fields.append("total_weight")

    greige_po.save(update_fields=update_fields)
    return total_weight



def _selected_yarn_inward_total(source_yarn_inward):
    if source_yarn_inward is None:
        return Decimal("0")
    return source_yarn_inward.items.aggregate(total=Sum("quantity")).get("total") or Decimal("0")


def _build_greige_material_rows(source_yarn_inward, owner, submitted_data=None, existing_po=None, row_errors=None):
    greige_qs = Material.objects.filter(material_kind="greige")
    if owner is not None and hasattr(Material, "owner"):
        greige_qs = greige_qs.filter(owner=owner)

    greige_material_options = list(
        greige_qs.select_related("material_type").order_by("name")
    )

    unit_options = list(
        MaterialUnit.objects.filter(owner=owner).order_by("name")
    ) if owner else list(MaterialUnit.objects.order_by("name"))

    material_name_to_id = {m.name: str(m.id) for m in greige_material_options}
    unit_name_to_id = {u.name: str(u.id) for u in unit_options}

    existing_by_po_item = {}
    if existing_po is not None:
        for item in existing_po.items.all():
            if item.source_yarn_po_item_id:
                existing_by_po_item[item.source_yarn_po_item_id] = item

    row_errors = row_errors or {}
    rows = []
    if source_yarn_inward is None:
        return rows, greige_material_options, unit_options

    for inward_item in source_yarn_inward.items.all():
        po_item = inward_item.po_item
        if po_item is None:
            continue

        source_name = (
            po_item.material_type.name
            if po_item.material_type
            else (po_item.material.name if po_item.material else "Yarn Item")
        )

        existing_item = existing_by_po_item.get(po_item.id)

        selected_material_id = ""
        selected_unit_id = ""

        if submitted_data is not None:
            selected_material_id = (submitted_data.get(f"greige_material_{inward_item.id}") or "").strip()
            selected_unit_id = (submitted_data.get(f"greige_unit_{inward_item.id}") or "").strip()
        elif existing_item is not None:
            selected_material_id = material_name_to_id.get(existing_item.fabric_name, "")
            selected_unit_id = unit_name_to_id.get(existing_item.unit, "")
        else:
            selected_unit_id = unit_name_to_id.get(po_item.unit or "", "")

        rows.append({
            "inward_item_id": inward_item.id,
            "po_item_id": po_item.id,
            "source_name": source_name,
            "source_unit": po_item.unit or "",
            "quantity": inward_item.quantity,
            "selected_material_id": selected_material_id,
            "selected_unit_id": selected_unit_id,
            "error": row_errors.get(inward_item.id, ""),
        })

    return rows, greige_material_options, unit_options


def _extract_greige_material_selection(request, source_yarn_inward, owner):
    greige_qs = Material.objects.filter(material_kind="greige")
    if owner is not None and hasattr(Material, "owner"):
        greige_qs = greige_qs.filter(owner=owner)

    unit_qs = MaterialUnit.objects.filter(owner=owner) if owner else MaterialUnit.objects.all()

    greige_material_map = {}
    greige_unit_map = {}
    row_errors = {}

    if source_yarn_inward is None:
        return greige_material_map, greige_unit_map, row_errors

    for inward_item in source_yarn_inward.items.all():
        po_item = inward_item.po_item
        if po_item is None:
            continue

        raw_material_id = (request.POST.get(f"greige_material_{inward_item.id}") or "").strip()
        raw_unit_id = (request.POST.get(f"greige_unit_{inward_item.id}") or "").strip()

        if not raw_material_id:
            row_errors[inward_item.id] = "Select greige name."
            continue

        greige_material = greige_qs.filter(pk=raw_material_id).first()
        if greige_material is None:
            row_errors[inward_item.id] = "Select a valid greige name."
            continue

        greige_material_map[po_item.id] = greige_material

        if raw_unit_id:
            unit_obj = unit_qs.filter(pk=raw_unit_id).first()
            if unit_obj is None:
                row_errors[inward_item.id] = "Select a valid unit."
                continue
            greige_unit_map[po_item.id] = unit_obj.name
        else:
            greige_unit_map[po_item.id] = po_item.unit or ""

    return greige_material_map, greige_unit_map, row_errors
    
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
    source_inward = getattr(dyeing_po, "source_greige_inward", None)

    if source_inward is not None:
        inward_items = source_inward.items.select_related("po_item")
        for inward_item in inward_items:
            greige_item = inward_item.po_item
            inward_qty = inward_item.quantity or Decimal("0")
            if greige_item is None or inward_qty <= 0:
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
                    remark=f"Generated from Greige inward {source_inward.inward_number}",
                )
            )
            total_weight += inward_qty
    else:
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
    selected_source_inward = None

    if yarn_po_id is not None:
        source_yarn_po = get_object_or_404(_greige_source_queryset(), pk=yarn_po_id)
        if not _can_access_yarn_po(request.user, source_yarn_po):
            raise PermissionDenied("You do not have access to this Yarn PO.")

    inward_id = (request.POST.get("source_yarn_inward_id") or request.GET.get("inward") or "").strip()
    if source_yarn_po is not None and inward_id:
        selected_source_inward = get_object_or_404(
            source_yarn_po.inwards.prefetch_related("items__po_item__material", "items__po_item__material_type"),
            pk=inward_id,
        )

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

            if selected_source_inward is not None:
                if selected_source_inward.po_id != selected_source.id:
                    form.add_error(None, "Selected Yarn inward does not belong to the chosen Yarn PO.")
                elif selected_source_inward.generated_greige_pos.exists():
                    form.add_error(None, "Greige PO already exists for this Yarn inward.")
                else:
                    greige_po = form.save(commit=False)
                    greige_po.owner = selected_source.owner
                    greige_po.system_number = _next_greige_po_number()
                    greige_po.source_yarn_po = selected_source
                    greige_po.source_yarn_inward = selected_source_inward

                    if not greige_po.shipping_address and selected_source.firm:
                        greige_po.shipping_address = _firm_address(selected_source.firm)

                    greige_po.save()
                    _sync_greige_po_items_from_source(greige_po, source_inward=selected_source_inward)
                    messages.success(request, f"Greige PO {greige_po.system_number} saved successfully.")
                    return redirect("accounts:greigepo_inward", pk=greige_po.pk)
            else:
                if not selected_source.inwards.exists():
                    form.add_error("source_yarn_po", "Selected Yarn PO has no inward entries yet.")
                elif selected_source.greige_pos.filter(source_yarn_inward__isnull=True).exists():
                    form.add_error("source_yarn_po", "Greige PO already exists for this Yarn PO.")
                else:
                    greige_po = form.save(commit=False)
                    greige_po.owner = selected_source.owner
                    greige_po.system_number = _next_greige_po_number()
                    greige_po.source_yarn_po = selected_source

                    if not greige_po.shipping_address and selected_source.firm:
                        greige_po.shipping_address = _firm_address(selected_source.firm)
                    greige_po.save()
                    _sync_greige_po_items_from_source(greige_po)
                    messages.success(request, f"Greige PO {greige_po.system_number} saved successfully.")
                    return redirect("accounts:greigepo_inward", pk=greige_po.pk)
    else:
        initial = {}
        if source_yarn_po is not None:
            initial = {
                "po_number": source_yarn_po.po_number or "",
                "po_date": timezone.localdate(),
                "available_qty": _selected_yarn_inward_total(selected_source_inward) if selected_source_inward else (source_yarn_po.total_inward_qty or Decimal("0")),
                "vendor": source_yarn_po.vendor_id,
                "firm": source_yarn_po.firm_id if source_yarn_po.firm else None,
                "shipping_address": _firm_address(source_yarn_po.firm) if source_yarn_po.firm else "",
                "remarks": (
                    f"Generated from Yarn inward {selected_source_inward.inward_number}"
                    if selected_source_inward else
                    f"Generated from Yarn PO {source_yarn_po.system_number}"
                ),
            }

        form = GreigePurchaseOrderForm(
            initial=initial,
            user=request.user,
            source_yarn_po=source_yarn_po,
            lock_source=bool(source_yarn_po),
        )

    source_inwards = [selected_source_inward] if selected_source_inward else (list(source_yarn_po.inwards.all()) if source_yarn_po else [])
    existing_po = selected_source_inward.generated_greige_pos.order_by("-id").first() if selected_source_inward else None

    effective_owner = source_yarn_po.owner if source_yarn_po else request.user

    greige_rows, greige_material_options, unit_options = _build_greige_material_rows(
        selected_source_inward,
        effective_owner,
        submitted_data=request.POST if request.method == "POST" else None,
        existing_po=existing_po,
    )

    terms_condition_options = _greige_terms_condition_options(effective_owner)

    selected_terms_condition_id = (request.POST.get("terms_condition_id") or "").strip() if request.method == "POST" else ""
    greige_description = (request.POST.get("greige_description") or "").strip() if request.method == "POST" else ""
    greige_total_weight = (request.POST.get("greige_total_weight") or form.initial.get("available_qty") or form["available_qty"].value() or "0.00")
    greige_subtotal = (request.POST.get("greige_subtotal") or "0.00")
    greige_discount_percent = (request.POST.get("greige_discount_percent") or "0")
    greige_after_discount = (request.POST.get("greige_after_discount") or "0.00")
    greige_others = (request.POST.get("greige_others") or "0")
    greige_cgst = (request.POST.get("greige_cgst") or "2.5")
    greige_sgst = (request.POST.get("greige_sgst") or "2.5")
    
    return render(
        request,
        "accounts/greige_po/form.html",
        {
            "form": form,
            "mode": "add",
            "po_obj": None,
            "system_number_preview": _next_greige_po_number(),
            "source_yarn_po": source_yarn_po,
            "selected_source_inward": selected_source_inward,
            "source_inwards": source_inwards,
            "existing_po": existing_po,
            "greige_rows": greige_rows,
            "greige_material_options": greige_material_options,
            "unit_options": unit_options,
            "terms_condition_options": terms_condition_options,
            "selected_terms_condition_id": selected_terms_condition_id,
            "greige_description": greige_description,
            "greige_total_weight": greige_total_weight,
            "greige_subtotal": greige_subtotal,
            "greige_discount_percent": greige_discount_percent,
            "greige_after_discount": greige_after_discount,
            "greige_others": greige_others,
            "greige_cgst": greige_cgst,
            "greige_sgst": greige_sgst,
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
        if not po.shipping_address and po.source_yarn_po and po.source_yarn_po.firm:
            po.shipping_address = _firm_address(po.source_yarn_po.firm)
        po.save()
        messages.success(request, f"Greige PO {po.system_number} updated successfully.")
        return redirect("accounts:greigepo_inward", pk=po.pk)

    source_inwards = [po.source_yarn_inward] if po.source_yarn_inward else (list(po.source_yarn_po.inwards.all()) if po.source_yarn_po else [])
    effective_owner = po.owner

    greige_rows, greige_material_options, unit_options = _build_greige_material_rows(
        po.source_yarn_inward,
        effective_owner,
        submitted_data=request.POST if request.method == "POST" else None,
        existing_po=po,
    )

    terms_condition_options = _greige_terms_condition_options(effective_owner)

    selected_terms_condition_id = (request.POST.get("terms_condition_id") or "").strip()
    greige_description = (request.POST.get("greige_description") or "").strip()
    greige_total_weight = (request.POST.get("greige_total_weight") or po.available_qty or "0.00")
    greige_subtotal = (request.POST.get("greige_subtotal") or "0.00")
    greige_discount_percent = (request.POST.get("greige_discount_percent") or "0")
    greige_after_discount = (request.POST.get("greige_after_discount") or "0.00")
    greige_others = (request.POST.get("greige_others") or "0")
    greige_cgst = (request.POST.get("greige_cgst") or "2.5")
    greige_sgst = (request.POST.get("greige_sgst") or "2.5")
    
    return render(
        request,
        "accounts/greige_po/form.html",
        {
            "form": form,
            "mode": "edit",
            "po_obj": po,
            "system_number_preview": po.system_number,
            "source_yarn_po": po.source_yarn_po,
            "selected_source_inward": po.source_yarn_inward,
            "source_inwards": source_inwards,
            "existing_po": None,
            "greige_rows": greige_rows,
            "greige_material_options": greige_material_options,
            "unit_options": unit_options,
            "terms_condition_options": terms_condition_options,
            "selected_terms_condition_id": selected_terms_condition_id,
            "greige_description": greige_description,
            "greige_total_weight": greige_total_weight,
            "greige_subtotal": greige_subtotal,
            "greige_discount_percent": greige_discount_percent,
            "greige_after_discount": greige_after_discount,
            "greige_others": greige_others,
            "greige_cgst": greige_cgst,
            "greige_sgst": greige_sgst,
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
    if not _is_po_approved_for_inward(po):
        messages.error(request, "Greige PO must be approved before inward can be generated.")
        return redirect("accounts:greigepo_list")

    item_errors = {}
    line_inputs = {}
    inward_form = GreigePOInwardForm(request.POST or None, user=request.user)

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

            tracker_url = reverse("accounts:greige_inward_tracker")
            return redirect(f"{tracker_url}?inward={inward.pk}")

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
    target_inward_id = (request.GET.get("inward") or "").strip()

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
        inward_entries = []
        dyeing_generated_count = 0

        for inward in po.inwards.all():
            linked_dyeing_po = inward.generated_dyeing_pos.order_by("-id").first()
            if linked_dyeing_po:
                dyeing_generated_count += 1

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
                "is_target": str(inward.id) == target_inward_id,
                "dyeing_po": linked_dyeing_po,
                "dyeing_started": bool(linked_dyeing_po),
                "dyeing_items_count": linked_dyeing_po.items.count() if linked_dyeing_po else 0,
            })

        rows.append({
            "po": po,
            "inward_entries": inward_entries,
            "dyeing_generated_count": dyeing_generated_count,
            "total_inwards": len(inward_entries),
        })

    return render(
        request,
        "accounts/greige_po/inward_tracker.html",
        {
            "rows": rows,
            "q": q,
            "target_inward_id": target_inward_id,
        },
    )


@login_required
@require_POST
def generate_dyeing_po_from_greige(request, pk: int):
    greige_po = get_object_or_404(_greige_po_queryset(), pk=pk)
    if not _can_access_greige_po(request.user, greige_po):
        raise PermissionDenied("You do not have access to this Greige PO.")

    inward_id = (request.POST.get("inward_id") or "").strip()
    if not inward_id:
        return redirect("accounts:greige_inward_tracker")

    greige_inward = get_object_or_404(
        GreigePOInward.objects.select_related("po"),
        pk=inward_id,
        po=greige_po,
    )

    return redirect(
        f"{reverse('accounts:dyeingpo_add_from_greige', kwargs={'greige_po_id': pk})}?inward={greige_inward.pk}"
    )

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
    selected_source_inward = None

    if greige_po_id is not None:
        source_greige_po = get_object_or_404(_greige_po_queryset(), pk=greige_po_id)
        if not _can_access_greige_po(request.user, source_greige_po):
            raise PermissionDenied("You do not have access to this Greige PO.")

    inward_id = (request.POST.get("source_greige_inward") or request.GET.get("inward") or "").strip()
    if source_greige_po is not None and inward_id:
        selected_source_inward = get_object_or_404(
            source_greige_po.inwards.prefetch_related("items__po_item"),
            pk=inward_id,
        )

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

            if selected_source_inward is not None:
                if selected_source_inward.po_id != selected_source.id:
                    form.add_error(None, "Selected Greige inward does not belong to the chosen Greige PO.")
                elif selected_source_inward.generated_dyeing_pos.exists():
                    form.add_error(None, "Dyeing PO already exists for this Greige inward.")
                else:
                    dyeing_po = form.save(commit=False)
                    dyeing_po.owner = selected_source.owner
                    dyeing_po.system_number = _next_dyeing_po_number()
                    dyeing_po.source_greige_po = selected_source
                    dyeing_po.source_greige_inward = selected_source_inward
                    if dyeing_po.firm and not dyeing_po.shipping_address:
                        dyeing_po.shipping_address = _firm_address(dyeing_po.firm)
                    dyeing_po.save()
                    _sync_dyeing_po_items_from_source(dyeing_po)
                    return redirect("accounts:dyeingpo_inward", pk=dyeing_po.pk)
            else:
                if not selected_source.inwards.exists():
                    form.add_error("source_greige_po", "Selected Greige PO has no inward entries yet.")
                elif selected_source.dyeing_pos.filter(source_greige_inward__isnull=True).exists():
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
                    return redirect("accounts:dyeingpo_inward", pk=dyeing_po.pk)
    else:
        initial = {}
        if source_greige_po is not None:
            initial = {
                "po_number": source_greige_po.po_number or "",
                "po_date": timezone.localdate(),
                "available_qty": _selected_greige_inward_total(selected_source_inward) if selected_source_inward else (source_greige_po.total_inward_qty or Decimal("0")),
                "vendor": source_greige_po.vendor_id,
                "firm": source_greige_po.firm_id if source_greige_po.firm else None,
                "shipping_address": _firm_address(source_greige_po.firm) if source_greige_po.firm else "",
                "remarks": (
                    f"Generated from Greige inward {selected_source_inward.inward_number}"
                    if selected_source_inward else
                    f"Generated from Greige PO {source_greige_po.system_number}"
                ),
                "source_greige_inward": selected_source_inward.pk if selected_source_inward else None,
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
            "selected_source_inward": selected_source_inward,
            "source_inwards": [selected_source_inward] if selected_source_inward else (list(source_greige_po.inwards.all()) if source_greige_po else []),
            "existing_po": selected_source_inward.generated_dyeing_pos.order_by("-id").first() if selected_source_inward else (source_greige_po.dyeing_pos.order_by("-id").first() if source_greige_po else None),
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
    inward_form = DyeingPOInwardForm(request.POST or None, user=request.user)

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
    inward_form = ReadyPOInwardForm(request.POST or None, user=request.user)

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

def _dyeing_other_charge_list_url(request):
    url = reverse("accounts:dyeing_other_charge_list")
    if _is_embed(request):
        url += "?embed=1"
    return url

def _termscondition_list_url(request):
    url = reverse("accounts:termscondition_list")
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

@login_required
@require_GET
def dyeing_other_charge_list(request):
    q = (request.GET.get("q") or "").strip()

    charges = DyeingOtherCharge.objects.filter(owner=request.user).order_by("name")
    if q:
        charges = charges.filter(name__icontains(q))

    template = (
        "accounts/dyeing_other_charges/list_embed.html"
        if _is_embed(request)
        else "accounts/dyeing_other_charges/list.html"
    )
    return render(
        request,
        template,
        {
            "charges": charges,
            "q": q,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def dyeing_other_charge_create(request):
    form = DyeingOtherChargeForm(request.POST or None, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _dyeing_other_charge_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = (
        "accounts/dyeing_other_charges/form_embed.html"
        if _is_embed(request)
        else "accounts/dyeing_other_charges/form.html"
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
def dyeing_other_charge_edit(request, pk: int):
    charge = get_object_or_404(DyeingOtherCharge, pk=pk, owner=request.user)
    form = DyeingOtherChargeForm(request.POST or None, instance=charge, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _dyeing_other_charge_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = (
        "accounts/dyeing_other_charges/form_embed.html"
        if _is_embed(request)
        else "accounts/dyeing_other_charges/form.html"
    )
    return render(
        request,
        template,
        {
            "form": form,
            "charge": charge,
            "mode": "edit",
        },
    )

@login_required
@require_POST
def dyeing_other_charge_delete(request, pk: int):
    charge = get_object_or_404(DyeingOtherCharge, pk=pk, owner=request.user)
    charge.delete()

    url = _dyeing_other_charge_list_url(request)
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
    files = request.FILES if bind else None

    material_queryset = (
        instance.material_items.filter(item_type=BOMMaterialItem.ItemType.RAW_FABRIC).order_by("sort_order", "id")
        if instance else BOMMaterialItem.objects.none()
    )
    accessory_queryset = (
        instance.material_items.filter(item_type=BOMMaterialItem.ItemType.ACCESSORY).order_by("sort_order", "id")
        if instance else BOMMaterialItem.objects.none()
    )
    image_queryset = (
        instance.images.order_by("sort_order", "id")
        if instance else BOMImage.objects.none()
    )

    materials_formset = BOMMaterialItemFormSet(
        data=data,
        instance=instance,
        prefix="materials",
        queryset=material_queryset,
        form_kwargs={
            "user": request.user,
            "forced_item_type": BOMMaterialItem.ItemType.RAW_FABRIC,
        },
    )

    accessories_formset = BOMMaterialItemFormSet(
        data=data,
        instance=instance,
        prefix="accessories",
        queryset=accessory_queryset,
        form_kwargs={
            "user": request.user,
            "forced_item_type": BOMMaterialItem.ItemType.ACCESSORY,
        },
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
        form_kwargs={"user": request.user},
    )

    image_formset = BOMImageFormSet(
        data=data,
        files=files,
        instance=instance,
        prefix="images",
        queryset=image_queryset,
    )

    return materials_formset, accessories_formset, jobber_formset, process_formset, expense_formset, image_formset


def _save_bom_material_formset(formset, bom, forced_item_type):
    objects = formset.save(commit=False)

    for obj in formset.deleted_objects:
        obj.delete()

    for index, obj in enumerate(objects, start=1):
        obj.bom = bom
        obj.item_type = forced_item_type
        obj.sort_order = index
        obj.save()

def _save_simple_formset(formset):
    objects = formset.save(commit=False)

    for obj in formset.deleted_objects:
        obj.delete()

    for index, obj in enumerate(objects, start=1):
        if hasattr(obj, "sort_order"):
            obj.sort_order = index
        obj.save()


def _save_bom_image_formset(formset, bom):
    objects = formset.save(commit=False)

    for obj in formset.deleted_objects:
        obj.delete()

    for index, obj in enumerate(objects, start=1):
        obj.bom = bom
        obj.sort_order = index
        obj.save()

    formset.save_m2m()


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
            "images",
        )
        .order_by("-id")
    )

    if q:
        qs = qs.filter(
            Q(bom_code__icontains=q)
            | Q(sku_code__icontains=q)
            | Q(product_name__icontains=q)
            | Q(catalogue_name__icontains=q)
            | Q(catalogue__name__icontains=q)
            | Q(sub_category__icontains=q)
            | Q(sub_category_master__name__icontains=q)
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
    materials_formset, accessories_formset, jobber_formset, process_formset, expense_formset, image_formset = _build_bom_formsets(request)

    if request.method == "POST":
        is_valid = (
            form.is_valid()
            and materials_formset.is_valid()
            and accessories_formset.is_valid()
            and jobber_formset.is_valid()
            and process_formset.is_valid()
            and expense_formset.is_valid()
            and image_formset.is_valid()
        )

        if is_valid and not _bom_has_at_least_one_material(materials_formset):
            materials_formset._non_form_errors = materials_formset.error_class(
                ["Add at least one material row."]
            )
            is_valid = False

        if is_valid:
            with transaction.atomic():
                bom = form.save(commit=False)
                bom.owner = request.user
                bom.save()

                materials_formset.instance = bom
                accessories_formset.instance = bom
                jobber_formset.instance = bom
                process_formset.instance = bom
                expense_formset.instance = bom
                image_formset.instance = bom

                _save_bom_material_formset(
                    materials_formset,
                    bom,
                    BOMMaterialItem.ItemType.RAW_FABRIC,
                )
                _save_bom_material_formset(
                    accessories_formset,
                    bom,
                    BOMMaterialItem.ItemType.ACCESSORY,
                )
                _save_simple_formset(jobber_formset)
                _save_simple_formset(process_formset)
                _save_simple_formset(expense_formset)
                _save_bom_image_formset(image_formset, bom)

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
            "materials_formset": materials_formset,
            "accessories_formset": accessories_formset,
            "jobber_formset": jobber_formset,
            "process_formset": process_formset,
            "expense_formset": expense_formset,
            "image_formset": image_formset,
            "mode": "add",
        },
    )


def _greige_terms_condition_options(owner):

    qs = TermsCondition.objects.all()
    if owner is not None:
        qs = qs.filter(owner=owner)
    return qs.order_by("title")
@login_required
@require_http_methods(["GET", "POST"])
def bom_update(request, pk: int):
    bom = get_object_or_404(BOM, pk=pk, owner=request.user)
    form = BOMForm(request.POST or None, request.FILES or None, instance=bom, user=request.user)
    materials_formset, accessories_formset, jobber_formset, process_formset, expense_formset, image_formset = _build_bom_formsets(
        request,
        instance=bom,
    )

    if request.method == "POST":
        is_valid = (
            form.is_valid()
            and materials_formset.is_valid()
            and accessories_formset.is_valid()
            and jobber_formset.is_valid()
            and process_formset.is_valid()
            and expense_formset.is_valid()
            and image_formset.is_valid()
        )

        if is_valid and not _bom_has_at_least_one_material(materials_formset):
            materials_formset._non_form_errors = materials_formset.error_class(
                ["Add at least one material row."]
            )
            is_valid = False

        if is_valid:
            with transaction.atomic():
                bom = form.save()

                materials_formset.instance = bom
                accessories_formset.instance = bom
                jobber_formset.instance = bom
                process_formset.instance = bom
                expense_formset.instance = bom
                image_formset.instance = bom

                _save_bom_material_formset(
                    materials_formset,
                    bom,
                    BOMMaterialItem.ItemType.RAW_FABRIC,
                )
                _save_bom_material_formset(
                    accessories_formset,
                    bom,
                    BOMMaterialItem.ItemType.ACCESSORY,
                )
                _save_simple_formset(jobber_formset)
                _save_simple_formset(process_formset)
                _save_simple_formset(expense_formset)
                _save_bom_image_formset(image_formset, bom)

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
            "materials_formset": materials_formset,
            "accessories_formset": accessories_formset,
            "jobber_formset": jobber_formset,
            "process_formset": process_formset,
            "expense_formset": expense_formset,
            "image_formset": image_formset,
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
        "sub_category_name": bom.display_sub_category_name,
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



@login_required
@require_http_methods(["GET"])
def termscondition_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = TermsCondition.objects.filter(owner=request.user).order_by("title")

    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(content__icontains=q)
        )

    ctx = {
        "terms_conditions": qs,
        "q": q,
    }

    tpl = (
        "accounts/terms_conditions/list_embed.html"
        if _is_embed(request)
        else "accounts/terms_conditions/list.html"
    )
    return render(request, tpl, ctx)


@login_required
@require_http_methods(["GET", "POST"])
def termscondition_create(request):
    form = TermsConditionForm(request.POST or None, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.is_active = True
        obj.save()

        url = _termscondition_list_url(request)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "url": url})

        return redirect(url)

    tpl = (
        "accounts/terms_conditions/form_embed.html"
        if _is_embed(request)
        else "accounts/terms_conditions/form.html"
    )
    return render(request, tpl, {"form": form, "mode": "add"})


@login_required
@require_http_methods(["GET", "POST"])
def termscondition_update(request, pk: int):
    terms_condition = get_object_or_404(TermsCondition, pk=pk, owner=request.user)
    form = TermsConditionForm(request.POST or None, instance=terms_condition, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.is_active = True
        obj.save()

        url = _termscondition_list_url(request)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "url": url})

        return redirect(url)

    tpl = (
        "accounts/terms_conditions/edit_embed.html"
        if _is_embed(request)
        else "accounts/terms_conditions/edit.html"
    )
    return render(
        request,
        tpl,
        {
            "form": form,
            "mode": "edit",
            "terms_condition": terms_condition,
        },
    )


@login_required
@require_POST
def termscondition_delete(request, pk: int):
    terms_condition = get_object_or_404(TermsCondition, pk=pk, owner=request.user)
    terms_condition.delete()

    url = _termscondition_list_url(request)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "url": url})

    return redirect(url)


def _inwardtype_list_url(request):
    url = reverse("accounts:inwardtype_list")
    if _is_embed(request):
        url += "?embed=1"
    return url

@login_required
@require_GET
def inwardtype_list(request):
    q = (request.GET.get("q") or "").strip()

    inward_types = InwardType.objects.filter(owner=request.user).order_by("name")
    if q:
        inward_types = inward_types.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )

    template = (
        "accounts/inward_types/list_embed.html"
        if _is_embed(request)
        else "accounts/inward_types/list.html"
    )
    return render(
        request,
        template,
        {
            "inward_types": inward_types,
            "q": q,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def inwardtype_create(request):
    form = InwardTypeForm(request.POST or None, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _inwardtype_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = (
        "accounts/inward_types/form_embed.html"
        if _is_embed(request)
        else "accounts/inward_types/form.html"
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
def inwardtype_edit(request, pk: int):
    inward_type = get_object_or_404(InwardType, pk=pk, owner=request.user)
    form = InwardTypeForm(request.POST or None, instance=inward_type, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _inwardtype_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = (
        "accounts/inward_types/form_embed.html"
        if _is_embed(request)
        else "accounts/inward_types/form.html"
    )
    return render(
        request,
        template,
        {
            "form": form,
            "inward_type": inward_type,
            "mode": "edit",
        },
    )


@login_required
@require_POST
def inwardtype_delete(request, pk: int):
    inward_type = get_object_or_404(InwardType, pk=pk, owner=request.user)
    inward_type.delete()

    url = _inwardtype_list_url(request)
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)


def _subcategory_list_url(request):
    url = reverse("accounts:subcategory_list")
    if _is_embed(request):
        url += "?embed=1"
    return url


@login_required
def subcategory_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = (
        SubCategory.objects.filter(owner=request.user)
        .select_related("main_category")
        .order_by("main_category__name", "name")
    )
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(main_category__name__icontains=q)
        )

    template = (
        "accounts/sub_categories/list_embed.html"
        if _is_embed(request)
        else "accounts/sub_categories/list.html"
    )
    return render(
        request,
        template,
        {
            "sub_categories": qs,
            "q": q,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def subcategory_create(request):
    form = SubCategoryForm(request.POST or None, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _subcategory_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = (
        "accounts/sub_categories/form_embed.html"
        if _is_embed(request)
        else "accounts/sub_categories/form.html"
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
def subcategory_edit(request, pk: int):
    sub_category = get_object_or_404(SubCategory, pk=pk, owner=request.user)
    form = SubCategoryForm(request.POST or None, instance=sub_category, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _subcategory_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = (
        "accounts/sub_categories/form_embed.html"
        if _is_embed(request)
        else "accounts/sub_categories/form.html"
    )
    return render(
        request,
        template,
        {
            "form": form,
            "mode": "edit",
            "sub_category": sub_category,
        },
    )


@login_required
@require_POST
def subcategory_delete(request, pk: int):
    sub_category = get_object_or_404(SubCategory, pk=pk, owner=request.user)
    sub_category.delete()

    url = _subcategory_list_url(request)
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)

def _is_po_approved_for_inward(po) -> bool:
    current_status = str(getattr(po, "approval_status", "") or "").strip().lower()
    if current_status:
        return current_status == "approved"

    source_yarn_po = getattr(po, "source_yarn_po", None)
    source_status = str(getattr(source_yarn_po, "approval_status", "") or "").strip().lower()
    if source_status:
        return source_status == "approved"

    return True

@login_required
@require_http_methods(["GET", "POST"])
def greigepo_review(request, pk: int):
    po = get_object_or_404(
        _greige_po_queryset(),
        pk=pk,
    )

    if not _can_access_greige_po(request.user, po):
        raise PermissionDenied("You do not have access to this Greige PO.")

    embed_mode = _is_embed(request)
    can_review = _can_review_yarn_po(request.user)

    review_form = GreigePOReviewForm(request.POST or None)

    review_checks = {
        "has_header": bool(po.vendor_id and po.po_date),
        "has_source": bool(po.source_yarn_po_id),
        "has_items": po.items.exists(),
        "has_shipping": bool((po.shipping_address or "").strip()),
    }
    review_ready_count = sum(1 for value in review_checks.values() if value)

    context = {
        "po": po,
        "review_form": review_form,
        "can_review_greige_po": can_review,
        "embed_mode": embed_mode,
        "review_checks": review_checks,
        "review_ready_count": review_ready_count,
    }

    if request.method == "POST":
        if not can_review:
            return HttpResponseForbidden("You are not allowed to review this PO.")

        if review_form.is_valid():
            decision = review_form.cleaned_data["decision"]

            if decision == "approve":
                po.approval_status = "approved"
                po.rejection_reason = ""
            else:
                po.approval_status = "rejected"
                po.rejection_reason = review_form.cleaned_data["rejection_reason"].strip()

            po.reviewed_by = request.user
            po.reviewed_at = timezone.now()
            po.save(update_fields=[
                "approval_status",
                "rejection_reason",
                "reviewed_by",
                "reviewed_at",
            ])

            if embed_mode:
                return JsonResponse({
                    "ok": True,
                    "message": "Greige PO reviewed successfully.",
                    "redirect_url": reverse("accounts:greigepo_list"),
                })

            return redirect("accounts:greigepo_list")

        if embed_mode:
            return render(
                request,
                "accounts/greige_po/review_embed.html",
                context,
                status=400,
            )

    template_name = (
        "accounts/greige_po/review_embed.html"
        if embed_mode
        else "accounts/greige_po/review.html"
    )

    return render(request, template_name, context)