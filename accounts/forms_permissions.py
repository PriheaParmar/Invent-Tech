from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.utils.text import slugify

from .models import ERPCompany, ERPRole, ERPUserProfile, Firm
from .permissions import ALL_PERMISSION_CODES, PERMISSION_GROUPS, ROLE_FORBIDDEN_PERMISSION_CODES


class ERPCompanyForm(forms.ModelForm):
    admin_username = forms.CharField(max_length=150)
    admin_email = forms.EmailField(required=False)
    admin_password = forms.CharField(widget=forms.PasswordInput, required=False)
    admin_password_confirm = forms.CharField(widget=forms.PasswordInput, required=False)

    class Meta:
        model = ERPCompany
        fields = [
            "name",
            "slug",
            "contact_person",
            "phone",
            "email",
            "status",
            "subscription_start",
            "subscription_end",
            "notes",
        ]
        widgets = {
            "subscription_start": forms.DateInput(attrs={"type": "date"}),
            "subscription_end": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.instance_obj = kwargs.get("instance")
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "perm-input")

        if self.instance and self.instance.pk:
            self.fields["admin_username"].initial = self.instance.admin_user.username
            self.fields["admin_email"].initial = self.instance.admin_user.email
            self.fields["admin_password"].help_text = "Leave blank to keep current password."
            self.fields["admin_password_confirm"].help_text = "Leave blank to keep current password."
        else:
            self.fields["admin_password"].required = True
            self.fields["admin_password_confirm"].required = True

    def clean_slug(self):
        slug = slugify(self.cleaned_data.get("slug") or self.cleaned_data.get("name") or "")
        if not slug:
            raise forms.ValidationError("Slug is required.")
        qs = ERPCompany.objects.filter(slug=slug)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This company slug already exists.")
        return slug

    def clean_admin_username(self):
        username = (self.cleaned_data.get("admin_username") or "").strip()
        if not username:
            raise forms.ValidationError("Admin username is required.")
        qs = User.objects.filter(username__iexact=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.admin_user_id)
        if qs.exists():
            raise forms.ValidationError("This username is already used.")
        return username

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("admin_password") or ""
        confirm = cleaned.get("admin_password_confirm") or ""

        if password or confirm or not (self.instance and self.instance.pk):
            if password != confirm:
                self.add_error("admin_password_confirm", "Passwords do not match.")
            if password:
                try:
                    validate_password(password)
                except forms.ValidationError as exc:
                    self.add_error("admin_password", exc)
        return cleaned

    def save(self, commit=True):
        company = super().save(commit=False)
        username = self.cleaned_data["admin_username"]
        email = self.cleaned_data.get("admin_email") or self.cleaned_data.get("email") or ""
        password = self.cleaned_data.get("admin_password") or ""

        if self.instance and self.instance.pk:
            admin_user = self.instance.admin_user
            admin_user.username = username
            admin_user.email = email
            if password:
                admin_user.set_password(password)
        else:
            admin_user = User(username=username, email=email, is_staff=False, is_superuser=False)
            admin_user.set_password(password)

        if commit:
            admin_user.save()
            company.admin_user = admin_user
            company.save()

            ERPUserProfile.objects.update_or_create(
                user=admin_user,
                defaults={
                    "company": company,
                    "user_type": ERPUserProfile.USER_TYPE_COMPANY_ADMIN,
                    "is_active": True,
                },
            )
        else:
            company.admin_user = admin_user

        return company


class ERPRoleForm(forms.ModelForm):
    permission_choices = forms.MultipleChoiceField(
        required=False,
        choices=[],
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = ERPRole
        fields = ["name", "description", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)
        self.fields["permission_choices"].choices = [
            (code, label)
            for group in PERMISSION_GROUPS.values()
            for code, label in group
            if code not in ROLE_FORBIDDEN_PERMISSION_CODES
        ]
        self.fields["permission_choices"].initial = [
            code
            for code in (self.instance.permissions if self.instance and self.instance.pk else [])
            if code not in ROLE_FORBIDDEN_PERMISSION_CODES
        ]
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs.setdefault("class", "perm-input")

    def clean_permission_choices(self):
        permissions = self.cleaned_data.get("permission_choices") or []
        return [
            code
            for code in permissions
            if code in ALL_PERMISSION_CODES and code not in ROLE_FORBIDDEN_PERMISSION_CODES
        ]

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.company is not None:
            obj.company = self.company
        obj.permissions = self.cleaned_data.get("permission_choices") or []
        if commit:
            obj.save()
        return obj


class TeamUserForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    email = forms.EmailField(required=False)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    password_confirm = forms.CharField(widget=forms.PasswordInput, required=False)
    allowed_firms = forms.ModelMultipleChoiceField(
        queryset=Firm.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = ERPUserProfile
        fields = ["role", "phone", "designation", "department", "is_active", "allowed_firms"]

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop("company")
        self.owner = self.company.admin_user
        self.user_instance = kwargs.pop("user_instance", None)
        super().__init__(*args, **kwargs)

        self.fields["role"].queryset = ERPRole.objects.filter(company=self.company, is_active=True).order_by("name")
        self.fields["allowed_firms"].queryset = Firm.objects.filter(owner=self.owner).order_by("firm_name")

        if self.user_instance:
            self.fields["username"].initial = self.user_instance.username
            self.fields["email"].initial = self.user_instance.email
            self.fields["first_name"].initial = self.user_instance.first_name
            self.fields["last_name"].initial = self.user_instance.last_name
            self.fields["password"].help_text = "Leave blank to keep current password."
            self.fields["password_confirm"].help_text = "Leave blank to keep current password."

        if self.instance and self.instance.pk:
            self.fields["allowed_firms"].initial = self.instance.allowed_firms.all()

        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs.setdefault("class", "perm-input")

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise forms.ValidationError("Username is required.")
        qs = User.objects.filter(username__iexact=username)
        if self.user_instance:
            qs = qs.exclude(pk=self.user_instance.pk)
        if qs.exists():
            raise forms.ValidationError("This username is already used.")
        return username

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password") or ""
        confirm = cleaned.get("password_confirm") or ""

        if not self.user_instance and not password:
            self.add_error("password", "Password is required for a new user.")

        if password or confirm:
            if password != confirm:
                self.add_error("password_confirm", "Passwords do not match.")
            if password:
                try:
                    validate_password(password)
                except forms.ValidationError as exc:
                    self.add_error("password", exc)

        return cleaned

    def save(self, commit=True):
        if self.user_instance:
            user = self.user_instance
        else:
            user = User(is_staff=False, is_superuser=False)

        user.username = self.cleaned_data["username"]
        user.email = self.cleaned_data.get("email") or ""
        user.first_name = self.cleaned_data.get("first_name") or ""
        user.last_name = self.cleaned_data.get("last_name") or ""

        password = self.cleaned_data.get("password") or ""
        if password:
            user.set_password(password)

        if commit:
            user.save()

        profile = super().save(commit=False)
        profile.user = user
        profile.company = self.company
        profile.user_type = ERPUserProfile.USER_TYPE_STAFF

        if commit:
            profile.save()
            profile.allowed_firms.set(self.cleaned_data.get("allowed_firms") or [])
        return profile
