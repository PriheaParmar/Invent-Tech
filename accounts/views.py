from calendar import monthcalendar
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
import logging
from zoneinfo import ZoneInfo

from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Count, Prefetch, Q, Sum
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .forms import (
    AccessoryForm,
    BOMAccessoryItemFormSet,
    BOMForm,
    BOMImageFormSet,
    BOMMaterialItemFormSet,
    BOMJobberTypeProcessFormSet,
    BOMJobberDetailFormSet,
    BOMExpenseItemFormSet,
    BrandForm,
    CatalogueForm,
    CategoryForm,
    ClientForm,
    DashboardProfileForm,
    DyeingMaterialLinkDetailFormSet,
    DyeingMaterialLinkForm,
    DyeingOtherChargeForm,
    DyeingPOInwardForm,
    DyeingPurchaseOrderForm,
    DyeingPurchaseOrderItemFormSet,
    ExpenseForm,
    FirmForm,
    GreigePOInwardForm,
    GreigePurchaseOrderItemFormSet,
    GreigePOReviewForm,
    GreigePurchaseOrderForm,
    InwardTypeForm,
    JobberForm,
    JobberTypeForm,
    LocationForm,
    MainCategoryForm,
    MaterialForm,
    MaterialShadeForm,
    MaterialSubTypeForm,
    MaterialTypeForm,
    MaterialUnitForm,
    PartyForm,
    PatternTypeForm,
    ProgramForm,
    ProgramJobberDetailFormSet,
    ReadyPOInwardForm,
    ReadyPurchaseOrderForm,
    SubCategoryForm,
    TermsConditionForm,
    VendorForm,
    YarnPOInwardForm,
    YarnPOReviewForm,
    YarnPurchaseOrderForm,
    YarnPurchaseOrderItemFormSet,
)

DyeingPOReviewForm = GreigePOReviewForm

try:
    from .forms import DispatchChallanForm
except ImportError:
    class DispatchChallanForm(forms.Form):
        pass

from .models import (
    Accessory,
    BOM,
    BOMAccessoryItem,
    BOMImage,
    BOMJobberTypeProcess,
    BOMMaterialItem,
    Program,
    ProgramSizeDetail,
    ProgramJobberDetail,
    Brand,
    Catalogue,
    Category,
    Client,
    DyeingMaterialLink,
    DyeingMaterialLinkDetail,
    DyeingOtherCharge,
    DyeingPOInward,
    DyeingPOInwardItem,
    DyeingPurchaseOrder,
    DyeingPurchaseOrderItem,
    Expense,
    Firm,
    GreigePOInward,
    GreigePOInwardItem,
    GreigePurchaseOrder,
    GreigePurchaseOrderItem,
    InwardType,
    Jobber,
    JobberType,
    Location,
    MainCategory,
    Material,
    MaterialShade,
    MaterialSubType,
    MaterialType,
    MaterialUnit,
    Party,
    PatternType,
    ReadyPOInward,
    ReadyPOInwardItem,
    ReadyPurchaseOrder,
    ReadyPurchaseOrderItem,
    SubCategory,
    TermsCondition,
    UserExtra,
    Vendor,
    YarnPOInward,
    YarnPOInwardItem,
    YarnPurchaseOrder,
    YarnPurchaseOrderItem,
)
from .navigation import UTILITIES_GROUPS

try:
    from .models import DispatchChallan
except ImportError:
    DispatchChallan = None


logger = logging.getLogger(__name__)


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


def _template_exists(template_name: str) -> bool:
    try:
        get_template(template_name)
        return True
    except TemplateDoesNotExist:
        return False


def _pick_template(*template_names: str) -> str:
    for template_name in template_names:
        if template_name and _template_exists(template_name):
            return template_name
    return template_names[-1]


