from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST, require_http_methods

from .forms import JobberForm, JobberTypeForm
from .models import Jobber, JobberType, UserExtra

from .models import Material
from .forms import MaterialForm

def _is_embed(request) -> bool:
    return request.GET.get("embed") == "1" or request.headers.get("X-Requested-With") == "XMLHttpRequest"

def is_embed(request):
    return request.GET.get("embed") == "1" or request.POST.get("embed") == "1"


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
                request.session.set_expiry(60 * 60 * 24 * 14)  # 14 days
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
    return render(request, "accounts/dashboard.html")


@login_required
def utilities_view(request):
    return render(request, "accounts/utilities.html")


@login_required
def users_list_view(request):
    q = (request.GET.get("q") or "").strip()

    qs = User.objects.select_related("userextra").all().order_by("-date_joined")

    if q:
        qs = qs.filter(
            Q(username__icontains=q) |
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(userextra__phone__icontains=q) |
            Q(userextra__designation__icontains=q)
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

    return render(request, "accounts/developer_stats.html", {
        "total_users": total_users,
        "new_today": new_today,
        "new_7_days": new_7_days,
        "active_24h": active_24h,
        "active_7d": active_7d,
    })


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
    q = request.GET.get("q", "").strip()
    qs = Jobber.objects.filter(owner=request.user)

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(phone__icontains=q) |
            Q(email__icontains=q) |
            Q(role__icontains=q) |
            Q(jobber_type__name__icontains=q)
        )

    qs = qs.order_by("name")

    template = "accounts/jobbers/embed_list.html" if _is_embed(request) else "accounts/jobbers/list.html"
    return render(request, template, {"jobbers": qs, "q": q})


@login_required
def jobber_create(request):
    form = JobberForm(request.POST or None)
    if "jobber_type" in form.fields:
        form.fields["jobber_type"].queryset = JobberType.objects.filter(owner=request.user)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()

        if _is_embed(request):
            return JsonResponse({"ok": True, "url": reverse("accounts:jobber_list")})
        return redirect("accounts:jobber_list")

    template = "accounts/jobbers/embed_form.html" if _is_embed(request) else "accounts/jobbers/form.html"
    return render(request, template, {"form": form, "mode": "add"})


@login_required
def jobber_update(request, pk):
    jobber = get_object_or_404(Jobber, pk=pk, owner=request.user)
    form = JobberForm(request.POST or None, instance=jobber)
    if "jobber_type" in form.fields:
        form.fields["jobber_type"].queryset = JobberType.objects.filter(owner=request.user)

    if request.method == "POST" and form.is_valid():
        form.save()

        if _is_embed(request):
            return JsonResponse({"ok": True, "url": reverse("accounts:jobber_list")})
        return redirect("accounts:jobber_list")

    template = "accounts/jobbers/embed_form.html" if _is_embed(request) else "accounts/jobbers/form.html"
    return render(request, template, {"form": form, "mode": "edit", "jobber": jobber})


@login_required
def jobber_delete(request, pk):
    jobber = get_object_or_404(Jobber, pk=pk, owner=request.user)

    if request.method == "POST":
        jobber.delete()

        if _is_embed(request):
            return JsonResponse({"ok": True, "url": reverse("accounts:jobber_list")})
        return redirect("accounts:jobber_list")

    template = "accounts/jobbers/embed_confirm_delete.html" if _is_embed(request) else "accounts/jobbers/confirm_delete.html"
    return render(request, template, {"jobber": jobber})


@login_required
def jobbertype_list_create(request):
    types = JobberType.objects.filter(owner=request.user).order_by("name")

    if request.method == "POST":
        form = JobberTypeForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()

            if _is_embed(request):
                return JsonResponse({"ok": True, "url": reverse("accounts:jobbertype_list")})
            return redirect("accounts:jobbertype_list")
    else:
        form = JobberTypeForm()

    template = "accounts/jobbers/embed_types.html" if _is_embed(request) else "accounts/jobbers/types.html"
    return render(request, template, {"types": types, "form": form})

@login_required
def jobber_create(request):
    embed = (request.GET.get("embed") == "1") or (request.POST.get("embed") == "1")
    tpl = "accounts/jobbers/embed_form.html" if embed else "accounts/jobbers/form.html"

    if request.method == "POST":
        form = JobberForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()

            if embed:
                return JsonResponse({"ok": True, "url": reverse("accounts:jobber_list") + "?embed=1"})
            return redirect("accounts:jobber_list")
    else:
        form = JobberForm()

    return render(request, tpl, {"form": form, "mode": "add"})


@login_required
def jobber_update(request, pk):
    jobber = get_object_or_404(Jobber, pk=pk, owner=request.user)
    embed = (request.GET.get("embed") == "1") or (request.POST.get("embed") == "1")
    tpl = "accounts/jobbers/embed_form.html" if embed else "accounts/jobbers/form.html"

    if request.method == "POST":
        form = JobberForm(request.POST, instance=jobber)
        if form.is_valid():
            form.save()

            if embed:
                return JsonResponse({"ok": True, "url": reverse("accounts:jobber_list") + "?embed=1"})
            return redirect("accounts:jobber_list")
    else:
        form = JobberForm(instance=jobber)

    return render(request, tpl, {"form": form, "mode": "edit", "jobber": jobber})

def _is_embed(request):
    return request.GET.get("embed") == "1"


def _wants_json(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"
def _is_embed(request) -> bool:
    return request.GET.get("embed") == "1"


def material_list(request):
    q = (request.GET.get("q") or "").strip()
    material_type = (request.GET.get("type") or "").strip()

    qs = Material.objects.all().order_by("-id").select_related("yarn", "greige", "finished", "trim")

    if material_type:
        qs = qs.filter(material_type=material_type)

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(remarks__icontains=q) |
            Q(yarn__yarn_type__icontains=q) |
            Q(greige__fabric_type__icontains=q) |
            Q(finished__base_fabric_type__icontains=q) |
            Q(trim__trim_type__icontains=q)
        )

    ctx = {"materials": qs, "q": q, "type": material_type}

    tpl = "accounts/materials/list_embed.html" if _is_embed(request) else "accounts/materials/list_page.html"
    return render(request, tpl, ctx)


def material_create(request):
    if request.method == "POST":
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            url = reverse("accounts:material_list")
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)
    else:
        form = MaterialForm()

    ctx = {"form": form, "mode": "create"}
    tpl = "accounts/materials/form_embed.html" if _is_embed(request) else "accounts/materials/form_page.html"
    return render(request, tpl, ctx)


def material_edit(request, pk: int):
    material = get_object_or_404(Material.objects.select_related("yarn", "greige", "finished", "trim"), pk=pk)

    if request.method == "POST":
        form = MaterialForm(request.POST, request.FILES, instance=material)
        if form.is_valid():
            form.save()
            url = reverse("accounts:material_list")
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)
    else:
        form = MaterialForm(instance=material)

    ctx = {"form": form, "mode": "edit", "material": material}
    tpl = "accounts/materials/form_embed.html" if _is_embed(request) else "accounts/materials/form_page.html"
    return render(request, tpl, ctx)


@require_POST
def material_delete(request, pk: int):
    material = get_object_or_404(Material, pk=pk)
    material.delete()
    url = reverse("accounts:material_list")
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)