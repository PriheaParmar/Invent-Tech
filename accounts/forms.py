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

        # add placeholders + CSS class so it matches your design
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
        self.fields["password1"].widget.attrs.update({
            "class": "input",
            "placeholder": "Create a password",
            "autocomplete": "new-password",
        })
        self.fields["password2"].widget.attrs.update({
            "class": "input",
            "placeholder": "Confirm password",
            "autocomplete": "new-password",
        })

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
    # STEP 1: Material Kind (fixed 4 options)
    material_kind = forms.ChoiceField(
        choices=[("", "Select")] + list(Material.MATERIAL_KIND_CHOICES),
        required=True,
        label="Material Kind",
    )

    # STEP 2: Material Type (dynamic master)
    material_type = forms.ModelChoiceField(
        queryset=MaterialType.objects.none(),
        required=False,
        empty_label="Select",
        label="Material Type",
    )

    # STEP 3: Material Shade (dynamic master)
    material_shade = forms.ModelChoiceField(
        queryset=MaterialShade.objects.none(),
        required=False,
        empty_label="Select",
        label="Material Shade",
    )

    # common
    name = forms.CharField(max_length=150, label="Material Name")
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

    def __init__(self, *args, instance: Material | None = None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance

        # Dynamic dropdowns (single source of truth)
        type_qs = MaterialType.objects.all().order_by("name")
        shade_qs = MaterialShade.objects.all().order_by("name")
        if user is not None:
            type_qs = type_qs.filter(owner=user)
            shade_qs = shade_qs.filter(owner=user)

        self.fields["material_type"].queryset = type_qs
        self.fields["material_shade"].queryset = shade_qs

        self.fields["name"].widget.attrs.update({"placeholder": "Enter name"})
        self.fields["remarks"].widget.attrs.update({"placeholder": "Remarks (optional)"})

        if instance:
            self.fields["material_kind"].initial = instance.material_kind
            self.fields["material_type"].initial = instance.material_type_id
            self.fields["material_shade"].initial = instance.material_shade_id
            self.fields["name"].initial = instance.name
            self.fields["remarks"].initial = instance.remarks

            k = instance.material_kind

            if k == "yarn" and hasattr(instance, "yarn"):
                self.fields["yarn_type"].initial = instance.yarn.yarn_type
                self.fields["yarn_subtype"].initial = instance.yarn.yarn_subtype
                self.fields["count_denier"].initial = instance.yarn.count_denier
                self.fields["yarn_color"].initial = instance.yarn.color

            if k == "greige" and hasattr(instance, "greige"):
                self.fields["fabric_type"].initial = instance.greige.fabric_type
                self.fields["gsm"].initial = instance.greige.gsm
                self.fields["width"].initial = instance.greige.width
                self.fields["construction"].initial = instance.greige.construction

            if k == "finished" and hasattr(instance, "finished"):
                self.fields["base_fabric_type"].initial = instance.finished.base_fabric_type
                self.fields["finish_type"].initial = instance.finished.finish_type
                self.fields["finished_gsm"].initial = instance.finished.gsm
                self.fields["finished_width"].initial = instance.finished.width
                self.fields["end_use"].initial = instance.finished.end_use

            if k == "trim" and hasattr(instance, "trim"):
                self.fields["trim_type"].initial = instance.trim.trim_type
                self.fields["trim_size"].initial = instance.trim.size
                self.fields["trim_color"].initial = instance.trim.color
                self.fields["brand"].initial = instance.trim.brand

    def clean(self):
        cd = super().clean()
        k = (cd.get("material_kind") or "").strip()

        # image rules (keeps your old behavior: finished requires image)
        IMAGE_REQUIRED = {
            "yarn": False,
            "greige": False,
            "finished": True,
            "trim": False,
        }
        need_img = IMAGE_REQUIRED.get(k, False)
        if need_img and not cd.get("image") and not (self.instance and self.instance.image):
            raise ValidationError({"image": "Image is required for this material kind."})

        # required fields per kind (same validations, just switched to material_kind)
        if k == "yarn":
            if not cd.get("yarn_type"):
                raise ValidationError({"yarn_type": "Yarn Type is required."})

        elif k == "greige":
            if not cd.get("fabric_type"):
                raise ValidationError({"fabric_type": "Fabric Type is required."})

        elif k == "finished":
            if not cd.get("base_fabric_type"):
                raise ValidationError({"base_fabric_type": "Base Fabric Type is required."})
            if not cd.get("finish_type"):
                raise ValidationError({"finish_type": "Finish Type is required."})

        elif k == "trim":
            if not cd.get("trim_type"):
                raise ValidationError({"trim_type": "Trim Type is required."})

        return cd

    def save(self) -> Material:
        if not self.is_valid():
            raise ValueError("Call is_valid() before save().")

        cd = self.cleaned_data
        k = cd["material_kind"]

        material = self.instance or Material()
        material.material_kind = k
        material.material_type = cd.get("material_type")  # FK object
        material.material_shade = cd.get("material_shade")  # FK object
        material.name = cd["name"]
        material.remarks = cd.get("remarks", "")

        img = cd.get("image")
        if img:
            material.image = img

        material.save()

        # Keep your old behavior: clear and recreate details
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
        fields = ["name", "code", "notes"]


class MaterialTypeForm(forms.ModelForm):
    class Meta:
        model = MaterialType
        fields = ["name", "description"]
