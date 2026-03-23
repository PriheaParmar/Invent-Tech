from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

import re

from .models import (
    Jobber,
    JobberType,
    Material,
    YarnDetail,
    GreigeDetail,
    FinishedDetail,
    TrimDetail,
    Party,
    Location,
    Firm,
    MaterialShade,
    MaterialType,
)

# ============================================================
# JOBBERS
# ============================================================

class JobberForm(forms.ModelForm):
    class Meta:
        model = Jobber
        fields = ["name", "phone", "email", "role", "jobber_type", "address", "is_active"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }


class JobberTypeForm(forms.ModelForm):
    class Meta:
        model = JobberType
        fields = ["name"]


# ============================================================
# AUTH
# ============================================================

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].widget.attrs.update({
            "class": "input",
            "placeholder": "Enter your username",
            "autocomplete": "username",
        })
        self.fields["email"].widget.attrs.update({
            "class": "input",
            "placeholder": "Enter your email",
            "autocomplete": "email",
        })

        self.fields["password1"].widget = forms.PasswordInput(
            render_value=True,
            attrs={
                "class": "input",
                "placeholder": "Create a password",
                "autocomplete": "new-password",
            },
        )
        self.fields["password2"].widget = forms.PasswordInput(
            render_value=True,
            attrs={
                "class": "input",
                "placeholder": "Confirm password",
                "autocomplete": "new-password",
            },
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email already registered.")

        return email

    def clean_password1(self):
        password = self.cleaned_data.get("password1", "")

        if not re.search(r"\d", password):
            raise forms.ValidationError("Password must contain at least 1 number.")

        if not re.search(r"[^A-Za-z0-9]", password):
            raise forms.ValidationError("Password must contain at least 1 special character.")

        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


# ============================================================
# MATERIALS (UPDATED for MaterialType FK)
# ============================================================
# ============================================================
# MATERIAL FORM (Step-1 Kind → Step-2 Type master → Step-3 Shade master)
# ============================================================
class MaterialForm(forms.Form):
    material_kind = forms.ChoiceField(
        choices=Material.MATERIAL_KIND_CHOICES,
        label="Material Kind",
        error_messages={"required": "Please select Material Kind."},
    )
    material_type = forms.ModelChoiceField(
        queryset=MaterialType.objects.none(),
        required=False,
        empty_label="Select"
    )
    material_shade = forms.ModelChoiceField(
        queryset=MaterialShade.objects.none(),
        required=False,
        empty_label="Select"
    )

    # common
    name = forms.CharField(
        max_length=150,
        label="Material Name",
        error_messages={"required": "Please enter Material Name."},
    )
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    image = forms.ImageField(required=False)

    # Yarn
    yarn_type = forms.CharField(required=False, max_length=80, label="Yarn Type")
    yarn_subtype = forms.CharField(required=False, max_length=80, label="Yarn Subtype")
    count_denier = forms.CharField(required=False, max_length=40, label="Count / Denier")
    yarn_color = forms.CharField(required=False, max_length=60, label="Color")

    # Greige
    fabric_type = forms.CharField(required=False, max_length=120, label="Fabric Type")
    gsm = forms.DecimalField(required=False, max_digits=8, decimal_places=2, label="GSM")
    width = forms.DecimalField(required=False, max_digits=8, decimal_places=2, label="Width")
    construction = forms.CharField(required=False, max_length=120, label="Construction")

    # Finished
    base_fabric_type = forms.CharField(required=False, max_length=120, label="Base Fabric Type")
    finish_type = forms.ChoiceField(required=False, choices=[("", "Select")] + list(FinishedDetail.FinishType.choices))
    finished_gsm = forms.DecimalField(required=False, max_digits=8, decimal_places=2, label="GSM")
    finished_width = forms.DecimalField(required=False, max_digits=8, decimal_places=2, label="Width")
    end_use = forms.CharField(required=False, max_length=120, label="End Use")

    # Trim
    trim_type = forms.ChoiceField(required=False, choices=[("", "Select")] + list(TrimDetail.TRIM_TYPE_CHOICES))
    trim_size = forms.CharField(required=False, max_length=60, label="Size")
    trim_color = forms.CharField(required=False, max_length=60, label="Color")
    brand = forms.CharField(required=False, max_length=80, label="Brand (optional)")

    def __init__(self, *args, instance=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance

        kind = (self.data.get("material_kind") or "").strip()
        if not kind and instance:
            kind = (getattr(instance, "material_kind", "") or "").strip()

        type_qs = MaterialType.objects.all()
        if user is not None:
            type_qs = type_qs.filter(owner=user)
        if kind:
            type_qs = type_qs.filter(material_kind=kind)
        type_qs = type_qs.order_by("name")

        shade_qs = MaterialShade.objects.all()
        if user is not None:
            shade_qs = shade_qs.filter(owner=user)
        if kind:
            shade_qs = shade_qs.filter(material_kind=kind)
        shade_qs = shade_qs.order_by("name")

        self.fields["material_type"].queryset = type_qs
        self.fields["material_shade"].queryset = shade_qs

        self.fields["material_type"].label_from_instance = lambda o: f"{o.get_material_kind_display()} — {o.name}"
        self.fields["material_shade"].label_from_instance = lambda o: f"{o.get_material_kind_display()} — {o.name}"

        # ✅ Prefill edit form values
        if instance and not self.is_bound:
            self.initial.update({
                "material_kind": instance.material_kind,
                "material_type": instance.material_type,
                "material_shade": instance.material_shade,
                "name": instance.name,
                "remarks": instance.remarks,
            })

            if instance.material_kind == "yarn" and hasattr(instance, "yarn"):
                self.initial.update({
                    "yarn_type": instance.yarn.yarn_type,
                    "yarn_subtype": instance.yarn.yarn_subtype,
                    "count_denier": instance.yarn.count_denier,
                    "yarn_color": instance.yarn.color,
                })

            elif instance.material_kind == "greige" and hasattr(instance, "greige"):
                self.initial.update({
                    "fabric_type": instance.greige.fabric_type,
                    "gsm": instance.greige.gsm,
                    "width": instance.greige.width,
                    "construction": instance.greige.construction,
                })

            elif instance.material_kind == "finished" and hasattr(instance, "finished"):
                self.initial.update({
                    "base_fabric_type": instance.finished.base_fabric_type,
                    "finish_type": instance.finished.finish_type,
                    "finished_gsm": instance.finished.gsm,
                    "finished_width": instance.finished.width,
                    "end_use": instance.finished.end_use,
                })

            elif instance.material_kind == "trim" and hasattr(instance, "trim"):
                self.initial.update({
                    "trim_type": instance.trim.trim_type,
                    "trim_size": instance.trim.size,
                    "trim_color": instance.trim.color,
                    "brand": instance.trim.brand,
                })

    def clean(self):
        cd = super().clean()
        k = (cd.get("material_kind") or "").strip()

        mt = cd.get("material_type")
        if k and not mt:
            self.add_error("material_type", "Please select Material Type.")
        elif k and mt and mt.material_kind != k:
            self.add_error("material_type", "Selected Material Type does not belong to selected Kind.")

        ms = cd.get("material_shade")
        if k and not ms:
            self.add_error("material_shade", "Please select Material Shade.")
        elif k and ms and ms.material_kind != k:
            self.add_error("material_shade", "Selected Material Shade does not belong to selected Kind.")

        if k == "yarn" and not (cd.get("yarn_type") or "").strip():
            self.add_error("yarn_type", "Please enter Yarn Type.")

        elif k == "greige" and not (cd.get("fabric_type") or "").strip():
            self.add_error("fabric_type", "Please enter Fabric Type.")

        elif k == "finished" and not (cd.get("base_fabric_type") or "").strip():
            self.add_error("base_fabric_type", "Please enter Base Fabric Type.")

        elif k == "trim" and not (cd.get("trim_type") or "").strip():
            self.add_error("trim_type", "Please select Trim Type.")

        return cd

    def save(self) -> Material:
        if not self.is_valid():
            raise ValueError("Call is_valid() before save().")

        cd = self.cleaned_data
        k = cd["material_kind"]

        material = self.instance or Material()
        material.material_kind = k
        material.material_type = cd.get("material_type")
        material.material_shade = cd.get("material_shade")
        material.name = cd["name"]
        material.remarks = cd.get("remarks", "")

        img = cd.get("image")
        if img:
            material.image = img

        material.save()

        YarnDetail.objects.filter(material=material).delete()
        GreigeDetail.objects.filter(material=material).delete()
        FinishedDetail.objects.filter(material=material).delete()
        TrimDetail.objects.filter(material=material).delete()

        if k == "yarn":
            YarnDetail.objects.create(
                material=material,
                yarn_type=cd["yarn_type"],
                yarn_subtype=cd.get("yarn_subtype", ""),
                count_denier=cd.get("count_denier", ""),
                color=cd.get("yarn_color", ""),
            )

        elif k == "greige":
            GreigeDetail.objects.create(
                material=material,
                fabric_type=cd["fabric_type"],
                gsm=cd.get("gsm"),
                width=cd.get("width"),
                construction=cd.get("construction", ""),
            )

        elif k == "finished":
            FinishedDetail.objects.create(
                material=material,
                base_fabric_type=cd["base_fabric_type"],
                finish_type=cd["finish_type"],
                gsm=cd.get("finished_gsm"),
                width=cd.get("finished_width"),
                end_use=cd.get("end_use", ""),
            )

        elif k == "trim":
            TrimDetail.objects.create(
                material=material,
                trim_type=cd["trim_type"],
                size=cd.get("trim_size", ""),
                color=cd.get("trim_color", ""),
                brand=cd.get("brand", ""),
            )

        return material

# ============================================================
# PARTY
# ============================================================

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
GST_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
PHONE_RE = re.compile(r"^[0-9]{10,15}$")


class PartyForm(forms.ModelForm):
    class Meta:
        model = Party
        fields = "__all__"

    def clean_party_name(self):
        v = (self.cleaned_data.get("party_name") or "").strip()
        if not v:
            raise forms.ValidationError("Party Name is required.")
        return v

    def clean_pan_number(self):
        v = (self.cleaned_data.get("pan_number") or "").strip().upper()
        if v and not PAN_RE.match(v):
            raise forms.ValidationError("Invalid PAN format. Example: ABCDE1234F")
        return v

    def clean_gst_number(self):
        v = (self.cleaned_data.get("gst_number") or "").strip().upper()
        if v and not GST_RE.match(v):
            raise forms.ValidationError("Invalid GST format. Example: 27ABCDE1234F1Z5")
        return v

    def clean_phone_number(self):
        v = (self.cleaned_data.get("phone_number") or "").strip()
        if v and not PHONE_RE.match(v):
            raise forms.ValidationError("Phone must be numeric (10–15 digits).")
        return v


# ============================================================
# LOCATION
# ============================================================

class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ["name", "city", "state", "address", "pincode", "is_active"]


# ============================================================
# FIRM
# ============================================================

GST_RE = RegexValidator(
    regex=r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$",
    message="Invalid GST format.",
)
PAN_RE = RegexValidator(
    regex=r"^[A-Z]{5}\d{4}[A-Z]{1}$",
    message="Invalid PAN format.",
)
IFSC_RE = RegexValidator(
    regex=r"^[A-Z]{4}0[A-Z0-9]{6}$",
    message="Invalid IFSC format.",
)
PHONE_RE = RegexValidator(
    regex=r"^\d{10}$",
    message="Phone must be 10 digits.",
)


class FirmForm(forms.ModelForm):
    gst_number = forms.CharField(required=False, validators=[GST_RE])
    pan_number = forms.CharField(required=False, validators=[PAN_RE])
    ifsc_code = forms.CharField(required=False, validators=[IFSC_RE])
    phone = forms.CharField(required=False, validators=[PHONE_RE])

    class Meta:
        model = Firm
        fields = [
            "firm_name", "firm_type",
            "address_line", "city", "state", "pincode",
            "phone", "email", "website",
            "gst_number", "pan_number", "tan_number", "cin_number",
            "bank_name", "account_holder_name", "account_number", "ifsc_code", "branch_name",
        ]


# ============================================================
# UTILITIES: MATERIAL SHADE / MATERIAL TYPE
# ============================================================

class MaterialShadeForm(forms.ModelForm):
    class Meta:
        model = MaterialShade
        fields = ["material_kind", "name", "code", "notes"]


class MaterialTypeForm(forms.ModelForm):
    class Meta:
        model = MaterialType
        fields = ["material_kind", "name", "description"]
