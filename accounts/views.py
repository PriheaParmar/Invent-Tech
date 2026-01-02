from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

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
            return redirect("dashboard")

    return render(request, "accounts/signup.html", {"error": error})


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    error = None

    if request.method == "POST":
        identifier = request.POST.get("username", "").strip()  # username OR email
        password = request.POST.get("password", "")
        remember_me = request.POST.get("remember_me")

        # If user enters email, convert it to username
        username = identifier
        if "@" in identifier:
            user_obj = User.objects.filter(email__iexact=identifier).first()
            if user_obj:
                username = user_obj.username
            else:
                username = None

        user = None
        if username:
            user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Remember me = keep session longer
            if remember_me:
                request.session.set_expiry(60 * 60 * 24 * 14)  # 14 days
            else:
                request.session.set_expiry(0)  # until browser closes

            return redirect("dashboard")

        error = "Invalid username/email or password."

    return render(request, "accounts/login.html", {"error": error})


@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard_view(request):
    return render(request, "accounts/dashboard.html")

@login_required
def utilities_view(request):
    return render(request, "accounts/utilities.html")
