from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django import forms

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
    Category,
    Firm,
    MaterialShade,
    MaterialSubType,
    MaterialType,
    Vendor,
    MainCategory,
    PatternType,
    Catalogue,
    Brand,
    YarnPurchaseOrder,
    GreigePurchaseOrder,
    YarnPurchaseOrderItem,
    YarnPOInward,
    GreigePOInward,
    DyeingPurchaseOrder,
    DyeingPOInward,ReadyPurchaseOrder,
    ReadyPOInward,
    MaterialUnit,
)

# ============================================================
# JOBBERS
# ============================================================

class JobberForm(forms.ModelForm):
    class Meta:
        model = Jobber
        fields = ["name", "phone", "email", "role", "jobber_type", "address", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter full name",
            }),
            "phone": forms.TextInput(attrs={
                "placeholder": "Enter phone number",
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "Enter email address",
            }),
            "role": forms.Select(),
            "jobber_type": forms.Select(),
            "address": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Enter address",
            }),
            "is_active": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["jobber_type"].required = False
        self.fields["jobber_type"].empty_label = "Select jobber type"


class JobberTypeForm(forms.ModelForm):
    class Meta:
        model = JobberType
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter type name",
            }),
        }


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
# MATERIALS
# ============================================================



class MaterialTypeSelect(forms.Select):
    def _resolve_choice_instance(self, value):
        if value in (None, ""):
            return None

        instance = getattr(value, "instance", None)
        if instance is not None:
            return instance

        raw_value = getattr(value, "value", value)
        if raw_value in (None, ""):
            return None

        queryset = getattr(self.choices, "queryset", None)
        if queryset is None:
            return None
        return queryset.filter(pk=raw_value).first()

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        obj = self._resolve_choice_instance(value)
        if obj is not None:
            option.setdefault("attrs", {})["data-kind"] = obj.material_kind or ""
        return option


class MaterialSubTypeSelect(forms.Select):
    def _resolve_choice_instance(self, value):
        if value in (None, ""):
            return None

        instance = getattr(value, "instance", None)
        if instance is not None:
            return instance

        raw_value = getattr(value, "value", value)
        if raw_value in (None, ""):
            return None

        queryset = getattr(self.choices, "queryset", None)
        if queryset is None:
            return None
        return queryset.filter(pk=raw_value).first()

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        obj = self._resolve_choice_instance(value)
        if obj is not None:
            option.setdefault("attrs", {})["data-kind"] = obj.material_kind or ""
            option.setdefault("attrs", {})["data-material-type"] = str(obj.material_type_id or "")
        return option
    
