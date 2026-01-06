from datetime import timedelta

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

from .forms import JobberForm, JobberTypeForm, LocationForm, MaterialForm, PartyForm
from .models import Jobber, JobberType, Location, Material, Party, UserExtra

from .models import Firm, MaterialShade, MaterialType, Material
from .forms import FirmForm, MaterialShadeForm, MaterialTypeForm


def _is_embed(request) -> bool:
    return (
        request.GET.get("embed") == "1"
        or request.POST.get("embed") == "1"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
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
    qs = Jobber.objects.filter(owner=request.user)

    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(phone__icontains=q)
            | Q(email__icontains=q)
            | Q(role__icontains=q)
            | Q(jobber_type__name__icontains=q)
        )

    qs = qs.order_by("name")
    template = "accounts/jobbers/embed_list.html" if _is_embed(request) else "accounts/jobbers/list.html"
    return render(request, template, {"jobbers": qs, "q": q})


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
    types = JobberType.objects.filter(owner=request.user).order_by("name")

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

    template = "accounts/jobbers/embed_types.html" if _is_embed(request) else "accounts/jobbers/types.html"
    return render(request, template, {"types": types, "form": form})


# ==========================
# MATERIALS (embed supported)
# ==========================
@login_required
def material_list(request):
    q = (request.GET.get("q") or "").strip()
    selected_type = (request.GET.get("type") or "").strip()

    qs = Material.objects.all().order_by("-id").select_related("yarn", "greige", "finished", "trim")

    if selected_type:
        if selected_type.isdigit():
            qs = qs.filter(material_type_id=int(selected_type))


    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(remarks__icontains=q)
            | Q(yarn__yarn_type__icontains=q)
            | Q(greige__fabric_type__icontains=q)
            | Q(finished__base_fabric_type__icontains=q)
            | Q(trim__trim_type__icontains=q)
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
@require_http_methods(["GET", "POST"])
def material_create(request):
    if request.method == "POST":
        form = MaterialForm(request.POST, request.FILES, user=request.user)


        if form.is_valid():
            form.save()
            url = reverse("accounts:material_list")
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)
    else:
        form = MaterialForm(user=request.user)


    ctx = {"form": form, "mode": "create"}
    tpl = "accounts/materials/form_embed.html" if _is_embed(request) else "accounts/materials/form_page.html"
    return render(request, tpl, ctx)

@login_required
@require_http_methods(["GET", "POST"])
def material_edit(request, pk: int):
    material = get_object_or_404(Material.objects.select_related("yarn", "greige", "finished", "trim"), pk=pk)

    if request.method == "POST":
        form = MaterialForm(request.POST, request.FILES, instance=material, user=request.user)

        if form.is_valid():
            form.save()
            url = reverse("accounts:material_list")
            if _is_embed(request):
                return JsonResponse({"ok": True, "url": url})
            return redirect(url)
    else:
        form = MaterialForm(instance=material, user=request.user)



    ctx = {"form": form, "mode": "edit", "material": material}
    tpl = "accounts/materials/form_embed.html" if _is_embed(request) else "accounts/materials/form_page.html"
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
        # ✅ IMPORTANT: set owner before validation so unique_together(owner, name) is checked safely
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
    # OneToOne => 0 or 1 row, but list UI stays consistent
    firm = Firm.objects.filter(owner=request.user).first()
    firms = [firm] if firm else []

    tpl = "accounts/firms/list_embed.html" if _is_embed(request) else "accounts/firms/list.html"
    return render(request, tpl, {"firms": firms})


@login_required
@require_http_methods(["GET", "POST"])
def firm_create(request):
    existing = Firm.objects.filter(owner=request.user).first()

    # ✅ If firm already exists, open Edit page instead of returning JSON
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
        firm = Firm(owner=request.user)  # important for first save

    form = FirmForm(request.POST or None, instance=firm)

    if request.method == "POST" and form.is_valid():
        form.save()  # owner already set on instance above

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

    qs = MaterialShade.objects.filter(owner=request.user).order_by("name")
    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(code__icontains=q) |
            Q(notes__icontains=q)
        )

    ctx = {"shades": qs, "q": q}
    tpl = "accounts/material_shades/list_embed.html" if _is_embed(request) else "accounts/material_shades/list.html"
    return render(request, tpl, ctx)


@login_required
@require_http_methods(["GET", "POST"])
def materialshade_create(request):
    form = MaterialShadeForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user  # ✅ REQUIRED (owner is mandatory)
        obj.save()

        url = reverse("accounts:materialshade_list")
        if _is_embed(request):
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
        form.save()
        url = reverse("accounts:materialshade_list")
        if _is_embed(request):
            return JsonResponse({"ok": True, "url": url})
        return redirect(url)

    tpl = "accounts/material_shades/form_embed.html" if _is_embed(request) else "accounts/material_shades/form.html"
    return render(request, tpl, {"form": form, "mode": "edit", "shade": shade})


@login_required
@require_POST
def materialshade_delete(request, pk: int):
    shade = get_object_or_404(MaterialShade, pk=pk, owner=request.user)
    shade.delete()

    url = reverse("accounts:materialshade_list")
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)


# ==========================
# MATERIAL TYPES (Utilities)
# ==========================
@login_required
def materialtype_list(request):
    q = (request.GET.get("q") or "").strip()

    qs = MaterialType.objects.filter(owner=request.user).order_by("name")
    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q)
        )

    ctx = {"types": qs, "q": q}
    tpl = "accounts/material_types/list_embed.html" if _is_embed(request) else "accounts/material_types/list.html"
    return render(request, tpl, ctx)


@login_required
@require_http_methods(["GET", "POST"])
def materialtype_create(request):
    form = MaterialTypeForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user  # ✅ REQUIRED (owner is mandatory)
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
        form.save()
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

    # (Optional) block delete if used by Material (enable after your FK is final)
    # if Material.objects.filter(material_type=mt).exists():
    #     if _is_embed(request):
    #         return JsonResponse({"ok": False, "error": "Cannot delete: type is in use."}, status=400)
    #     messages.error(request, "Cannot delete: type is in use.")
    #     return redirect("accounts:materialtype_list")

    mt.delete()

    url = reverse("accounts:materialtype_list")
    if _is_embed(request):
        return JsonResponse({"ok": True, "url": url})
    return redirect(url)