def _model_has_fields(model, *field_names: str) -> bool:
    try:
        existing_fields = {field.name for field in model._meta.get_fields()}
    except Exception:
        return False
    return all(field_name in existing_fields for field_name in field_names)


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

    today_local = now_local.date()

    yarn_inward_count = YarnPOInward.objects.filter(owner=request.user).count()
    greige_inward_count = GreigePOInward.objects.filter(owner=request.user).count()
    dyeing_inward_count = DyeingPOInward.objects.filter(owner=request.user).count()
    ready_inward_count = ReadyPOInward.objects.filter(owner=request.user).count()

    fabric_inward_count = greige_inward_count + dyeing_inward_count + ready_inward_count
    total_inward_count = yarn_inward_count + greige_inward_count + dyeing_inward_count + ready_inward_count

    today_inward_count = (
        YarnPOInward.objects.filter(owner=request.user, inward_date=today_local).count()
        + GreigePOInward.objects.filter(owner=request.user, inward_date=today_local).count()
        + DyeingPOInward.objects.filter(owner=request.user, inward_date=today_local).count()
        + ReadyPOInward.objects.filter(owner=request.user, inward_date=today_local).count()
    )

    return render(
        request,
        "accounts/dashboard.html",
        {
            "greeting": greeting,
            "current_month_label": now_local.strftime("%B %Y"),
            "current_date_label": now_local.strftime("%d %b %Y"),
            "current_time_label": now_local.strftime("%I:%M %p"),
            "calendar_weeks": calendar_weeks,

            "total_inward_count": total_inward_count,
            "today_inward_count": today_inward_count,
            "fabric_inward_count": fabric_inward_count,
            "yarn_inward_count": yarn_inward_count,
            "greige_inward_count": greige_inward_count,
            "dyeing_inward_count": dyeing_inward_count,
            "ready_inward_count": ready_inward_count,
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

    template = _pick_template(
        "accounts/jobbers/embed_types.html" if _is_embed(request) else "accounts/jobbers/types.html",
        "accounts/jobbers/embed_types.html",
    )
    return render(request, template, context)


# ==========================
# MATERIALS (embed supported)
# ==========================
@login_required
def material_kind_picker(request):
    ctx = {
        "kind_choices": Material.MATERIAL_KIND_CHOICES,
    }
    tpl = _pick_template(
        "accounts/materials/kind_picker_embed.html" if _is_embed(request) else "accounts/materials/kind_picker_page.html",
        "accounts/materials/kind_picker_embed.html",
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

    tpl = _pick_template(
        "accounts/firms/list_embed.html" if _is_embed(request) else "accounts/firms/list.html",
        "accounts/firms/list_embed.html",
    )
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

    template = _pick_template(
        "accounts/firms/form_embed.html" if _is_embed(request) else "accounts/firms/form.html",
        "accounts/firms/form_embed.html",
        "accounts/firms/form.html",
    )
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

def _build_greige_po_pdf_response(po):
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

    firm = getattr(po.source_yarn_po, "firm", None)
    vendor = po.vendor
    po_items = list(po.items.all())

    def resolve_logo_path():
        if firm and getattr(firm, "logo", None):
            try:
                logo_path = firm.logo.path
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
        "GPOBase",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=10.5,
        textColor=ink,
        spaceAfter=0,
    )

    header_left_style = ParagraphStyle(
        "GPOHeaderLeft",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8.4,
        leading=10.4,
        textColor=white,
        alignment=TA_LEFT,
    )

    header_title_style = ParagraphStyle(
        "GPOHeaderTitle",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=16,
        textColor=brand_navy,
        alignment=TA_RIGHT,
    )

    header_meta_style = ParagraphStyle(
        "GPOHeaderMeta",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8.3,
        leading=10.2,
        textColor=ink,
        alignment=TA_RIGHT,
    )

    section_head_left = ParagraphStyle(
        "GPOSectionHeadLeft",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=white,
        alignment=TA_LEFT,
    )

    section_value_style = ParagraphStyle(
        "GPOSectionValue",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8.2,
        leading=10.2,
        textColor=ink,
        alignment=TA_LEFT,
    )

    table_head_style = ParagraphStyle(
        "GPOTableHead",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=7.8,
        leading=9.5,
        textColor=white,
        alignment=TA_CENTER,
    )

    item_center_style = ParagraphStyle(
        "GPOItemCenter",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8,
        leading=9.6,
        alignment=TA_CENTER,
    )

    item_desc_style = ParagraphStyle(
        "GPOItemDesc",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8,
        leading=9.6,
        alignment=TA_LEFT,
    )

    money_style = ParagraphStyle(
        "GPOMoney",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8,
        leading=9.6,
        alignment=TA_RIGHT,
    )

    block_title_style = ParagraphStyle(
        "GPOBlockTitle",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=8.4,
        leading=10.5,
        textColor=brand_navy,
        alignment=TA_LEFT,
    )

    block_text_style = ParagraphStyle(
        "GPOBlockText",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8.1,
        leading=10.1,
        textColor=ink,
        alignment=TA_LEFT,
    )

    sign_style = ParagraphStyle(
        "GPOSign",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=ink,
        alignment=TA_LEFT,
    )

    total_label_style = ParagraphStyle(
        "GPOTotalLabel",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=8.2,
        leading=10.2,
        textColor=ink,
        alignment=TA_LEFT,
    )

    total_value_style = ParagraphStyle(
        "GPOTotalValue",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=8.2,
        leading=10.2,
        textColor=ink,
        alignment=TA_RIGHT,
    )

    footer_note_style = ParagraphStyle(
        "GPOFooterNote",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=7.6,
        leading=9.2,
        textColor=muted,
        alignment=TA_CENTER,
    )

    story = []

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

    source_yarn_po_no = text_or_dash(po.source_yarn_po.system_number if po.source_yarn_po else "")
    source_yarn_inward_no = text_or_dash(po.source_yarn_inward.inward_number if po.source_yarn_inward else "")

    header_table = Table(
        [[
            Paragraph(firm_header_html, header_left_style),
            Table(
                [[
                    Paragraph("<b>GREIGE PURCHASE ORDER</b>", header_title_style),
                ], [
                    Paragraph(
                        f"<b>PO No:</b> {escape(order_number)}<br/>"
                        f"<b>PO Date:</b> {escape(po_date)}<br/>"
                        f"<b>System No:</b> {escape(text_or_dash(po.system_number))}<br/>"
                        f"<b>Status:</b> {escape(text_or_dash(approval_label))}<br/>"
                        f"<b>Source Yarn PO:</b> {escape(source_yarn_po_no)}"
                        + (f"<br/><b>Source Inward:</b> {escape(source_yarn_inward_no)}" if source_yarn_inward_no != "-" else "")
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

    total_amount = Decimal("0")
    total_qty = Decimal("0")
    total_inward = Decimal("0")
    remaining_qty = Decimal("0")

    for index, item in enumerate(po_items, start=1):
        label = item.fabric_name or (item.material.name if item.material else "Greige Item")

        details = []
        if item.yarn_name:
            details.append(f"Yarn: {item.yarn_name}")
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

        description_html = f"<b>{escape(text_or_dash(label))}</b>"
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

        total_amount += Decimal(item.final_amount or 0)
        total_qty += Decimal(item.quantity or 0)
        total_inward += Decimal(item.inward_qty_total or 0)
        remaining_qty += Decimal(item.remaining_qty_total or 0)

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
    if po.address:
        notes_parts.append(
            f"<font color='#0F172A'><b>Address</b></font><br/>{escape(po.address).replace(chr(10), '<br/>')}"
        )
    if po.delivery_schedule:
        notes_parts.append(
            f"<font color='#0F172A'><b>Delivery Schedule</b></font><br/>{escape(po.delivery_schedule).replace(chr(10), '<br/>')}"
        )
    if po.shipping_address:
        notes_parts.append(
            f"<font color='#0F172A'><b>Shipping Address</b></font><br/>{escape(po.shipping_address).replace(chr(10), '<br/>')}"
        )
    if po.source_yarn_po:
        notes_parts.append(
            f"<font color='#0F172A'><b>Source Yarn PO</b></font><br/>{escape(text_or_dash(po.source_yarn_po.system_number))}"
        )
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

    totals_rows = [
        [Paragraph("Total Qty", total_label_style), Paragraph(escape(fmt_qty(total_qty)), total_value_style)],
        [Paragraph("Total Inward", total_label_style), Paragraph(escape(fmt_qty(total_inward)), total_value_style)],
        [Paragraph("Remaining Qty", total_label_style), Paragraph(escape(fmt_qty(remaining_qty)), total_value_style)],
        [Paragraph("Total Amount", total_label_style), Paragraph(escape(fmt_money(total_amount)), total_value_style)],
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
    return response


@login_required
def greigepo_pdf(request, pk: int):
    po = get_object_or_404(
        GreigePurchaseOrder.objects
        .select_related("vendor", "source_yarn_po", "source_yarn_po__firm", "owner", "reviewed_by")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=GreigePurchaseOrderItem.objects.select_related("material", "source_yarn_po_item")
            )
        ),
        pk=pk,
    )

    if not _can_access_greige_po(request.user, po):
        raise PermissionDenied("You do not have access to this Greige PO.")

    try:
        response = _build_greige_po_pdf_response(po)
    except Exception:
        logger.exception(
            "Branded Greige PO PDF generation failed for PO id=%s system_no=%s",
            po.pk,
            po.system_number,
        )
        response = _build_simple_greige_po_pdf_response(po)

    if response.status_code == 200 and response.get("Content-Type", "").startswith("application/pdf"):
        filename = f'{po.system_number or "greige_po"}.pdf'
        disposition = "attachment" if request.GET.get("download") == "1" else "inline"
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        response["Cache-Control"] = "no-store"
        response["X-Content-Type-Options"] = "nosniff"
        try:
            response["Content-Length"] = str(len(response.content))
        except Exception:
            pass

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

def _build_simple_greige_po_pdf_response(po):
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

    items = list(po.items.all())
    total_amount = sum((item.final_amount or Decimal("0")) for item in items)
    total_qty = sum((item.quantity or Decimal("0")) for item in items)

    firm = getattr(po.source_yarn_po, "firm", None)

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
    pdf.drawString(left, top, safe_text(firm.firm_name if firm else "InventTech"))

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawRightString(width - 15 * mm, top, "GREIGE PURCHASE ORDER")

    y = top - 9 * mm
    draw_line("PO No", po.po_number or po.system_number, y)
    draw_line("PO Date", po.po_date.strftime("%d-%m-%Y") if po.po_date else "-", y - line_gap)
    draw_line("System No", po.system_number, y - (2 * line_gap))
    draw_line("Status", po.get_approval_status_display(), y - (3 * line_gap))
    draw_line("Source Yarn PO", po.source_yarn_po.system_number if po.source_yarn_po else "-", y - (4 * line_gap))

    y -= 32 * mm

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
        safe_text(firm.firm_name if firm else ""),
        f"Phone: {safe_text(getattr(firm, 'phone', ''))}",
        f"Email: {safe_text(getattr(firm, 'email', ''))}",
        f"GSTIN: {safe_text(getattr(firm, 'gst_number', ''))}",
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
    pdf.drawString(left + 12 * mm, y, "Fabric")
    pdf.drawString(left + 62 * mm, y, "Yarn")
    pdf.drawString(left + 108 * mm, y, "Unit")
    pdf.drawRightString(left + 135 * mm, y, "Qty")
    pdf.drawRightString(left + 162 * mm, y, "Rate")
    pdf.drawRightString(width - 15 * mm, y, "Amount")

    y -= 4 * mm
    pdf.line(left, y, width - 15 * mm, y)
    y -= 6 * mm

    for index, item in enumerate(items, start=1):
        if y < 45 * mm:
            pdf.showPage()
            y = height - 20 * mm

            pdf.setFont("Helvetica-Bold", 9)
            pdf.drawString(left, y, "Sr")
            pdf.drawString(left + 12 * mm, y, "Fabric")
            pdf.drawString(left + 62 * mm, y, "Yarn")
            pdf.drawString(left + 108 * mm, y, "Unit")
            pdf.drawRightString(left + 135 * mm, y, "Qty")
            pdf.drawRightString(left + 162 * mm, y, "Rate")
            pdf.drawRightString(width - 15 * mm, y, "Amount")
            y -= 4 * mm
            pdf.line(left, y, width - 15 * mm, y)
            y -= 6 * mm

        fabric_name = item.fabric_name or (item.material.name if item.material else "Greige Item")
        yarn_name = item.yarn_name or "-"
        unit = item.unit or "-"
        qty = item.quantity or Decimal("0")
        rate = item.rate or Decimal("0")
        amount = item.final_amount or Decimal("0")

        pdf.setFont("Helvetica", 8.5)
        pdf.drawString(left, y, str(index))
        pdf.drawString(left + 12 * mm, y, safe_text(fabric_name)[:28])
        pdf.drawString(left + 62 * mm, y, safe_text(yarn_name)[:24])
        pdf.drawString(left + 108 * mm, y, safe_text(unit)[:8])
        pdf.drawRightString(left + 135 * mm, y, qty_text(qty))
        pdf.drawRightString(left + 162 * mm, y, money_text(rate))
        pdf.drawRightString(width - 15 * mm, y, money_text(amount))
        y -= 6 * mm

    y -= 4 * mm
    pdf.line(left, y, width - 15 * mm, y)
    y -= 8 * mm

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(left, y, f"Total Qty: {qty_text(total_qty)}")
    pdf.drawRightString(left + 162 * mm, y, "Total Amount")
    pdf.drawRightString(width - 15 * mm, y, money_text(total_amount))

    y -= 12 * mm
    pdf.setFont("Helvetica", 8.5)
    pdf.drawString(left, y, "THIS PO IS COMPUTER GENERATED, HENCE SIGNATURE IS NOT REQUIRED")

    pdf.save()
    buffer.seek(0)

    return HttpResponse(buffer.getvalue(), content_type="application/pdf")


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

    template = _pick_template(
        "accounts/jobbers/jobbertype_edit_embed.html" if _is_embed(request) else "accounts/jobbers/jobbertype_edit.html",
        "accounts/jobbers/jobbertype_edit_embed.html",
    )
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
            queryset=GreigePOInward.objects.select_related("vendor").prefetch_related("items__po_item"),
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
        .select_related("vendor", "firm", "source_greige_po", "source_greige_inward", "reviewed_by", "owner")
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

def _sync_greige_po_items_from_source(
    greige_po,
    source_inward=None,
    greige_material_map=None,
    greige_unit_map=None,
):
    yarn_po = (
        _greige_source_queryset()
        .filter(pk=greige_po.source_yarn_po_id)
        .first()
    )
    if yarn_po is None:
        return Decimal("0")

    greige_material_map = greige_material_map or {}
    greige_unit_map = greige_unit_map or {}

    item_rows = []
    total_weight = Decimal("0")

    if source_inward is not None:
        inward_items = source_inward.items.select_related("po_item__material", "po_item__material_type")
        for inward_item in inward_items:
            yarn_item = inward_item.po_item
            inward_qty = inward_item.quantity or Decimal("0")
            if yarn_item is None or inward_qty <= 0:
                continue

            source_yarn_name = (
                yarn_item.material_type.name
                if yarn_item.material_type
                else (yarn_item.material.name if yarn_item.material else "Yarn Item")
            )

            selected_greige_material = greige_material_map.get(yarn_item.id)
            fabric_name = (
                selected_greige_material.name
                if selected_greige_material is not None
                else source_yarn_name
            )

            unit_name = greige_unit_map.get(yarn_item.id) or yarn_item.unit or ""

            item_rows.append(
                GreigePurchaseOrderItem(
                    po=greige_po,
                    source_yarn_po_item=yarn_item,
                    fabric_name=fabric_name,
                    yarn_name=source_yarn_name,
                    unit=unit_name,
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

            source_yarn_name = (
                yarn_item.material_type.name
                if yarn_item.material_type
                else (yarn_item.material.name if yarn_item.material else "Yarn Item")
            )

            item_rows.append(
                GreigePurchaseOrderItem(
                    po=greige_po,
                    source_yarn_po_item=yarn_item,
                    fabric_name=source_yarn_name,
                    yarn_name=source_yarn_name,
                    unit=yarn_item.unit or "",
                    quantity=inward_qty,
                    remark=f"Generated from Yarn inward of {yarn_po.system_number}",
                )
            )
            total_weight += inward_qty

    GreigePurchaseOrderItem.objects.filter(po=greige_po).delete()
    if item_rows:
        GreigePurchaseOrderItem.objects.bulk_create(item_rows)

    greige_po.available_qty = total_weight
    greige_po.save(update_fields=["available_qty", "updated_at"])
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
    subtotal = Decimal("0")
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
                    total_qty=inward_qty,
                    remaining_qty=inward_qty,
                    value=Decimal("0"),
                    rolls=Decimal("0"),
                    dyeing_type="",
                    dyeing_name="",
                    rate=Decimal("0"),
                    other_charge_amount=Decimal("0"),
                    job_work_charges=Decimal("0"),
                    description="",
                    remark=f"Generated from Greige inward {source_inward.inward_number}",
                    line_subtotal=Decimal("0"),
                    line_final_amount=Decimal("0"),
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
                    total_qty=inward_qty,
                    remaining_qty=inward_qty,
                    value=Decimal("0"),
                    rolls=Decimal("0"),
                    dyeing_type="",
                    dyeing_name="",
                    rate=Decimal("0"),
                    other_charge_amount=Decimal("0"),
                    job_work_charges=Decimal("0"),
                    description="",
                    remark=f"Generated from Greige inward of {greige_po.system_number}",
                    line_subtotal=Decimal("0"),
                    line_final_amount=Decimal("0"),
                )
            )
            total_weight += inward_qty

    DyeingPurchaseOrderItem.objects.filter(po=dyeing_po).delete()
    if item_rows:
        DyeingPurchaseOrderItem.objects.bulk_create(item_rows)

    update_fields = ["total_weight", "updated_at"]
    dyeing_po.total_weight = total_weight

    if hasattr(dyeing_po, "subtotal"):
        dyeing_po.subtotal = subtotal
        update_fields.append("subtotal")

    if hasattr(dyeing_po, "after_discount_value"):
        dyeing_po.after_discount_value = subtotal
        update_fields.append("after_discount_value")

    if hasattr(dyeing_po, "final_amount"):
        dyeing_po.final_amount = subtotal
        update_fields.append("final_amount")

    if hasattr(dyeing_po, "available_qty"):
        dyeing_po.available_qty = total_weight
        update_fields.append("available_qty")

    dyeing_po.save(update_fields=update_fields)
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
            | Q(source_yarn_po__firm__firm_name__icontains=q)
        ).distinct()

    return render(
        request,
        "accounts/greige_po/list.html",
        {
            "orders": qs,
            "q": q,
            "can_review_greige_po": _can_review_yarn_po(request.user),
        },
    )

@login_required
@require_http_methods(["GET", "POST"])
def greige_inward_edit(request, pk: int):
    inward = get_object_or_404(
        GreigePOInward.objects.select_related("po__vendor", "po__firm", "po__owner"),
        pk=pk,
    )
    po = inward.po

    if not _can_access_greige_po(request.user, po):
        raise PermissionDenied("You do not have access to this Greige inward.")

    if not _is_po_approved_for_inward(po):
        messages.error(request, "Greige PO must be approved before inward can be updated.")
        return redirect("accounts:greige_inward_tracker")

    if inward.generated_dyeing_pos.exists():
        messages.error(request, "This inward cannot be edited because a Dyeing PO has already been generated from it.")
        tracker_url = reverse("accounts:greige_inward_tracker")
        return redirect(f"{tracker_url}?inward={inward.pk}")

    item_errors = {}
    line_inputs = {
        row.po_item_id: {
            "qty": row.quantity,
            "remark": row.remark or "",
        }
        for row in inward.items.all()
    }

    inward_form = GreigePOInwardForm(request.POST or None, instance=inward, user=request.user)

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

            other_inward_qty = (
                item.inward_items.exclude(inward=inward).aggregate(total=Sum("quantity")).get("total")
                or Decimal("0")
            )
            max_editable_qty = (item.quantity or Decimal("0")) - other_inward_qty

            if qty > max_editable_qty:
                item_errors[item.id] = "Entered quantity is greater than remaining quantity."
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

            GreigePOInwardItem.objects.bulk_create([
                GreigePOInwardItem(
                    inward=inward,
                    po_item=item,
                    quantity=qty,
                    remark=remark,
                )
                for item, qty, remark in line_payload
            ])

            messages.success(request, f"Inward {inward.inward_number} updated successfully.")
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
            "editing_inward": inward,
            "next_inward_number_preview": inward.inward_number,
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

    temp_po = GreigePurchaseOrder(
        source_yarn_po=source_yarn_po,
        source_yarn_inward=selected_source_inward,
    )

    if request.method == "POST":
        form = GreigePurchaseOrderForm(
            request.POST,
            user=request.user,
            source_yarn_po=source_yarn_po,
            lock_source=bool(source_yarn_po),
        )
        formset = GreigePurchaseOrderItemFormSet(
            request.POST,
            instance=temp_po,
            prefix="items",
            form_kwargs={"user": request.user},
        )

        if form.is_valid() and formset.is_valid():
            selected_source = source_yarn_po or form.cleaned_data["source_yarn_po"]
            if not _can_access_yarn_po(request.user, selected_source):
                raise PermissionDenied("You do not have access to this Yarn PO.")

            if selected_source_inward is not None and selected_source_inward.po_id != selected_source.id:
                form.add_error(None, "Selected Yarn inward does not belong to the chosen Yarn PO.")
            elif selected_source_inward is not None and selected_source_inward.generated_greige_pos.exists():
                form.add_error(None, "Greige PO already exists for this Yarn inward.")
            else:
                with transaction.atomic():
                    greige_po = form.save(commit=False)
                    greige_po.owner = selected_source.owner
                    greige_po.system_number = _next_greige_po_number()
                    greige_po.source_yarn_po = selected_source
                    greige_po.source_yarn_inward = selected_source_inward

                    if not greige_po.shipping_address and selected_source.firm:
                        greige_po.shipping_address = _firm_address(selected_source.firm)

                    greige_po.save()

                    formset.instance = greige_po
                    items = formset.save(commit=False)

                    for obj in formset.deleted_objects:
                        obj.delete()

                    for item in items:
                        item.po = greige_po
                        item.source_yarn_po_item = None
                        item.fabric_name = item.material.name if item.material else ""
                        item.yarn_name = ""
                        item.save()

                    formset.save_m2m()

                    total_qty = greige_po.items.aggregate(total=Sum("quantity")).get("total") or Decimal("0")
                    greige_po.available_qty = total_qty
                    greige_po.save(update_fields=["available_qty", "updated_at"])

                messages.success(request, f"Greige PO {greige_po.system_number} saved successfully.")
                return redirect("accounts:greigepo_inward", pk=greige_po.pk)
    else:
        initial = {}
        if source_yarn_po is not None:
            initial = {
                "po_number": source_yarn_po.po_number or "",
                "po_date": timezone.localdate(),
                "available_qty": Decimal("0.00"),
                "vendor": source_yarn_po.vendor_id,
                "shipping_address": _firm_address(source_yarn_po.firm) if source_yarn_po.firm else "",
            }

        form = GreigePurchaseOrderForm(
            initial=initial,
            user=request.user,
            source_yarn_po=source_yarn_po,
            lock_source=bool(source_yarn_po),
        )
        formset = GreigePurchaseOrderItemFormSet(
            instance=temp_po,
            prefix="items",
            form_kwargs={"user": request.user},
        )

    source_inwards = [selected_source_inward] if selected_source_inward else (list(source_yarn_po.inwards.all()) if source_yarn_po else [])
    effective_owner = source_yarn_po.owner if source_yarn_po else request.user

    terms_condition_options = _greige_terms_condition_options(effective_owner)

    selected_terms_condition_id = (request.POST.get("terms_condition_id") or "").strip() if request.method == "POST" else ""
    greige_description = (request.POST.get("greige_description") or "").strip() if request.method == "POST" else ""
    greige_total_weight = request.POST.get("greige_total_weight") or "0.00"
    greige_subtotal = request.POST.get("greige_subtotal") or "0.00"
    greige_discount_percent = request.POST.get("greige_discount_percent") or "0"
    greige_after_discount = request.POST.get("greige_after_discount") or "0.00"
    greige_others = request.POST.get("greige_others") or "0"
    greige_cgst = request.POST.get("greige_cgst") or "2.5"
    greige_sgst = request.POST.get("greige_sgst") or "2.5"

    return render(
        request,
        "accounts/greige_po/form.html",
        {
            "form": form,
            "formset": formset,
            "mode": "add",
            "po_obj": None,
            "system_number_preview": _next_greige_po_number(),
            "source_yarn_po": source_yarn_po,
            "selected_source_inward": selected_source_inward,
            "source_inwards": source_inwards,
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

    formset = GreigePurchaseOrderItemFormSet(
        request.POST or None,
        instance=po,
        prefix="items",
        form_kwargs={"user": request.user},
    )

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            po = form.save(commit=False)
            if not po.shipping_address and po.source_yarn_po and po.source_yarn_po.firm:
                po.shipping_address = _firm_address(po.source_yarn_po.firm)
            po.save()

            items = formset.save(commit=False)

            for obj in formset.deleted_objects:
                obj.delete()

            for item in items:
                item.po = po
                item.source_yarn_po_item = None
                item.fabric_name = item.material.name if item.material else ""
                item.yarn_name = ""
                item.save()

            formset.save_m2m()

            total_qty = po.items.aggregate(total=Sum("quantity")).get("total") or Decimal("0")
            po.available_qty = total_qty
            po.save(update_fields=["available_qty", "updated_at"])

        messages.success(request, f"Greige PO {po.system_number} updated successfully.")
        return redirect("accounts:greigepo_inward", pk=po.pk)

    source_inwards = [po.source_yarn_inward] if po.source_yarn_inward else (list(po.source_yarn_po.inwards.all()) if po.source_yarn_po else [])
    effective_owner = po.owner

    terms_condition_options = _greige_terms_condition_options(effective_owner)

    selected_terms_condition_id = (request.POST.get("terms_condition_id") or "").strip()
    greige_description = (request.POST.get("greige_description") or "").strip()
    greige_total_weight = request.POST.get("greige_total_weight") or str(po.available_qty or "0.00")
    greige_subtotal = request.POST.get("greige_subtotal") or "0.00"
    greige_discount_percent = request.POST.get("greige_discount_percent") or "0"
    greige_after_discount = request.POST.get("greige_after_discount") or "0.00"
    greige_others = request.POST.get("greige_others") or "0"
    greige_cgst = request.POST.get("greige_cgst") or "2.5"
    greige_sgst = request.POST.get("greige_sgst") or "2.5"

    return render(
        request,
        "accounts/greige_po/form.html",
        {
            "form": form,
            "formset": formset,
            "mode": "edit",
            "po_obj": po,
            "system_number_preview": po.system_number,
            "source_yarn_po": po.source_yarn_po,
            "selected_source_inward": po.source_yarn_inward,
            "source_inwards": source_inwards,
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
    inward_form = GreigePOInwardForm(request.POST or None, user=po.owner)

    if request.method == "GET" and po.vendor_id and "vendor" in inward_form.fields:
        inward_form.fields["vendor"].initial = po.vendor_id

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

            if not inward.vendor_id and po.vendor_id:
                inward.vendor = po.vendor

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
            "next_inward_number_preview": _next_greige_inward_number(),
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
            | Q(source_yarn_po__firm__firm_name__icontains=q)
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
    if not _is_po_approved_for_inward(dyeing_po):
        messages.error(request, "Dyeing PO must be approved before Ready PO can be generated.")
        return redirect("accounts:dyeingpo_list")
    if not dyeing_po.inwards.exists():
        messages.error(request, "Create at least one Dyeing inward before generating Ready PO.")
        return redirect("accounts:dyeingpo_inward", pk=dyeing_po.pk)
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
            "can_review_dyeing_po": _can_review_yarn_po(request.user),
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

    temp_po = DyeingPurchaseOrder(
        source_greige_po=source_greige_po,
        source_greige_inward=selected_source_inward,
    )

    if request.method == "POST":
        form = DyeingPurchaseOrderForm(
            request.POST,
            user=request.user,
            source_greige_po=source_greige_po,
            lock_source=bool(source_greige_po),
        )
        formset = DyeingPurchaseOrderItemFormSet(
            request.POST,
            instance=temp_po,
            prefix="items",
            form_kwargs={"user": request.user},
        )

        if form.is_valid() and formset.is_valid():
            selected_source = source_greige_po or form.cleaned_data["source_greige_po"]
            if not _can_access_greige_po(request.user, selected_source):
                raise PermissionDenied("You do not have access to this Greige PO.")

            if selected_source_inward is not None and selected_source_inward.po_id != selected_source.id:
                form.add_error(None, "Selected Greige inward does not belong to the chosen Greige PO.")
            elif selected_source_inward is not None and selected_source_inward.generated_dyeing_pos.exists():
                form.add_error(None, "Dyeing PO already exists for this Greige inward.")
            elif selected_source_inward is None and not selected_source.inwards.exists():
                form.add_error("source_greige_po", "Selected Greige PO has no inward entries yet.")
            elif selected_source_inward is None and selected_source.dyeing_pos.filter(source_greige_inward__isnull=True).exists():
                form.add_error("source_greige_po", "Dyeing PO already exists for this Greige PO.")
            else:
                with transaction.atomic():
                    dyeing_po = form.save(commit=False)
                    dyeing_po.owner = selected_source.owner
                    dyeing_po.system_number = _next_dyeing_po_number()
                    dyeing_po.source_greige_po = selected_source
                    dyeing_po.source_greige_inward = selected_source_inward

                    if dyeing_po.firm and not dyeing_po.shipping_address:
                        dyeing_po.shipping_address = _firm_address(dyeing_po.firm)

                    dyeing_po.save()

                    formset.instance = dyeing_po
                    items = formset.save(commit=False)

                    for obj in formset.deleted_objects:
                        obj.delete()

                    total_weight = Decimal("0")
                    subtotal = Decimal("0")

                    for item in items:
                        item.po = dyeing_po

                        if item.finished_material:
                            item.fabric_name = item.finished_material.name
                        elif item.dyeing_name:
                            item.fabric_name = item.dyeing_name
                        else:
                            item.fabric_name = "Dyeing Item"

                        if not item.greige_name:
                            if selected_source_inward and selected_source_inward.items.exists():
                                first_inward_item = selected_source_inward.items.select_related("po_item").first()
                                if first_inward_item and first_inward_item.po_item:
                                    item.greige_name = first_inward_item.po_item.fabric_name or ""
                            elif selected_source and selected_source.items.exists():
                                first_po_item = selected_source.items.first()
                                if first_po_item:
                                    item.greige_name = first_po_item.fabric_name or ""

                        item.quantity = item.total_qty or Decimal("0")
                        if not item.remaining_qty:
                            item.remaining_qty = item.total_qty or Decimal("0")

                        item.line_subtotal = item.line_subtotal or Decimal("0")
                        item.line_final_amount = item.line_final_amount or Decimal("0")

                        item.save()

                        total_weight += item.total_qty or Decimal("0")
                        subtotal += item.line_final_amount or Decimal("0")

                    formset.save_m2m()

                    discount = dyeing_po.discount_percent or Decimal("0")
                    others = dyeing_po.others or Decimal("0")
                    gst = dyeing_po.gst_percent or Decimal("0")
                    tcs = dyeing_po.tcs_percent or Decimal("0")

                    after_discount = subtotal - (subtotal * discount / Decimal("100"))
                    after_others = after_discount + others
                    gst_amount = after_others * gst / Decimal("100")
                    tcs_amount = after_others * tcs / Decimal("100")
                    final_amount = after_others + gst_amount + tcs_amount

                    dyeing_po.total_weight = total_weight
                    dyeing_po.subtotal = subtotal
                    dyeing_po.after_discount_value = after_discount
                    dyeing_po.final_amount = final_amount
                    dyeing_po.save(update_fields=[
                        "total_weight",
                        "subtotal",
                        "after_discount_value",
                        "final_amount",
                        "updated_at",
                    ])

                messages.success(request, f"Dyeing PO {dyeing_po.system_number} saved successfully.")
                return redirect("accounts:dyeingpo_list")
    else:
        initial = {}
        if source_greige_po is not None:
            initial = {
                "po_number": source_greige_po.po_number or "",
                "po_date": timezone.localdate(),
                "vendor": source_greige_po.vendor_id,
                "firm": source_greige_po.source_yarn_po.firm_id if source_greige_po.source_yarn_po and source_greige_po.source_yarn_po.firm else None,
                "shipping_address": _firm_address(source_greige_po.source_yarn_po.firm) if source_greige_po.source_yarn_po and source_greige_po.source_yarn_po.firm else "",
                "remarks": (
                    f"Generated from Greige inward {selected_source_inward.inward_number}"
                    if selected_source_inward else
                    f"Generated from Greige PO {source_greige_po.system_number}"
                ),
            }

        form = DyeingPurchaseOrderForm(
            initial=initial,
            user=request.user,
            source_greige_po=source_greige_po,
            lock_source=bool(source_greige_po),
        )
        formset = DyeingPurchaseOrderItemFormSet(
            instance=temp_po,
            prefix="items",
            form_kwargs={"user": request.user},
        )

    return render(
    request,
    "accounts/dyeing_po/form.html",
    {
        "form": form,
        "formset": formset,
        "mode": "add",
        "po_obj": None,
        "source_greige_po": source_greige_po,
        "selected_source_inward": selected_source_inward,
        "source_inwards": [selected_source_inward] if selected_source_inward else (list(source_greige_po.inwards.all()) if source_greige_po else []),
        "existing_po": selected_source_inward.generated_dyeing_pos.order_by("-id").first() if selected_source_inward else (source_greige_po.dyeing_pos.order_by("-id").first() if source_greige_po else None),
        "system_number_preview": _next_dyeing_po_number(),
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

    formset = DyeingPurchaseOrderItemFormSet(
        request.POST or None,
        instance=po,
        prefix="items",
        form_kwargs={"user": request.user},
    )

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            po = form.save(commit=False)
            if po.firm and not po.shipping_address:
                po.shipping_address = _firm_address(po.firm)
            po.save()

            items = formset.save(commit=False)

            for obj in formset.deleted_objects:
                obj.delete()

            total_weight = Decimal("0")
            subtotal = Decimal("0")

            for item in items:
                item.po = po

                if item.finished_material:
                    item.fabric_name = item.finished_material.name
                elif item.dyeing_name:
                    item.fabric_name = item.dyeing_name
                else:
                    item.fabric_name = "Dyeing Item"

                item.quantity = item.total_qty or Decimal("0")
                if not item.remaining_qty:
                    item.remaining_qty = item.total_qty or Decimal("0")

                item.save()

                total_weight += item.total_qty or Decimal("0")
                subtotal += item.line_final_amount or Decimal("0")

            formset.save_m2m()

            discount = po.discount_percent or Decimal("0")
            others = po.others or Decimal("0")
            gst = po.gst_percent or Decimal("0")
            tcs = po.tcs_percent or Decimal("0")

            after_discount = subtotal - (subtotal * discount / Decimal("100"))
            after_others = after_discount + others
            gst_amount = after_others * gst / Decimal("100")
            tcs_amount = after_others * tcs / Decimal("100")
            final_amount = after_others + gst_amount + tcs_amount

            po.total_weight = total_weight
            po.subtotal = subtotal
            po.after_discount_value = after_discount
            po.final_amount = final_amount
            po.save(update_fields=[
                "total_weight",
                "subtotal",
                "after_discount_value",
                "final_amount",
                "updated_at",
            ])

        return redirect("accounts:dyeingpo_list")

    return render(
        request,
        "accounts/dyeing_po/form.html",
        {
            "form": form,
            "formset": formset,
            "mode": "edit",
            "po_obj": po,
            "source_greige_po": po.source_greige_po,
            "selected_source_inward": po.source_greige_inward,
            "source_inwards": list(po.source_greige_po.inwards.all()) if po.source_greige_po else [],
            "existing_po": None,
            "system_number_preview": po.system_number,
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

@login_required
@require_http_methods(["GET", "POST"])
def ready_inward_edit(request, pk: int):
    inward = get_object_or_404(
        ReadyPOInward.objects.select_related("po__vendor", "po__firm", "po__owner"),
        pk=pk,
    )
    po = inward.po

    if not _can_access_ready_po(request.user, po):
        raise PermissionDenied("You do not have access to this Ready inward.")

    item_errors = {}
    line_inputs = {
        row.po_item_id: {
            "qty": row.quantity,
            "remark": row.remark or "",
        }
        for row in inward.items.all()
    }

    inward_form = ReadyPOInwardForm(request.POST or None, instance=inward, user=request.user)

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

            other_inward_qty = (
                item.inward_items.exclude(inward=inward).aggregate(total=Sum("quantity")).get("total")
                or Decimal("0")
            )
            max_editable_qty = (item.quantity or Decimal("0")) - other_inward_qty

            if qty > max_editable_qty:
                item_errors[item.id] = "Entered quantity is greater than remaining quantity."
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

            ReadyPOInwardItem.objects.bulk_create([
                ReadyPOInwardItem(
                    inward=inward,
                    po_item=item,
                    quantity=qty,
                    remark=remark,
                )
                for item, qty, remark in line_payload
            ])

            messages.success(request, f"Inward {inward.inward_number} updated successfully.")
            tracker_url = reverse("accounts:ready_inward_tracker")
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
        "accounts/ready_po/inward.html",
        {
            "po": po,
            "inward_form": inward_form,
            "line_rows": line_rows,
            "existing_inwards": po.inwards.all().order_by("-inward_date", "-id"),
            "editing_inward": inward,
            "next_inward_number_preview": inward.inward_number,
        },
    )
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
    if not _is_po_approved_for_inward(po):
        messages.error(request, "Dyeing PO must be approved before inward can be generated.")
        return redirect("accounts:dyeingpo_list")

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
            "po_item__finished_material",
            "po_item__source_greige_po_item",
        )
        .filter(inward__owner=user)
        .order_by("-inward__inward_date", "-id")
    )

    for inward_item in dyeing_inward_items:
        inward = inward_item.inward
        po_item = inward_item.po_item
        po = po_item.po if po_item else None

        ready_material_name = "Ready Material"
        raw_material_name = "-"
        dyeing_name = "-"
        dyeing_type = "-"
        unit = "KG"

        if po_item:
            if po_item.finished_material:
                ready_material_name = po_item.finished_material.name
            elif po_item.fabric_name:
                ready_material_name = po_item.fabric_name
            else:
                ready_material_name = "Ready Material"

            raw_material_name = po_item.greige_name or "-"
            dyeing_name = po_item.dyeing_name or "-"
            dyeing_type = po_item.dyeing_type or "-"
            unit = po_item.unit or "KG"

        vendor_name = po.vendor.name if po and po.vendor else "-"
        firm_name = po.firm.firm_name if po and po.firm else "-"
        quantity = inward_item.quantity or Decimal("0")

        rows.append({
            "stage": "ready",
            "stage_label": "Ready",
            "lot_number": inward.inward_number or f"DYEING-{inward.pk}",
            "lot_date": inward.inward_date,
            "material_name": ready_material_name,
            "material_key": _normalize_stock_lot_search_value(ready_material_name),
            "ready_material_name": ready_material_name,
            "raw_material_name": raw_material_name,
            "vendor_name": vendor_name,
            "firm_name": firm_name,
            "source_number": po.system_number if po and po.system_number else (po.po_number if po else "-"),
            "quantity": quantity,
            "used_quantity": Decimal("0"),
            "final_stock": quantity,
            "unit": unit,
            "remark": inward_item.remark or "",
            "dyeing_name": dyeing_name,
            "dyeing_type": dyeing_type,
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
    target_inward_id = (request.GET.get("inward") or "").strip()

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
                "is_target": str(inward.id) == target_inward_id,
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
            "target_inward_id": target_inward_id,
        },
    )

@login_required
@require_http_methods(["GET", "POST"])
def dyeing_inward_edit(request, pk: int):
    inward = get_object_or_404(
        DyeingPOInward.objects.select_related("po__vendor", "po__firm", "po__owner"),
        pk=pk,
    )
    po = inward.po
    if not _is_po_approved_for_inward(po):
        messages.error(request, "Dyeing PO must be approved before inward can be updated.")
        return redirect("accounts:dyeing_inward_tracker")

    if po.ready_pos.exists():
        messages.error(
            request,
            "This inward cannot be edited because a Ready PO has already been generated from this Dyeing PO."
        )
        tracker_url = reverse("accounts:dyeing_inward_tracker")
        return redirect(f"{tracker_url}?inward={inward.pk}")
    if not _can_access_dyeing_po(request.user, po):
        raise PermissionDenied("You do not have access to this Dyeing inward.")

    if po.ready_pos.exists():
        messages.error(request, "This inward cannot be edited because a Ready PO has already been generated from this Dyeing PO.")
        tracker_url = reverse("accounts:dyeing_inward_tracker")
        return redirect(f"{tracker_url}?inward={inward.pk}")

    item_errors = {}
    line_inputs = {
        row.po_item_id: {
            "qty": row.quantity,
            "remark": row.remark or "",
        }
        for row in inward.items.all()
    }

    inward_form = DyeingPOInwardForm(request.POST or None, instance=inward, user=request.user)

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

            other_inward_qty = (
                item.inward_items.exclude(inward=inward).aggregate(total=Sum("quantity")).get("total")
                or Decimal("0")
            )
            max_editable_qty = (item.quantity or Decimal("0")) - other_inward_qty

            if qty > max_editable_qty:
                item_errors[item.id] = "Entered quantity is greater than remaining quantity."
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

            DyeingPOInwardItem.objects.bulk_create([
                DyeingPOInwardItem(
                    inward=inward,
                    po_item=item,
                    quantity=qty,
                    remark=remark,
                )
                for item, qty, remark in line_payload
            ])

            messages.success(request, f"Inward {inward.inward_number} updated successfully.")
            tracker_url = reverse("accounts:dyeing_inward_tracker")
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
        "accounts/dyeing_po/inward.html",
        {
            "po": po,
            "inward_form": inward_form,
            "line_rows": line_rows,
            "existing_inwards": po.inwards.all().order_by("-inward_date", "-id"),
            "existing_ready_po": po.ready_pos.order_by("-id").first(),
            "editing_inward": inward,
            "next_inward_number_preview": inward.inward_number,
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
        if not _is_po_approved_for_inward(source_dyeing_po):
            messages.error(request, "Dyeing PO must be approved before Ready PO can be created.")
            return redirect("accounts:dyeingpo_list")
        if not source_dyeing_po.inwards.exists():
            messages.error(request, "Create at least one Dyeing inward before generating Ready PO.")
            return redirect("accounts:dyeingpo_inward", pk=source_dyeing_po.pk)

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
            elif not _is_po_approved_for_inward(selected_source):
                form.add_error("source_dyeing_po", "Selected Dyeing PO must be approved before Ready PO can be created.")
            elif not selected_source.inwards.exists():
                form.add_error("source_dyeing_po", "Selected Dyeing PO must have inward entries before Ready PO can be created.")
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
    target_inward_id = (request.GET.get("inward") or "").strip()

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
                "is_target": str(inward.id) == target_inward_id,
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
            "target_inward_id": target_inward_id,
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

def _accessory_list_url(request):
    url = reverse("accounts:accessory_list")
    if _is_embed(request):
        url += "?embed=1"
    return url


@login_required
@require_http_methods(["GET", "POST"])
def accessory_list_create(request):
    q = (request.GET.get("q") or "").strip()

    accessories = Accessory.objects.filter(owner=request.user).select_related("default_unit").order_by("name")
    if q:
        accessories = accessories.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )

    if request.method == "POST":
        form = AccessoryForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()

            url = _accessory_list_url(request)
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)
    else:
        form = AccessoryForm(user=request.user)

    template = (
        "accounts/accessories/list_embed.html"
        if _is_embed(request)
        else "accounts/accessories/list.html"
    )
    return render(
        request,
        template,
        {
            "accessories": accessories,
            "form": form,
            "q": q,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def accessory_edit(request, pk: int):
    accessory = get_object_or_404(Accessory, pk=pk, owner=request.user)
    form = AccessoryForm(request.POST or None, instance=accessory, user=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        url = _accessory_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = (
        "accounts/accessories/edit_embed.html"
        if _is_embed(request)
        else "accounts/accessories/edit.html"
    )
    return render(
        request,
        template,
        {
            "form": form,
            "accessory": accessory,
        },
    )


@login_required
@require_POST
def accessory_delete(request, pk: int):
    accessory = get_object_or_404(Accessory, pk=pk, owner=request.user)
    accessory.delete()

    url = _accessory_list_url(request)
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)

@login_required
@require_GET
def dyeing_other_charge_list(request):
    q = (request.GET.get("q") or "").strip()

    charges = DyeingOtherCharge.objects.filter(owner=request.user).order_by("name")
    if q:
        charges = charges.filter(name__icontains=q)

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


def _greige_terms_condition_options(owner):

    qs = TermsCondition.objects.all()
    if owner is not None:
        qs = qs.filter(owner=owner)
    return qs.order_by("title")


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
    source_greige_po = getattr(po, "source_greige_po", None)
    source_dyeing_po = getattr(po, "source_dyeing_po", None)

    for source in [source_yarn_po, source_greige_po, source_dyeing_po]:
        source_status = str(getattr(source, "approval_status", "") or "").strip().lower()
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

@login_required
@require_http_methods(["GET", "POST"])
def dyeingpo_review(request, pk: int):
    po = get_object_or_404(
        _dyeing_po_queryset(),
        pk=pk,
    )

    if not _can_access_dyeing_po(request.user, po):
        raise PermissionDenied("You do not have access to this Dyeing PO.")

    review_field_names = ("approval_status", "rejection_reason", "reviewed_by", "reviewed_at")
    review_templates_available = (
        _template_exists("accounts/dyeing_po/review.html")
        and _template_exists("accounts/dyeing_po/review_embed.html")
    )

    if not _model_has_fields(DyeingPurchaseOrder, *review_field_names) or not review_templates_available:
        message = "Dyeing PO review needs model review fields and review templates before this page can work."
        if _is_embed(request):
            return JsonResponse({
                "ok": False,
                "message": message,
                "redirect_url": reverse("accounts:dyeingpo_list"),
            }, status=400)
        messages.error(request, message)
        return redirect("accounts:dyeingpo_list")

    embed_mode = _is_embed(request)
    can_review = _can_review_yarn_po(request.user)

    review_form = DyeingPOReviewForm(request.POST or None)

    review_checks = {
        "has_header": bool(po.vendor_id and po.po_date),
        "has_source": bool(po.source_greige_po_id),
        "has_items": po.items.exists(),
        "has_shipping": bool((po.shipping_address or "").strip()),
    }
    review_ready_count = sum(1 for value in review_checks.values() if value)

    context = {
        "po": po,
        "review_form": review_form,
        "can_review_dyeing_po": can_review,
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
                    "message": "Dyeing PO reviewed successfully.",
                    "redirect_url": reverse("accounts:dyeingpo_list"),
                })

            return redirect("accounts:dyeingpo_list")

        if embed_mode:
            return render(
                request,
                "accounts/dyeing_po/review_embed.html",
                context,
                status=400,
            )

    template_name = (
        "accounts/dyeing_po/review_embed.html"
        if embed_mode
        else "accounts/dyeing_po/review.html"
    )

    return render(request, template_name, context)

def _bom_list_url(request):
    url = reverse("accounts:bom_list")
    if _is_embed(request):
        url += "?embed=1"
    return url


@login_required
def bom_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = (
        BOM.objects.filter(owner=request.user)
        .select_related(
            "catalogue",
            "brand",
            "category",
            "main_category",
            "sub_category",
            "pattern_type",
        )
        .order_by("-id")
    )

    if q:
        qs = qs.filter(
            Q(bom_code__icontains=q)
            | Q(sku__icontains=q)
            | Q(product_name__icontains=q)
        )

    template = "accounts/bom/list_embed.html" if _is_embed(request) else "accounts/bom/list.html"
    return render(
        request,
        template,
        {
            "boms": qs,
            "q": q,
            "full_page": not _is_embed(request),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def bom_create(request):
    bom = BOM(owner=request.user)

    form = BOMForm(
        request.POST or None,
        request.FILES or None,
        instance=bom,
        user=request.user,
    )

    if request.method == "POST":
        material_formset = BOMMaterialItemFormSet(
            request.POST,
            instance=bom,
            prefix="materials",
        )
        accessory_formset = BOMAccessoryItemFormSet(
            request.POST,
            instance=bom,
            prefix="accessories",
        )
        image_formset = BOMImageFormSet(
            request.POST,
            request.FILES,
            instance=bom,
            prefix="images",
        )
        jobber_process_formset = BOMJobberTypeProcessFormSet(
            request.POST,
            instance=bom,
            prefix="jobber_processes",
            form_kwargs={"user": request.user},
        )
        jobber_detail_formset = BOMJobberDetailFormSet(
            request.POST,
            instance=bom,
            prefix="jobber_details",
            form_kwargs={"user": request.user},
        )
        expense_formset = BOMExpenseItemFormSet(
            request.POST,
            instance=bom,
            prefix="expenses",
            form_kwargs={"user": request.user},
        )

        if (
            form.is_valid()
            and material_formset.is_valid()
            and accessory_formset.is_valid()
            and image_formset.is_valid()
            and jobber_process_formset.is_valid()
            and jobber_detail_formset.is_valid()
            and expense_formset.is_valid()
        ):
            with transaction.atomic():
                bom = form.save(commit=False)
                bom.owner = request.user
                bom.save()

                material_formset.instance = bom
                material_formset.save()

                accessory_formset.instance = bom
                accessory_formset.save()

                image_formset.instance = bom
                image_formset.save()

                jobber_process_formset.instance = bom
                jobber_process_formset.save()

                jobber_detail_formset.instance = bom
                jobber_detail_formset.save()

                expense_formset.instance = bom
                expense_formset.save()

                if hasattr(bom, "recalculate_final_price"):
                    bom.recalculate_final_price(save=True)

            url = _bom_list_url(request)
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)
    else:
        material_formset = BOMMaterialItemFormSet(instance=bom, prefix="materials")
        accessory_formset = BOMAccessoryItemFormSet(instance=bom, prefix="accessories")
        image_formset = BOMImageFormSet(instance=bom, prefix="images")
        jobber_process_formset = BOMJobberTypeProcessFormSet(
            instance=bom,
            prefix="jobber_processes",
            form_kwargs={"user": request.user},
        )
        jobber_detail_formset = BOMJobberDetailFormSet(
            instance=bom,
            prefix="jobber_details",
            form_kwargs={"user": request.user},
        )
        expense_formset = BOMExpenseItemFormSet(
            instance=bom,
            prefix="expenses",
            form_kwargs={"user": request.user},
        )

    template = "accounts/bom/form_embed.html" if _is_embed(request) else "accounts/bom/form.html"
    return render(
        request,
        template,
        {
            "form": form,
            "material_formset": material_formset,
            "accessory_formset": accessory_formset,
            "image_formset": image_formset,
            "jobber_process_formset": jobber_process_formset,
            "jobber_detail_formset": jobber_detail_formset,
            "expense_formset": expense_formset,
            "mode": "add",
            "full_page": not _is_embed(request),
            "action_url": reverse("accounts:bom_add"),
        },
    )
    

@login_required
@require_http_methods(["GET", "POST"])
def bom_update(request, pk: int):
    bom = get_object_or_404(BOM, pk=pk, owner=request.user)

    form = BOMForm(
        request.POST or None,
        request.FILES or None,
        instance=bom,
        user=request.user,
    )

    if request.method == "POST":
        material_formset = BOMMaterialItemFormSet(
            request.POST,
            instance=bom,
            prefix="materials",
        )
        accessory_formset = BOMAccessoryItemFormSet(
            request.POST,
            instance=bom,
            prefix="accessories",
        )
        image_formset = BOMImageFormSet(
            request.POST,
            request.FILES,
            instance=bom,
            prefix="images",
        )
        jobber_process_formset = BOMJobberTypeProcessFormSet(
            request.POST,
            instance=bom,
            prefix="jobber_processes",
            form_kwargs={"user": request.user},
        )
        jobber_detail_formset = BOMJobberDetailFormSet(
            request.POST,
            instance=bom,
            prefix="jobber_details",
            form_kwargs={"user": request.user},
        )
        expense_formset = BOMExpenseItemFormSet(
            request.POST,
            instance=bom,
            prefix="expenses",
            form_kwargs={"user": request.user},
        )

        if (
            form.is_valid()
            and material_formset.is_valid()
            and accessory_formset.is_valid()
            and image_formset.is_valid()
            and jobber_process_formset.is_valid()
            and jobber_detail_formset.is_valid()
            and expense_formset.is_valid()
        ):
            with transaction.atomic():
                bom = form.save()

                material_formset.save()
                accessory_formset.save()
                image_formset.save()
                jobber_process_formset.save()
                jobber_detail_formset.save()
                expense_formset.save()

                if hasattr(bom, "recalculate_final_price"):
                    bom.recalculate_final_price(save=True)

            url = _bom_list_url(request)
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)
    else:
        material_formset = BOMMaterialItemFormSet(instance=bom, prefix="materials")
        accessory_formset = BOMAccessoryItemFormSet(instance=bom, prefix="accessories")
        image_formset = BOMImageFormSet(instance=bom, prefix="images")
        jobber_process_formset = BOMJobberTypeProcessFormSet(
            instance=bom,
            prefix="jobber_processes",
            form_kwargs={"user": request.user},
        )
        jobber_detail_formset = BOMJobberDetailFormSet(
            instance=bom,
            prefix="jobber_details",
            form_kwargs={"user": request.user},
        )
        expense_formset = BOMExpenseItemFormSet(
            instance=bom,
            prefix="expenses",
            form_kwargs={"user": request.user},
        )

    template = "accounts/bom/form_embed.html" if _is_embed(request) else "accounts/bom/form.html"
    return render(
        request,
        template,
        {
            "form": form,
            "material_formset": material_formset,
            "accessory_formset": accessory_formset,
            "image_formset": image_formset,
            "jobber_process_formset": jobber_process_formset,
            "jobber_detail_formset": jobber_detail_formset,
            "expense_formset": expense_formset,
            "mode": "edit",
            "bom": bom,
            "full_page": not _is_embed(request),
            "action_url": reverse("accounts:bom_edit", args=[bom.pk]),
        },
    )
    
def _program_edit_url(request, program):
    url = reverse("accounts:program_edit", args=[program.pk])
    if _is_embed(request):
        url += "?embed=1"
    return url

def _bom_preview_image_url(bom):
    # 1) direct image-like fields on BOM itself
    for attr in ("image", "photo", "photo_update", "product_image"):
        field = getattr(bom, attr, None)
        if field and getattr(field, "name", None) and getattr(field, "url", None):
            return field.url

    # 2) child image rows under BOM
    images_manager = getattr(bom, "images", None)
    if images_manager is not None:
        try:
            for img in images_manager.all().order_by("sort_order", "id"):
                for attr in ("image", "photo", "file"):
                    field = getattr(img, attr, None)
                    if field and getattr(field, "name", None) and getattr(field, "url", None):
                        return field.url
        except Exception:
            pass

    return ""

def _program_sku_payloads(user):
    boms = (
        BOM.objects.filter(owner=user)
        .select_related(
            "brand",
            "category",
            "main_category",
            "sub_category",
            "pattern_type",
            "catalogue",
        )
        .prefetch_related(
            Prefetch(
                "material_items",
                queryset=BOMMaterialItem.objects.select_related("material").order_by("sort_order", "id"),
            ),
            Prefetch(
                "accessory_items",
                queryset=BOMAccessoryItem.objects.select_related("accessory").order_by("sort_order", "id"),
            ),
            Prefetch(
                "images",
                queryset=BOMImage.objects.order_by("sort_order", "id"),
            ),
            Prefetch(
                "jobber_type_processes",
                queryset=BOMJobberTypeProcess.objects.select_related("jobber_type").order_by("sort_order", "id"),
            ),
        )
        .order_by("sku")
    )

    payload = {}
    for bom in boms:
        linked_fabrics = [
            item.material.name
            for item in bom.material_items.all()
            if item.material_id and item.material
        ]
        linked_accessories = [
            item.accessory.name
            for item in bom.accessory_items.all()
            if item.accessory_id and item.accessory
        ]
        accessories_price = sum(
            ((item.cost or Decimal("0")) for item in bom.accessory_items.all()),
            Decimal("0"),
        )


        payload[str(bom.pk)] = {
            "sku": bom.sku or "",
            "product_name": bom.product_name or "",
            "linked_fabrics": linked_fabrics,
            "linked_accessories": linked_accessories,
            "brand": getattr(bom.brand, "name", "") or "",
            "gender": bom.gender or "",
            "main_category": getattr(bom.main_category, "name", "") or "",
            "category": getattr(bom.category, "name", "") or "",
            "sub_category": getattr(bom.sub_category, "name", "") or "",
            "pattern_type": getattr(bom.pattern_type, "name", "") or "",
            "character_name": bom.character_name or "",
            "mrp": str(bom.mrp or Decimal("0")),
            "color": bom.color or "",
            "drawcord": bom.drawcord or "",
            "tie_dye_price": str(bom.tie_dye_price or Decimal("0")),
            "accessories_price": str(accessories_price),
            "image_url": _bom_preview_image_url(bom),
            "jobber_process_prices": {
                str(row.jobber_type_id): str(row.price or Decimal("0"))
                for row in bom.jobber_type_processes.all()
                if row.jobber_type_id
            },
        }

    return payload


def _program_jobber_defaults(user):
    rows = (
        Jobber.objects.filter(owner=user, is_active=True)
        .select_related("jobber_type")
        .order_by("name")
    )

    return {
        str(row.pk): {
            "jobber_type_id": str(row.jobber_type_id) if row.jobber_type_id else "",
            "jobber_type_name": row.jobber_type.name if row.jobber_type_id and row.jobber_type else "",
        }
        for row in rows
    }

def _ensure_program_size_rows(program):
    default_rows = [
        ("CQ", 1),
        ("FQ", 2),
        ("DQ", 3),
        ("FQ-DQ", 4),
        ("TP", 5),
    ]

    for line_name, order in default_rows:
        ProgramSizeDetail.objects.get_or_create(
            program=program,
            line_name=line_name,
            defaults={"sort_order": order},
        )

@login_required
@require_POST
def bom_delete(request, pk: int):
    bom = get_object_or_404(BOM, pk=pk, owner=request.user)
    bom.delete()

    url = _bom_list_url(request)
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)

@login_required
@require_http_methods(["GET", "POST"])
def program_create(request):
    program = Program(owner=request.user)

    if request.method == "GET":
        program.program_no = Program.next_program_no(request.user)
        program.program_date = timezone.localdate()

        user_firm = Firm.objects.filter(owner=request.user).first()
        if user_firm:
            program.firm = user_firm

    form = ProgramForm(
        request.POST or None,
        instance=program,
        user=request.user,
    )

    if request.method == "POST":
        jobber_formset = ProgramJobberDetailFormSet(
            request.POST,
            instance=program,
            prefix="jobbers",
            form_kwargs={"user": request.user},
        )

        if form.is_valid() and jobber_formset.is_valid():
            with transaction.atomic():
                program = form.save(commit=False)
                program.owner = request.user
                program.save()
                _ensure_program_size_rows(program)
                jobber_formset.instance = program
                jobber_formset.save()

            messages.success(request, "Program saved successfully.")
            edit_url = _program_edit_url(request, program)
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": edit_url})
            return redirect(edit_url)
    else:
        jobber_formset = ProgramJobberDetailFormSet(
            instance=program,
            prefix="jobbers",
            form_kwargs={"user": request.user},
        )

    template = "accounts/programs/form_embed.html" if _is_embed(request) else "accounts/programs/form.html"
    return render(
        request,
        template,
        {
            "form": form,
            "jobber_formset": jobber_formset,
            "mode": "add",
            "full_page": not _is_embed(request),
            "action_url": reverse("accounts:program_add"),
            "sku_payloads": _program_sku_payloads(request.user),
            "jobber_defaults": _program_jobber_defaults(request.user),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def program_update(request, pk: int):
    program = get_object_or_404(Program, pk=pk, owner=request.user)

    form = ProgramForm(
        request.POST or None,
        instance=program,
        user=request.user,
    )

    if request.method == "POST":
        jobber_formset = ProgramJobberDetailFormSet(
            request.POST,
            instance=program,
            prefix="jobbers",
            form_kwargs={"user": request.user},
        )

        if form.is_valid() and jobber_formset.is_valid():
            with transaction.atomic():
                program = form.save()
                _ensure_program_size_rows(program)
                jobber_formset.save()

            messages.success(request, "Program updated successfully.")
            edit_url = _program_edit_url(request, program)
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": edit_url})
            return redirect(edit_url)
    else:
        jobber_formset = ProgramJobberDetailFormSet(
            instance=program,
            prefix="jobbers",
            form_kwargs={"user": request.user},
        )

    template = "accounts/programs/form_embed.html" if _is_embed(request) else "accounts/programs/form.html"
    return render(
        request,
        template,
        {
            "form": form,
            "jobber_formset": jobber_formset,
            "mode": "edit",
            "program": program,
            "full_page": not _is_embed(request),
            "action_url": reverse("accounts:program_edit", args=[program.pk]),
            "sku_payloads": _program_sku_payloads(request.user),
            "jobber_defaults": _program_jobber_defaults(request.user),
        },
    )

@login_required
def program_list(request):
    q = (request.GET.get("q") or "").strip()

    programs = (
        Program.objects.filter(owner=request.user)
        .select_related("bom", "firm", "bom__brand", "bom__category", "bom__main_category", "bom__sub_category")
        .prefetch_related(
            Prefetch(
                "jobber_rows",
                queryset=ProgramJobberDetail.objects.select_related("jobber", "jobber_type").order_by("sort_order", "id"),
            ),
            Prefetch(
                "size_rows",
                queryset=ProgramSizeDetail.objects.order_by("sort_order", "id"),
            ),
            Prefetch(
                "bom__images",
                queryset=BOMImage.objects.order_by("sort_order", "id"),
            ),
        )
        .order_by("-created_at", "-id")
    )

    if q:
        programs = programs.filter(
            Q(program_no__icontains=q)
            | Q(bom__sku__icontains=q)
            | Q(bom__product_name__icontains=q)
            | Q(firm__firm_name__icontains=q)
        )

    verified_count = programs.filter(is_verified=True).count()
    unverified_count = programs.filter(is_verified=False).count()

    return render(
        request,
        "accounts/programs/list.html",
        {
            "programs": programs,
            "q": q,
            "verified_count": verified_count,
            "unverified_count": unverified_count,
        },
    )


@login_required
@require_POST
def program_toggle_verify(request, pk: int):
    program = get_object_or_404(Program, pk=pk, owner=request.user)
    program.is_verified = not program.is_verified
    program.save(update_fields=["is_verified"])
    messages.success(
        request,
        f"Program {'verified' if program.is_verified else 'marked unverified'} successfully."
    )
    return redirect("accounts:program_list")


@login_required
@require_POST
def program_toggle_status(request, pk: int):
    program = get_object_or_404(Program, pk=pk, owner=request.user)
    program.status = "closed" if program.status == "open" else "open"
    program.save(update_fields=["status"])
    messages.success(request, f"Program marked {program.status}.")
    return redirect("accounts:program_list")


@login_required
def program_print(request, pk: int):
    program = get_object_or_404(
        Program.objects.select_related("bom", "firm").prefetch_related(
            Prefetch(
                "jobber_rows",
                queryset=ProgramJobberDetail.objects.select_related("jobber", "jobber_type").order_by("sort_order", "id"),
            ),
            Prefetch(
                "size_rows",
                queryset=ProgramSizeDetail.objects.order_by("sort_order", "id"),
            ),
            Prefetch(
                "bom__images",
                queryset=BOMImage.objects.order_by("sort_order", "id"),
            ),
        ),
        pk=pk,
        owner=request.user,
    )
    return render(
        request,
        "accounts/programs/print.html",
        {
            "program": program,
        },
    )


def _dispatch_list_url(request):
    url = reverse("accounts:dispatch_list")
    if _is_embed(request):
        url += "?embed=1"
    return url


def _dispatch_feature_available() -> bool:
    return DispatchChallan is not None


def _dispatch_feature_unavailable_response(request):
    message = "Dispatch module is not available because DispatchChallan model/form is missing."
    if _is_embed(request):
        return JsonResponse({"ok": False, "message": message}, status=400)
    messages.error(request, message)
    return redirect("accounts:dashboard")


@login_required
def dispatch_list(request):
    if not _dispatch_feature_available():
        return _dispatch_feature_unavailable_response(request)

    q = (request.GET.get("q") or "").strip()

    challans = (
        DispatchChallan.objects.filter(owner=request.user)
        .select_related("program", "program__bom", "program__firm", "client", "firm")
        .order_by("-challan_date", "-id")
    )

    if q:
        challans = challans.filter(
            Q(challan_no__icontains=q)
            | Q(program__program_no__icontains=q)
            | Q(program__bom__sku__icontains=q)
            | Q(program__bom__product_name__icontains=q)
            | Q(client__name__icontains=q)
            | Q(lr_no__icontains=q)
            | Q(transport_name__icontains=q)
            | Q(vehicle_no__icontains=q)
            | Q(driver_name__icontains=q)
        )

    template = (
        "accounts/dispatch/list_embed.html"
        if _is_embed(request)
        else "accounts/dispatch/list.html"
    )
    return render(
        request,
        template,
        {
            "challans": challans,
            "q": q,
        },
    )


@login_required
def dispatch_program_picker(request):
    q = (request.GET.get("q") or "").strip()

    programs = (
        Program.objects.filter(owner=request.user)
        .select_related("bom", "firm")
        .annotate(challan_count=Count("dispatch_challans"))
        .order_by("-finishing_date", "-program_date", "-id")
    )

    if q:
        programs = programs.filter(
            Q(program_no__icontains=q)
            | Q(bom__sku__icontains=q)
            | Q(bom__product_name__icontains=q)
        )

    template = (
        "accounts/dispatch/program_picker_embed.html"
        if _is_embed(request)
        else "accounts/dispatch/program_picker.html"
    )
    return render(
        request,
        template,
        {
            "programs": programs,
            "q": q,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def dispatch_create(request, program_id: int):
    if not _dispatch_feature_available():
        return _dispatch_feature_unavailable_response(request)

    program = get_object_or_404(
        Program.objects.select_related("bom", "firm"),
        pk=program_id,
        owner=request.user,
    )

    challan = DispatchChallan(
        owner=request.user,
        program=program,
        firm=program.firm,
    )

    if request.method == "GET":
        challan.challan_no = DispatchChallan.next_challan_no(request.user)
        challan.challan_date = timezone.localdate()

    form = DispatchChallanForm(
        request.POST or None,
        instance=challan,
        user=request.user,
        program=program,
    )

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            challan = form.save(commit=False)
            challan.owner = request.user
            challan.program = program
            challan.firm = program.firm
            challan.save()

        messages.success(request, f"Dispatch challan {challan.challan_no} created successfully.")

        url = _dispatch_list_url(request)
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    template = (
        "accounts/dispatch/form_embed.html"
        if _is_embed(request)
        else "accounts/dispatch/form.html"
    )
    return render(
        request,
        template,
        {
            "form": form,
            "mode": "add",
            "program": program,
            "challan_obj": None,
        },
    )


@login_required
def dispatch_detail(request, pk: int):
    if not _dispatch_feature_available():
        return _dispatch_feature_unavailable_response(request)

    challan = get_object_or_404(
        DispatchChallan.objects.select_related("program", "program__bom", "program__firm", "client", "firm"),
        pk=pk,
        owner=request.user,
    )

    template = (
        "accounts/dispatch/detail_embed.html"
        if _is_embed(request)
        else "accounts/dispatch/detail.html"
    )
    return render(
        request,
        template,
        {
            "challan": challan,
            "program": challan.program,
        },
    )

def _build_dispatch_challan_pdf_response(challan):
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

    def fmt_qty(value):
        try:
            return f"{float(value or 0):,.2f}".rstrip("0").rstrip(".")
        except Exception:
            return text_or_dash(value)

    def join_parts(*parts):
        clean = [str(p).strip() for p in parts if str(p).strip()]
        return ", ".join(clean)

    def line_if(label, value):
        value = "" if value is None else str(value).strip()
        if not value:
            return ""
        return f"<b>{escape(label)}:</b> {escape(value)}"

    def resolve_logo_path():
        firm = challan.firm
        if firm and getattr(firm, "logo", None):
            try:
                logo_path = firm.logo.path
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
        "DispatchBase",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=10.5,
        textColor=ink,
        spaceAfter=0,
    )

    header_left_style = ParagraphStyle(
        "DispatchHeaderLeft",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8.4,
        leading=10.4,
        textColor=white,
        alignment=TA_LEFT,
    )

    header_title_style = ParagraphStyle(
        "DispatchHeaderTitle",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=16,
        textColor=brand_navy,
        alignment=TA_RIGHT,
    )

    header_meta_style = ParagraphStyle(
        "DispatchHeaderMeta",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8.3,
        leading=10.2,
        textColor=ink,
        alignment=TA_RIGHT,
    )

    section_head_left = ParagraphStyle(
        "DispatchSectionHeadLeft",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=white,
        alignment=TA_LEFT,
    )

    section_value_style = ParagraphStyle(
        "DispatchSectionValue",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8.2,
        leading=10.2,
        textColor=ink,
        alignment=TA_LEFT,
    )

    table_head_style = ParagraphStyle(
        "DispatchTableHead",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=7.8,
        leading=9.5,
        textColor=white,
        alignment=TA_CENTER,
    )

    item_style = ParagraphStyle(
        "DispatchItem",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8,
        leading=9.6,
        alignment=TA_LEFT,
    )

    centered_style = ParagraphStyle(
        "DispatchCentered",
        parent=base_style,
        fontName="Helvetica",
        fontSize=8,
        leading=9.6,
        alignment=TA_CENTER,
    )

    sign_style = ParagraphStyle(
        "DispatchSign",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=ink,
        alignment=TA_LEFT,
    )

    footer_note_style = ParagraphStyle(
        "DispatchFooterNote",
        parent=base_style,
        fontName="Helvetica-Bold",
        fontSize=7.6,
        leading=9.2,
        textColor=muted,
        alignment=TA_CENTER,
    )

    story = []

    program = challan.program
    bom = getattr(program, "bom", None)
    client = challan.client
    firm = challan.firm

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

    header_left_html = f"<font size='13'><b>{escape(firm_name)}</b></font>"
    if firm_type and firm_type != "-":
        header_left_html += f"<br/>{escape(firm_type)}"
    if firm_address:
        header_left_html += f"<br/>{escape(firm_address)}"
    if firm_contact_line:
        header_left_html += f"<br/>{firm_contact_line}"

    challan_date = challan.challan_date.strftime("%d-%m-%Y") if challan.challan_date else "-"
    finishing_date = program.finishing_date.strftime("%d-%m-%Y") if getattr(program, "finishing_date", None) else "-"
    program_date = program.program_date.strftime("%d-%m-%Y") if getattr(program, "program_date", None) else "-"

    right_meta_html = (
        f"<b>Challan No:</b> {escape(text_or_dash(challan.challan_no))}<br/>"
        f"<b>Challan Date:</b> {escape(challan_date)}<br/>"
        f"<b>Program No:</b> {escape(text_or_dash(getattr(program, 'program_no', '')))}<br/>"
        f"<b>Program Date:</b> {escape(program_date)}<br/>"
        f"<b>Finishing Date:</b> {escape(finishing_date)}"
    )

    header_table = Table(
        [[
            Paragraph(header_left_html, header_left_style),
            Table(
                [
                    [Paragraph("DISPATCH CHALLAN", header_title_style)],
                    [Paragraph(right_meta_html, header_meta_style)],
                ],
                colWidths=[68 * mm],
            ),
        ]],
        colWidths=[122 * mm, 68 * mm],
    )
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), brand_navy),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F4F8FF")),
        ("BOX", (0, 0), (-1, -1), 0.9, border),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 10),
        ("RIGHTPADDING", (0, 0), (0, 0), 10),
        ("TOPPADDING", (0, 0), (0, 0), 10),
        ("BOTTOMPADDING", (0, 0), (0, 0), 10),
        ("LEFTPADDING", (1, 0), (1, 0), 0),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("TOPPADDING", (1, 0), (1, 0), 0),
        ("BOTTOMPADDING", (1, 0), (1, 0), 0),
    ]))
    inner_header = header_table._cellvalues[0][1]
    inner_header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F8FF")),
        ("BOX", (0, 0), (-1, -1), 1.0, brand_blue),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 7))

    client_html = f"<b>{escape(text_or_dash(client.name if client else ''))}</b>"
    client_lines = [
        line_if("Contact", getattr(client, "contact_person", "")),
        line_if("Phone", getattr(client, "phone", "")),
        line_if("Email", getattr(client, "email", "")),
        line_if("GSTIN", getattr(client, "gst_number", "")),
        line_if("Address", getattr(client, "address", "")),
    ]
    client_body = "<br/>".join([line for line in client_lines if line])
    if client_body:
        client_html += "<br/>" + client_body

    program_html = (
        f"<b>{escape(text_or_dash(getattr(program, 'program_no', '')))}</b><br/>"
        f"<b>SKU:</b> {escape(text_or_dash(getattr(bom, 'sku', '')))}<br/>"
        f"<b>Product:</b> {escape(text_or_dash(getattr(bom, 'product_name', '')))}<br/>"
        f"<b>Program Date:</b> {escape(program_date)}<br/>"
        f"<b>Finishing Date:</b> {escape(finishing_date)}<br/>"
        f"<b>Total Qty:</b> {escape(fmt_qty(getattr(program, 'total_qty', 0)))}"
    )

    party_table = Table(
        [
            [
                Paragraph("CLIENT DETAILS", section_head_left),
                Paragraph("PROGRAM DETAILS", section_head_left),
            ],
            [
                Paragraph(client_html, section_value_style),
                Paragraph(program_html, section_value_style),
            ],
        ],
        colWidths=[92 * mm, 98 * mm],
    )
    party_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), brand_orange),
        ("BACKGROUND", (1, 0), (1, 0), brand_blue),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("BACKGROUND", (0, 1), (0, 1), colors.HexColor("#FFF9F3")),
        ("BACKGROUND", (1, 1), (1, 1), colors.HexColor("#F5F9FF")),
        ("BOX", (0, 0), (-1, -1), 0.9, border),
        ("INNERGRID", (0, 0), (-1, -1), 0.65, border),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(party_table)
    story.append(Spacer(1, 8))

    challan_rows = [
        [
            Paragraph("Driver Name", table_head_style),
            Paragraph("LR No", table_head_style),
            Paragraph("Transport", table_head_style),
            Paragraph("Vehicle No", table_head_style),
        ],
        [
            Paragraph(escape(text_or_dash(challan.driver_name)), item_style),
            Paragraph(escape(text_or_dash(challan.lr_no)), centered_style),
            Paragraph(escape(text_or_dash(challan.transport_name)), item_style),
            Paragraph(escape(text_or_dash(challan.vehicle_no)), centered_style),
        ],
    ]

    challan_table = Table(challan_rows, colWidths=[52 * mm, 32 * mm, 66 * mm, 40 * mm])
    challan_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), brand_navy),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.9, border),
        ("INNERGRID", (0, 0), (-1, -1), 0.55, border),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(challan_table)
    story.append(Spacer(1, 10))

    remarks_html = escape(text_or_dash(challan.remarks)).replace("\n", "<br/>")
    remarks_table = Table(
        [
            [Paragraph("REMARKS", section_head_left)],
            [Paragraph(remarks_html, section_value_style)],
        ],
        colWidths=[190 * mm],
    )
    remarks_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), brand_pink),
        ("TEXTCOLOR", (0, 0), (0, 0), white),
        ("BACKGROUND", (0, 1), (0, 1), soft_bg),
        ("BOX", (0, 0), (-1, -1), 0.9, border),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(remarks_table)
    story.append(Spacer(1, 12))

    sign_table = Table(
        [[
            Paragraph("<b>RECEIVER SIGNATURE</b><br/><br/>______________________________", sign_style),
            Paragraph("<b>FOR " + escape(firm_name.upper()) + "</b><br/><br/>______________________________", sign_style),
        ]],
        colWidths=[95 * mm, 95 * mm],
    )
    sign_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(sign_table)
    story.append(Spacer(1, 10))

    footer_table = Table(
        [[Paragraph("THIS CHALLAN IS COMPUTER GENERATED, HENCE SIGNATURE IS NOT REQUIRED", footer_note_style)]],
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
    return response

@login_required
def dispatch_print(request, pk: int):
    if not _dispatch_feature_available():
        return _dispatch_feature_unavailable_response(request)

    challan = get_object_or_404(
        DispatchChallan.objects.select_related(
            "program",
            "program__bom",
            "program__firm",
            "client",
            "firm",
        ),
        pk=pk,
        owner=request.user,
    )

    response = _build_dispatch_challan_pdf_response(challan)

    if response.status_code == 200 and response.get("Content-Type", "").startswith("application/pdf"):
        filename = f'{challan.challan_no or "dispatch_challan"}.pdf'
        disposition = "attachment" if request.GET.get("download") == "1" else "inline"
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        response["Cache-Control"] = "no-store"
        response["X-Content-Type-Options"] = "nosniff"
        try:
            response["Content-Length"] = str(len(response.content))
        except Exception:
            pass

    return response


def _dyeing_material_link_list_url(request):
    url = reverse("accounts:dyeing_material_link_list")
    if _is_embed(request):
        url += "?embed=1"
    return url


@login_required
def dyeing_material_link_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = (
        DyeingMaterialLink.objects
        .filter(owner=request.user)
        .select_related("vendor", "material_type", "material")
        .prefetch_related("details")
        .order_by("vendor__name", "material__name")
    )

    if q:
        qs = qs.filter(
            Q(vendor__name__icontains=q)
            | Q(material_type__name__icontains=q)
            | Q(material__name__icontains=q)
            | Q(details__dyeing_name__icontains=q)
            | Q(details__dyeing_type__icontains=q)
        ).distinct()

    context = {
        "links": qs,
        "q": q,
    }

    template = (
        "accounts/dyeing_material_links/list_embed.html"
        if _is_embed(request)
        else "accounts/dyeing_material_links/list.html"
    )
    return render(request, template, context)


@login_required
@require_http_methods(["GET", "POST"])
def dyeing_material_link_create(request):
    link = DyeingMaterialLink(owner=request.user)

    form = DyeingMaterialLinkForm(
        request.POST or None,
        instance=link,
        user=request.user,
    )
    formset = DyeingMaterialLinkDetailFormSet(
        request.POST or None,
        instance=link,
        prefix="details",
    )

    if request.method == "POST":
        if form.is_valid() and formset.is_valid():
            non_deleted_forms = [
                f for f in formset.forms
                if f.cleaned_data and not f.cleaned_data.get("DELETE", False)
            ]
            if not non_deleted_forms:
                form.add_error(None, "Add at least one dyeing detail row.")
            else:
                obj = form.save(commit=False)
                obj.owner = request.user
                obj.save()

                formset.instance = obj
                formset.save()

                url = _dyeing_material_link_list_url(request)
                if _is_embed(request):
                    return JsonResponse({"ok": True, "url": url})
                return redirect(url)

    template = (
        "accounts/dyeing_material_links/form_embed.html"
        if _is_embed(request)
        else "accounts/dyeing_material_links/form.html"
    )
    return render(request, template, {
        "form": form,
        "formset": formset,
        "mode": "add",
    })
    
    
@login_required
@require_http_methods(["GET", "POST"])
def dyeing_material_link_update(request, pk: int):
    obj = get_object_or_404(
        DyeingMaterialLink.objects.prefetch_related("details"),
        pk=pk,
        owner=request.user,
    )

    form = DyeingMaterialLinkForm(
        request.POST or None,
        instance=obj,
        user=request.user,
    )
    formset = DyeingMaterialLinkDetailFormSet(
        request.POST or None,
        instance=obj,
        prefix="details",
    )

    if request.method == "POST":
        if form.is_valid() and formset.is_valid():
            non_deleted_forms = [
                f for f in formset.forms
                if f.cleaned_data and not f.cleaned_data.get("DELETE", False)
            ]
            if not non_deleted_forms:
                form.add_error(None, "Add at least one dyeing detail row.")
            else:
                form.save()
                formset.save()

                url = _dyeing_material_link_list_url(request)
                if _is_embed(request):
                    return JsonResponse({"ok": True, "url": url})
                return redirect(url)

    template = (
        "accounts/dyeing_material_links/form_embed.html"
        if _is_embed(request)
        else "accounts/dyeing_material_links/form.html"
    )
    return render(request, template, {
        "form": form,
        "formset": formset,
        "mode": "edit",
        "link_obj": obj,
    })
    
@login_required
@require_POST
def dyeing_material_link_delete(request, pk: int):
    obj = get_object_or_404(DyeingMaterialLink, pk=pk, owner=request.user)
    obj.delete()

    url = _dyeing_material_link_list_url(request)
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)