class MaterialForm(forms.Form):
    material_kind = forms.ChoiceField(
        choices=Material.MATERIAL_KIND_CHOICES,
        label="Material Kind",
        widget=forms.HiddenInput(),
    )

    material_type = forms.ModelChoiceField(
        queryset=MaterialType.objects.none(),
        required=False,
        empty_label="Select Material Type",
        widget=MaterialTypeSelect(),
    )
    material_sub_type = forms.ModelChoiceField(
        queryset=MaterialSubType.objects.none(),
        required=False,
        empty_label="Select Material Sub Type",
        widget=MaterialSubTypeSelect(),
    )
    material_shade = forms.ModelChoiceField(
        queryset=MaterialShade.objects.none(),
        required=False,
        empty_label="Select Material Shade",
    )

    # common
    name = forms.CharField(max_length=150, label="Material Name")
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    image = forms.ImageField(required=False)

    # Yarn
    yarn_type = forms.CharField(required=False, widget=forms.HiddenInput())
    yarn_subtype = forms.CharField(required=False, widget=forms.HiddenInput())
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
    trim_type = forms.CharField(required=False, widget=forms.HiddenInput())
    trim_size = forms.CharField(required=False, max_length=60, label="Size")
    trim_color = forms.CharField(required=False, max_length=60, label="Color")
    brand = forms.CharField(required=False, max_length=80, label="Brand (optional)")

    def __init__(self, *args, instance=None, user=None, initial_kind=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance

        kind = (
            (self.data.get("material_kind") or "").strip()
            or (initial_kind or "").strip()
            or (self.initial.get("material_kind") or "").strip()
            or ((getattr(instance, "material_kind", "") if instance else "") or "").strip()
        )

        if kind:
            self.initial["material_kind"] = kind
            self.fields["material_kind"].initial = kind

        type_qs = MaterialType.objects.all()
        if user is not None:
            type_qs = type_qs.filter(owner=user)
        if kind:
            type_qs = type_qs.filter(material_kind=kind)
        type_qs = type_qs.order_by("name")

        sub_type_qs = MaterialSubType.objects.all()
        if user is not None:
            sub_type_qs = sub_type_qs.filter(owner=user)
        if kind:
            sub_type_qs = sub_type_qs.filter(material_kind=kind)
        sub_type_qs = sub_type_qs.select_related("material_type").order_by("material_type__name", "name")

        shade_qs = MaterialShade.objects.all()
        if user is not None:
            shade_qs = shade_qs.filter(owner=user)
        if kind:
            shade_qs = shade_qs.filter(material_kind=kind)
        shade_qs = shade_qs.order_by("name")

        self.fields["material_type"].queryset = type_qs
        self.fields["material_sub_type"].queryset = sub_type_qs
        self.fields["material_shade"].queryset = shade_qs

        self.fields["material_type"].label_from_instance = lambda o: o.name
        self.fields["material_sub_type"].label_from_instance = lambda o: o.name
        self.fields["material_shade"].label_from_instance = lambda o: o.name

        self.fields["material_type"].widget.attrs.update({
            "data-role": "material-type",
        })
        self.fields["material_sub_type"].widget.attrs.update({
            "data-role": "material-sub-type",
        })
        self.fields["material_shade"].widget.attrs.update({
            "data-role": "material-shade",
        })

        self.fields["name"].widget.attrs.update({
            "placeholder": "Enter material name",
        })
        self.fields["remarks"].widget.attrs.update({
            "rows": 4,
            "placeholder": "Add remarks if needed",
        })
        self.fields["image"].widget.attrs.update({
            "accept": "image/*",
        })

        self.fields["yarn_type"].widget.attrs.update({"placeholder": "Enter yarn type"})
        self.fields["yarn_subtype"].widget.attrs.update({"placeholder": "Enter yarn subtype"})
        self.fields["count_denier"].widget.attrs.update({"placeholder": "Enter count / denier"})
        self.fields["yarn_color"].widget.attrs.update({"placeholder": "Enter yarn color"})

        self.fields["fabric_type"].widget.attrs.update({"placeholder": "Enter fabric type"})
        self.fields["gsm"].widget.attrs.update({"placeholder": "Enter GSM"})
        self.fields["width"].widget.attrs.update({"placeholder": "Enter width"})
        self.fields["construction"].widget.attrs.update({"placeholder": "Enter construction"})

        self.fields["base_fabric_type"].widget.attrs.update({"placeholder": "Enter base fabric type"})
        self.fields["finished_gsm"].widget.attrs.update({"placeholder": "Enter GSM"})
        self.fields["finished_width"].widget.attrs.update({"placeholder": "Enter width"})
        self.fields["end_use"].widget.attrs.update({"placeholder": "Enter end use"})

        self.fields["trim_size"].widget.attrs.update({"placeholder": "Enter size"})
        self.fields["trim_color"].widget.attrs.update({"placeholder": "Enter color"})
        self.fields["brand"].widget.attrs.update({"placeholder": "Enter brand"})

        if instance and not self.is_bound:
            self.initial.update({
                "material_kind": instance.material_kind,
                "material_type": instance.material_type_id,
                "material_sub_type": instance.material_sub_type_id,
                "material_shade": instance.material_shade_id,
                "name": instance.name,
                "remarks": instance.remarks,
            })

            if instance.material_kind == "yarn":
                detail = YarnDetail.objects.filter(material=instance).first()
                if detail:
                    self.initial.update({
                        "count_denier": detail.count_denier,
                        "yarn_color": detail.color,
                    })

            elif instance.material_kind == "greige":
                detail = GreigeDetail.objects.filter(material=instance).first()
                if detail:
                    self.initial.update({
                        "fabric_type": detail.fabric_type,
                        "gsm": detail.gsm,
                        "width": detail.width,
                        "construction": detail.construction,
                    })

            elif instance.material_kind == "finished":
                detail = FinishedDetail.objects.filter(material=instance).first()
                if detail:
                    self.initial.update({
                        "base_fabric_type": detail.base_fabric_type,
                        "finish_type": detail.finish_type,
                        "finished_gsm": detail.gsm,
                        "finished_width": detail.width,
                        "end_use": detail.end_use,
                    })

            elif instance.material_kind == "trim":
                detail = TrimDetail.objects.filter(material=instance).first()
                if detail:
                    self.initial.update({
                        "trim_size": detail.size,
                        "trim_color": detail.color,
                        "brand": detail.brand,
                    })

    def clean(self):
        cd = super().clean()
        k = (cd.get("material_kind") or "").strip()

        mt = cd.get("material_type")
        if k and mt and mt.material_kind != k:
            self.add_error("material_type", "Selected Material Type does not belong to selected Kind.")

        mst = cd.get("material_sub_type")
        if mst and not mt:
            self.add_error("material_type", "Select Material Type before choosing Material Sub Type.")
        if k and mst and mst.material_kind != k:
            self.add_error("material_sub_type", "Selected Material Sub Type does not belong to selected Kind.")
        if mt and mst and mst.material_type_id != mt.id:
            self.add_error("material_sub_type", "Selected Material Sub Type does not belong to selected Material Type.")

        ms = cd.get("material_shade")
        if k and ms and ms.material_kind != k:
            self.add_error("material_shade", "Selected Material Shade does not belong to selected Kind.")

        return cd

    def save(self) -> Material:
        if not self.is_valid():
            raise ValueError("Call is_valid() before save().")

        cd = self.cleaned_data
        k = cd["material_kind"]

        material = self.instance or Material()
        material.material_kind = k
        material.material_type = cd.get("material_type")
        material.material_sub_type = cd.get("material_sub_type")
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
            selected_material_type = cd.get("material_type")
            selected_material_sub_type = cd.get("material_sub_type")

            resolved_yarn_type = ""
            resolved_yarn_subtype = ""

            if selected_material_type:
                resolved_yarn_type = selected_material_type.name

            if selected_material_sub_type:
                resolved_yarn_subtype = selected_material_sub_type.name

            YarnDetail.objects.create(
                material=material,
                yarn_type=resolved_yarn_type,
                yarn_subtype=resolved_yarn_subtype,
                count_denier=cd.get("count_denier", ""),
                color=cd.get("yarn_color", ""),
            )

        elif k == "greige":
            GreigeDetail.objects.create(
                material=material,
                fabric_type=cd.get("fabric_type", ""),
                gsm=cd.get("gsm"),
                width=cd.get("width"),
                construction=cd.get("construction", ""),
            )

        elif k == "finished":
            FinishedDetail.objects.create(
                material=material,
                base_fabric_type=cd.get("base_fabric_type", ""),
                finish_type=cd.get("finish_type", ""),
                gsm=cd.get("finished_gsm"),
                width=cd.get("finished_width"),
                end_use=cd.get("end_use", ""),
            )

        elif k == "trim":
            selected_material_type = cd.get("material_type")
            selected_material_sub_type = cd.get("material_sub_type")

            resolved_trim_type = ""
            if selected_material_sub_type:
                resolved_trim_type = selected_material_sub_type.name
            elif selected_material_type:
                resolved_trim_type = selected_material_type.name
            else:
                resolved_trim_type = ""

            TrimDetail.objects.create(
                material=material,
                trim_type=resolved_trim_type,
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
        widgets = {
            "party_name": forms.TextInput(attrs={"placeholder": "Enter party name"}),
            "full_name": forms.TextInput(attrs={"placeholder": "Enter full name"}),
            "address": forms.Textarea(attrs={"rows": 4, "placeholder": "Enter address"}),
            "pan_number": forms.TextInput(attrs={"placeholder": "ABCDE1234F"}),
            "gst_number": forms.TextInput(attrs={"placeholder": "27ABCDE1234F1Z5"}),
            "tan_number": forms.TextInput(attrs={"placeholder": "Enter TAN number"}),
            "state": forms.Select(),
            "phone_number": forms.TextInput(attrs={"placeholder": "Enter phone number"}),
            "email": forms.EmailInput(attrs={"placeholder": "Enter email"}),
            "bank_name": forms.TextInput(attrs={"placeholder": "Enter bank name"}),
            "account_number": forms.TextInput(attrs={"placeholder": "Enter account number"}),
            "ifsc_code": forms.TextInput(attrs={"placeholder": "Enter IFSC code"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            existing_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing_class} jf-input".strip()

        if "state" in self.fields:
            self.fields["state"].required = False

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


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Enter category name"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Add short description or notes"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_name(self):
        value = (self.cleaned_data.get("name") or "").strip()
        if not value:
            raise forms.ValidationError("Category name is required.")

        qs = Category.objects.all()
        if self.user is not None:
            qs = qs.filter(owner=self.user)

        qs = qs.filter(name__iexact=value)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("A category with this name already exists.")

        return value

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
        widgets = {
            "material_kind": forms.RadioSelect(choices=Material.MATERIAL_KIND_CHOICES),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class MaterialTypeForm(forms.ModelForm):
    class Meta:
        model = MaterialType
        fields = ["material_kind", "name", "description"]
        widgets = {
            "material_kind": forms.RadioSelect(choices=Material.MATERIAL_KIND_CHOICES),
            "description": forms.Textarea(attrs={"rows": 3}),
        }




class MaterialSubTypeForm(forms.ModelForm):
    class Meta:
        model = MaterialSubType
        fields = ["material_kind", "material_type", "name", "description"]
        widgets = {
            "material_kind": forms.RadioSelect(choices=Material.MATERIAL_KIND_CHOICES),
            "material_type": MaterialTypeSelect(),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        type_qs = MaterialType.objects.all()
        if user is not None:
            type_qs = type_qs.filter(owner=user)
        type_qs = type_qs.order_by("name")

        self.fields["material_type"].queryset = type_qs
        self.fields["material_type"].empty_label = "Select Material Type"
        self.fields["material_type"].label_from_instance = lambda o: f"{o.get_material_kind_display()} — {o.name}"

    def clean(self):
        cleaned_data = super().clean()
        material_kind = cleaned_data.get("material_kind")
        material_type = cleaned_data.get("material_type")
        name = (cleaned_data.get("name") or "").strip()

        if self.user is not None and material_type and material_type.owner_id != self.user.id:
            self.add_error("material_type", "Selected Material Type is not available for this user.")

        if material_kind and material_type and material_type.material_kind != material_kind:
            self.add_error("material_type", "Selected Material Type does not belong to selected Kind.")

        if self.user is not None and material_type and name:
            qs = MaterialSubType.objects.filter(
                owner=self.user,
                material_type=material_type,
                name__iexact=name,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("name", "This material sub type already exists for the selected material type.")

        return cleaned_data
class MainCategoryForm(forms.ModelForm):
    class Meta:
        model = MainCategory
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter main category name",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Main category name is required.")

        if self.user is not None:
            qs = MainCategory.objects.filter(owner=self.user, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This main category already exists.")

        return name


class PatternTypeForm(forms.ModelForm):
    class Meta:
        model = PatternType
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter pattern type name",
            }),
            "description": forms.Textarea(attrs={
                "placeholder": "Enter short description",
                "rows": 3,
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Pattern type name is required.")

        if self.user is not None:
            qs = PatternType.objects.filter(owner=self.user, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This pattern type already exists.")

        return name

# ============================================================
# VENDOR
# ============================================================

class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ["name", "contact_person", "phone", "email", "gst_number", "address", "is_active"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_phone(self):
        v = (self.cleaned_data.get("phone") or "").strip()
        if v and not re.fullmatch(r"\d{10,15}", v):
            raise forms.ValidationError("Phone must be numeric (10–15 digits).")
        return v


# ============================================================
# YARN PURCHASE ORDER
# ============================================================

class YarnPurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = YarnPurchaseOrder
        fields = [
            "po_number",
            "po_date",
            "cancel_date",
            "vendor",
            "firm",
            "shipping_address",
            "remarks",
            "terms_conditions",
            "discount_percent",
            "others",
            "cgst_percent",
            "sgst_percent",
        ]
        widgets = {
            "po_number": forms.TextInput(attrs={"placeholder": "Vendor / internal PO number"}),
            "po_date": forms.DateInput(attrs={"type": "date"}),
            "cancel_date": forms.DateInput(attrs={"type": "date"}),
            "shipping_address": forms.Textarea(attrs={"rows": 2, "placeholder": "Delivery or shipping address"}),
            "remarks": forms.Textarea(attrs={"rows": 2, "placeholder": "Short note for this PO"}),
            "terms_conditions": forms.Textarea(attrs={"rows": 3, "placeholder": "Payment, delivery, packing, or other terms"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["vendor"].queryset = Vendor.objects.filter(owner=user, is_active=True).order_by("name") if user else Vendor.objects.none()
        self.fields["firm"].queryset = Firm.objects.filter(owner=user).order_by("firm_name") if user else Firm.objects.none()
        self.fields["vendor"].empty_label = "Select vendor"
        self.fields["firm"].empty_label = "Select firm"

        compact_attrs = {
            "po_number": {"placeholder": "Vendor / internal PO number"},
            "shipping_address": {"rows": 2, "placeholder": "Delivery or shipping address"},
            "remarks": {"rows": 2, "placeholder": "Short note for this PO"},
            "terms_conditions": {"rows": 3, "placeholder": "Payment, delivery, packing, or other terms"},
            "discount_percent": {"min": "0", "step": "0.01", "placeholder": "0.00"},
            "others": {"min": "0", "step": "0.01", "placeholder": "0.00"},
            "cgst_percent": {"min": "0", "step": "0.01", "placeholder": "0.00"},
            "sgst_percent": {"min": "0", "step": "0.01", "placeholder": "0.00"},
        }
        for field_name, attrs in compact_attrs.items():
            self.fields[field_name].widget.attrs.update(attrs)

        if not self.is_bound:
            from django.utils import timezone
            self.fields["po_date"].initial = timezone.localdate()
            self.fields["discount_percent"].initial = 0
            self.fields["others"].initial = 0
            self.fields["cgst_percent"].initial = 2.5
            self.fields["sgst_percent"].initial = 2.5
            firm = self.fields["firm"].queryset.first()
            if firm:
                self.fields["firm"].initial = firm.pk
                if not self.initial.get("shipping_address"):
                    bits = [firm.address_line, firm.city, firm.state, firm.pincode]
                    self.fields["shipping_address"].initial = ", ".join([b for b in bits if b])

class YarnPOReviewForm(forms.Form):
    decision = forms.ChoiceField(
        choices=[("approve", "Approve"), ("reject", "Reject")],
        widget=forms.HiddenInput,
    )
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Reason for rejection"}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("decision") == "reject" and not (cleaned.get("rejection_reason") or "").strip():
            self.add_error("rejection_reason", "Rejection reason is required.")
        return cleaned


class YarnPOInwardForm(forms.ModelForm):
    class Meta:
        model = YarnPOInward
        fields = ["inward_date", "notes"]
        widgets = {
            "inward_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional inward notes"}),
        }

class YarnPurchaseOrderItemForm(forms.ModelForm):
    UNIT_CHOICES = [
        ("", "Select unit"),
        ("MTR", "MTR"),
        ("KG", "KG"),
        ("PCS", "PCS"),
        ("CONE", "CONE"),
        ("BAG", "BAG"),
        ("ROLL", "ROLL"),
    ]

    unit = forms.ChoiceField(required=False, choices=UNIT_CHOICES)

    class Meta:
        model = YarnPurchaseOrderItem
        fields = [
            "material_type", "unit", "quantity", "value", "dia", "gauge", "rolls",
            "count", "gsm", "sl", "hsn_code", "remark", "rate", "final_amount",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        qs = MaterialType.objects.filter(material_kind="yarn")
        if user is not None:
            qs = qs.filter(owner=user)
        qs = qs.order_by("name")

        self.fields["material_type"].queryset = qs
        self.fields["material_type"].empty_label = "Select Yarn Type"
        self.fields["material_type"].label_from_instance = lambda obj: obj.name

        current_unit = (self.initial.get("unit") or getattr(self.instance, "unit", "") or "").strip()
        if self.is_bound:
            bound_unit = (self.data.get(self.add_prefix("unit")) or "").strip()
            if bound_unit:
                current_unit = bound_unit

        self.fields["unit"].required = False
        self.fields["unit"].widget = forms.Select(
            choices=_material_unit_choices(user, current_unit)
        )

    def clean_unit(self):
        value = (self.cleaned_data.get("unit") or "").strip().upper()
        valid_units = {choice for choice, _label in self.UNIT_CHOICES if choice}
        if value and value not in valid_units:
            raise forms.ValidationError("Select a valid unit.")
        return value

YarnPurchaseOrderItemFormSet = inlineformset_factory(
    YarnPurchaseOrder,
    YarnPurchaseOrderItem,
    form=YarnPurchaseOrderItemForm,
    fields=[
        "material_type", "unit", "quantity", "value", "dia", "gauge", "rolls",
        "count", "gsm", "sl", "hsn_code", "remark", "rate", "final_amount",
    ],
    extra=1,
    can_delete=True,
)
class GreigePurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = GreigePurchaseOrder
        fields = [
            "po_number",
            "internal_po_number",
            "source_yarn_po",
            "po_date",
            "available_qty",
            "vendor",
            "firm",
            "shipping_address",
            "delivery_period",
            "expected_delivery_date",
            "cancel_date",
            "director",
            "validity_period",
            "address",
            "delivery_schedule",
            "remarks",
        ]
        widgets = {
            "po_date": forms.DateInput(attrs={"type": "date"}),
            "expected_delivery_date": forms.DateInput(attrs={"type": "date"}),
            "cancel_date": forms.DateInput(attrs={"type": "date"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, source_yarn_po=None, lock_source=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["vendor"].queryset = (
            Vendor.objects.filter(owner=user, is_active=True).order_by("name")
            if user else Vendor.objects.none()
        )
        self.fields["firm"].queryset = (
            Firm.objects.filter(owner=user).order_by("firm_name")
            if user else Firm.objects.none()
        )

        source_ids_qs = YarnPurchaseOrder.objects.filter(
            items__inward_items__isnull=False
        )
        if user is not None:
            source_ids_qs = source_ids_qs.filter(owner=user)

        allowed_ids = set(source_ids_qs.values_list("pk", flat=True))

        if self.instance.pk and self.instance.source_yarn_po_id:
            allowed_ids.add(self.instance.source_yarn_po_id)

        if source_yarn_po is not None:
            allowed_ids.add(source_yarn_po.pk)
            self.fields["source_yarn_po"].initial = source_yarn_po.pk

        self.fields["source_yarn_po"].queryset = YarnPurchaseOrder.objects.filter(
            pk__in=allowed_ids
        ).order_by("-id")

        self.fields["source_yarn_po"].empty_label = "Select source yarn PO"
        self.fields["vendor"].empty_label = "Select vendor"
        self.fields["firm"].empty_label = "Select firm"

        if lock_source:
            self.fields["source_yarn_po"].disabled = True

        if not self.is_bound:
            from django.utils import timezone
            self.fields["po_date"].initial = self.instance.po_date or timezone.localdate()
            if self.instance.pk and not self.initial.get("available_qty"):
                self.fields["available_qty"].initial = self.instance.remaining_qty_total


class GreigePOInwardForm(forms.ModelForm):
    class Meta:
        model = GreigePOInward
        fields = ["inward_date", "notes"]
        widgets = {
            "inward_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional inward notes"}),
        }


class DyeingPurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = DyeingPurchaseOrder
        fields = [
            "po_number",
            "internal_po_number",
            "source_greige_po",
            "po_date",
            "available_qty",
            "vendor",
            "firm",
            "shipping_address",
            "delivery_period",
            "expected_delivery_date",
            "cancel_date",
            "director",
            "validity_period",
            "address",
            "delivery_schedule",
            "remarks",
        ]
        widgets = {
            "po_date": forms.DateInput(attrs={"type": "date"}),
            "expected_delivery_date": forms.DateInput(attrs={"type": "date"}),
            "cancel_date": forms.DateInput(attrs={"type": "date"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, source_greige_po=None, lock_source=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["vendor"].queryset = (
            Vendor.objects.filter(owner=user, is_active=True).order_by("name")
            if user else Vendor.objects.none()
        )
        self.fields["firm"].queryset = (
            Firm.objects.filter(owner=user).order_by("firm_name")
            if user else Firm.objects.none()
        )

        source_ids_qs = GreigePurchaseOrder.objects.filter(
            items__inward_items__isnull=False
        )
        if user is not None:
            source_ids_qs = source_ids_qs.filter(owner=user)

        allowed_ids = set(source_ids_qs.values_list("pk", flat=True))

        if self.instance.pk and self.instance.source_greige_po_id:
            allowed_ids.add(self.instance.source_greige_po_id)

        if source_greige_po is not None:
            allowed_ids.add(source_greige_po.pk)
            self.fields["source_greige_po"].initial = source_greige_po.pk

        self.fields["source_greige_po"].queryset = GreigePurchaseOrder.objects.filter(
            pk__in=allowed_ids
        ).order_by("-id")

        self.fields["source_greige_po"].empty_label = "Select source greige PO"
        self.fields["vendor"].empty_label = "Select vendor"
        self.fields["firm"].empty_label = "Select firm"

        if lock_source:
            self.fields["source_greige_po"].disabled = True

        if not self.is_bound:
            from django.utils import timezone
            self.fields["po_date"].initial = self.instance.po_date or timezone.localdate()
            if self.instance.pk and not self.initial.get("available_qty"):
                self.fields["available_qty"].initial = self.instance.remaining_qty_total


class DyeingPOInwardForm(forms.ModelForm):
    class Meta:
        model = DyeingPOInward
        fields = ["inward_date", "notes"]
        widgets = {
            "inward_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional inward notes"}),
        }

class ReadyPurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = ReadyPurchaseOrder
        fields = [
            "po_number",
            "internal_po_number",
            "source_dyeing_po",
            "po_date",
            "available_qty",
            "vendor",
            "firm",
            "shipping_address",
            "delivery_period",
            "expected_delivery_date",
            "cancel_date",
            "director",
            "validity_period",
            "address",
            "delivery_schedule",
            "remarks",
        ]
        widgets = {
            "po_date": forms.DateInput(attrs={"type": "date"}),
            "expected_delivery_date": forms.DateInput(attrs={"type": "date"}),
            "cancel_date": forms.DateInput(attrs={"type": "date"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, source_dyeing_po=None, lock_source=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["vendor"].queryset = (
            Vendor.objects.filter(owner=user, is_active=True).order_by("name")
            if user else Vendor.objects.none()
        )
        self.fields["firm"].queryset = (
            Firm.objects.filter(owner=user).order_by("firm_name")
            if user else Firm.objects.none()
        )

        source_ids_qs = DyeingPurchaseOrder.objects.filter(items__inward_items__isnull=False)
        if user is not None:
            source_ids_qs = source_ids_qs.filter(owner=user)

        allowed_ids = set(source_ids_qs.values_list("pk", flat=True))

        if self.instance.pk and self.instance.source_dyeing_po_id:
            allowed_ids.add(self.instance.source_dyeing_po_id)

        if source_dyeing_po is not None:
            allowed_ids.add(source_dyeing_po.pk)
            self.fields["source_dyeing_po"].initial = source_dyeing_po.pk

        self.fields["source_dyeing_po"].queryset = DyeingPurchaseOrder.objects.filter(
            pk__in=allowed_ids
        ).order_by("-id")

        self.fields["source_dyeing_po"].empty_label = "Select source dyeing PO"
        self.fields["vendor"].empty_label = "Select vendor"
        self.fields["firm"].empty_label = "Select firm"

        if lock_source:
            self.fields["source_dyeing_po"].disabled = True

        if not self.is_bound:
            from django.utils import timezone
            self.fields["po_date"].initial = self.instance.po_date or timezone.localdate()
            if self.instance.pk and not self.initial.get("available_qty"):
                self.fields["available_qty"].initial = self.instance.remaining_qty_total
                
class ReadyPOInwardForm(forms.ModelForm):
    class Meta:
        model = ReadyPOInward
        fields = ["inward_date", "notes"]
        widgets = {
            "inward_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional inward notes"}),
        }


class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ["name", "description", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Brand name is required.")

        if self.user is not None:
            qs = Brand.objects.filter(owner=self.user, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This brand already exists.")

        return name
    
def _material_unit_choices(user, current_value=""):
    qs = MaterialUnit.objects.none()
    if user is not None:
        qs = MaterialUnit.objects.filter(owner=user).order_by("name")

    choices = [("", "Select unit")] + [(obj.name, obj.name) for obj in qs]
    values = {value for value, _label in choices}

    current_value = (current_value or "").strip()
    if current_value and current_value not in values:
        choices.append((current_value, current_value))

    return choices


class MaterialUnitForm(forms.ModelForm):
    class Meta:
        model = MaterialUnit
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter unit name (e.g. KG, MTR)",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Unit name is required.")

        if self.user is not None:
            qs = MaterialUnit.objects.filter(owner=self.user, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This material unit already exists.")

        return name
    
class CatalogueForm(forms.ModelForm):
    class Meta:
        model = Catalogue
        fields = ["name", "wear_type", "description", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Catalogue name is required.")

        if self.user is not None:
            qs = Catalogue.objects.filter(owner=self.user, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This catalogue already exists.")

        return name