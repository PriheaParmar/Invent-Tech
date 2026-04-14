from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

from django.db.models import Q
import re

from .models import (
    Jobber,
    JobberType,
    InwardType,
    Material,
    YarnDetail,
    GreigeDetail,
    FinishedDetail,
    DyeingOtherCharge,
    TermsCondition,
    TrimDetail,
    Party,
    Location,
    Category,
    Client,
    Firm,
    MaterialShade,
    MaterialSubType,
    MaterialType,
    BOM,
    BOMMaterialItem,
    BOMJobberItem,
    BOMProcessItem,
    BOMExpenseItem,
    BOMImage,
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
    DyeingPOInward,
    ReadyPurchaseOrder,
    ReadyPOInward,
    MaterialUnit,
    Program,
    ProgramJobberItem,
    ProgramSizeDetail,
    SubCategory,
    
    MainCategory,
    Expense,
)


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            "name",
            "contact_person",
            "phone",
            "email",
            "gst_number",
            "pan_number",
            "city",
            "state",
            "address",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Enter client name", "maxlength": "180"}),
            "contact_person": forms.TextInput(attrs={"placeholder": "Enter contact person", "maxlength": "120"}),
            "phone": forms.TextInput(attrs={
                "placeholder": "Enter 10 digit phone number",
                "inputmode": "numeric",
                "maxlength": "10",
                "autocomplete": "off",
                "pattern": r"\d{10}",
                "oninput": "this.value=this.value.replace(/\D/g,'').slice(0,10)",
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "Enter email",
                "autocomplete": "email",
                "spellcheck": "false",
            }),
            "gst_number": forms.TextInput(attrs={
                "placeholder": "27ABCDE1234F1Z5",
                "maxlength": "15",
                "autocapitalize": "characters",
                "spellcheck": "false",
                "autocomplete": "off",
                "data-mask-format": "99AAAAA9999AXZX",
            }),
            "pan_number": forms.TextInput(attrs={
                "placeholder": "ABCDE1234F",
                "maxlength": "10",
                "autocapitalize": "characters",
                "spellcheck": "false",
                "autocomplete": "off",
                "data-mask-format": "AAAAA9999A",
            }),
            "city": forms.TextInput(attrs={"placeholder": "Enter city", "maxlength": "80"}),
            "state": forms.Select(),
            "address": forms.Textarea(attrs={"rows": 3, "placeholder": "Enter address"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} jf-input".strip()

        self.fields["name"].required = True
        self.fields["phone"].required = True
        self.fields["state"].required = False

    @staticmethod
    def _clean_text(value):
        return re.sub(r"\s+", " ", (value or "").strip())

    def clean_name(self):
        value = self._clean_text(self.cleaned_data.get("name"))
        if not value:
            raise forms.ValidationError("Client name is required.")

        if self.user is not None:
            qs = Client.objects.filter(owner=self.user, name__iexact=value)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This client already exists.")

        return value

    def clean_contact_person(self):
        value = self._clean_text(self.cleaned_data.get("contact_person"))
        if value and not re.fullmatch(r"[A-Za-z][A-Za-z .'-]{1,119}", value):
            raise forms.ValidationError("Contact person can contain only letters, spaces, dot, apostrophe, and hyphen.")
        return value

    def clean_phone(self):
        value = re.sub(r"\D", "", (self.cleaned_data.get("phone") or ""))
        if not value:
            raise forms.ValidationError("Phone number is required.")
        if not re.fullmatch(r"\d{10}", value):
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        return value

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip().lower()

    def clean_gst_number(self):
        value = (self.cleaned_data.get("gst_number") or "").strip().upper()
        if value and not PARTY_GST_RE.fullmatch(value):
            raise forms.ValidationError("Enter a valid GST number, like 27ABCDE1234F1Z5.")
        return value

    def clean_pan_number(self):
        value = (self.cleaned_data.get("pan_number") or "").strip().upper()
        if value and not PARTY_PAN_RE.fullmatch(value):
            raise forms.ValidationError("Enter a valid PAN number, like ABCDE1234F.")
        return value

    def clean_city(self):
        value = self._clean_text(self.cleaned_data.get("city"))
        if value and not re.fullmatch(r"[A-Za-z][A-Za-z .'-]{1,79}", value):
            raise forms.ValidationError("City can contain only letters, spaces, dot, apostrophe, and hyphen.")
        return value

    def clean_address(self):
        return self._clean_text(self.cleaned_data.get("address"))
# ============================================================
# JOBBERS
# ============================================================

class JobberForm(forms.ModelForm):
    class Meta:
        model = Jobber
        fields = ["name", "phone", "email", "role", "jobber_type", "address"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter full name",
            }),
            "phone": forms.TextInput(attrs={
            "placeholder": "Enter phone number",
            "inputmode": "numeric",
            "maxlength": "10",
            "minlength": "10",
            "pattern": r"\d{10}",
            "autocomplete": "tel",
            "title": "Phone number must be exactly 10 digits",
            "oninput": "this.value=this.value.replace(/\\D/g,'').slice(0,10)",
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
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["jobber_type"].required = False
        self.fields["jobber_type"].empty_label = "Select jobber type"

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()

        if not phone:
            return phone

        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain digits only.")

        if len(phone) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")

        return phone

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
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
    ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

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
    finish_type = forms.ChoiceField(
        required=False,
        choices=[("", "Select")] + list(FinishedDetail.FINISH_TYPE_CHOICES),
    )
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
        self.user = user

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
            shade_qs = shade_qs.filter(
                Q(material_kind=kind) | Q(material_kind__isnull=True) | Q(material_kind="")
            )
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
            "maxlength": "150",
        })
        self.fields["remarks"].widget.attrs.update({
            "rows": 4,
            "placeholder": "Add remarks if needed",
            "maxlength": "500",
        })
        self.fields["image"].widget.attrs.update({
            "accept": "image/*",
        })

        self.fields["yarn_type"].widget.attrs.update({"placeholder": "Enter yarn type"})
        self.fields["yarn_subtype"].widget.attrs.update({"placeholder": "Enter yarn subtype"})
        self.fields["count_denier"].widget.attrs.update({
            "placeholder": "Enter count / denier",
            "maxlength": "40",
        })
        self.fields["yarn_color"].widget.attrs.update({
            "placeholder": "Enter yarn color",
            "maxlength": "60",
        })

        self.fields["fabric_type"].widget.attrs.update({
            "placeholder": "Enter fabric type",
            "maxlength": "120",
        })
        self.fields["gsm"].widget.attrs.update({
            "placeholder": "Enter GSM",
            "min": "0",
            "step": "0.01",
            "inputmode": "decimal",
        })
        self.fields["width"].widget.attrs.update({
            "placeholder": "Enter width",
            "min": "0",
            "step": "0.01",
            "inputmode": "decimal",
        })
        self.fields["construction"].widget.attrs.update({
            "placeholder": "Enter construction",
            "maxlength": "120",
        })

        self.fields["base_fabric_type"].widget.attrs.update({
            "placeholder": "Enter base fabric type",
            "maxlength": "120",
        })
        self.fields["finished_gsm"].widget.attrs.update({
            "placeholder": "Enter GSM",
            "min": "0",
            "step": "0.01",
            "inputmode": "decimal",
        })
        self.fields["finished_width"].widget.attrs.update({
            "placeholder": "Enter width",
            "min": "0",
            "step": "0.01",
            "inputmode": "decimal",
        })
        self.fields["end_use"].widget.attrs.update({
            "placeholder": "Enter end use",
            "maxlength": "120",
        })

        self.fields["trim_size"].widget.attrs.update({
            "placeholder": "Enter size",
            "maxlength": "60",
        })
        self.fields["trim_color"].widget.attrs.update({
            "placeholder": "Enter color",
            "maxlength": "60",
        })
        self.fields["brand"].widget.attrs.update({
            "placeholder": "Enter brand",
            "maxlength": "80",
        })

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

    def _clean_text_value(self, field_name, *, label, max_length=None, allow_chars_pattern=None):
        value = (self.cleaned_data.get(field_name) or "").strip()
        self.cleaned_data[field_name] = value

        if not value:
            return value

        if max_length and len(value) > max_length:
            raise ValidationError(f"{label} cannot be more than {max_length} characters.")

        if allow_chars_pattern and not re.fullmatch(allow_chars_pattern, value):
            raise ValidationError(f"Enter a valid {label.lower()}.")

        return value

    def _clean_positive_decimal(self, field_name, *, label):
        value = self.cleaned_data.get(field_name)
        if value in (None, ""):
            return value
        if value <= 0:
            raise ValidationError(f"{label} must be greater than 0.")
        return value

    def clean_material_kind(self):
        value = (self.cleaned_data.get("material_kind") or "").strip()
        allowed_kinds = {choice[0] for choice in Material.MATERIAL_KIND_CHOICES}
        if value not in allowed_kinds:
            raise ValidationError("Select a valid material kind.")
        return value

    def clean_name(self):
        value = self._clean_text_value(
            "name",
            label="Material Name",
            max_length=150,
            allow_chars_pattern=r".*[A-Za-z0-9].*",
        )
        if not value:
            raise ValidationError("Material Name is required.")
        if len(value) < 2:
            raise ValidationError("Material Name must be at least 2 characters long.")
        return value

    def clean_remarks(self):
        return self._clean_text_value("remarks", label="Remarks", max_length=500)

    def clean_count_denier(self):
        return self._clean_text_value(
            "count_denier",
            label="Count / Denier",
            max_length=40,
            allow_chars_pattern=r"[A-Za-z0-9\s./()_%+-]+",
        )

    def clean_yarn_color(self):
        return self._clean_text_value(
            "yarn_color",
            label="Color",
            max_length=60,
            allow_chars_pattern=r"[A-Za-z0-9\s.,()/#&+-]+",
        )

    def clean_fabric_type(self):
        return self._clean_text_value(
            "fabric_type",
            label="Fabric Type",
            max_length=120,
        )

    def clean_construction(self):
        return self._clean_text_value(
            "construction",
            label="Construction",
            max_length=120,
            allow_chars_pattern=r"[A-Za-z0-9\s.,()/%xX+-]+",
        )

    def clean_base_fabric_type(self):
        return self._clean_text_value(
            "base_fabric_type",
            label="Base Fabric Type",
            max_length=120,
        )

    def clean_end_use(self):
        return self._clean_text_value(
            "end_use",
            label="End Use",
            max_length=120,
        )

    def clean_trim_size(self):
        return self._clean_text_value(
            "trim_size",
            label="Size",
            max_length=60,
            allow_chars_pattern=r"[A-Za-z0-9\s.,()/#xX+-]+",
        )

    def clean_trim_color(self):
        return self._clean_text_value(
            "trim_color",
            label="Color",
            max_length=60,
            allow_chars_pattern=r"[A-Za-z0-9\s.,()/#&+-]+",
        )

    def clean_brand(self):
        return self._clean_text_value(
            "brand",
            label="Brand",
            max_length=80,
        )

    def clean_gsm(self):
        return self._clean_positive_decimal("gsm", label="GSM")

    def clean_width(self):
        return self._clean_positive_decimal("width", label="Width")

    def clean_finished_gsm(self):
        return self._clean_positive_decimal("finished_gsm", label="GSM")

    def clean_finished_width(self):
        return self._clean_positive_decimal("finished_width", label="Width")

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            return image

        file_name = (getattr(image, "name", "") or "").lower()
        if file_name:
            dot = file_name.rfind(".")
            ext = file_name[dot:] if dot != -1 else ""
            if ext not in self.ALLOWED_IMAGE_EXTENSIONS:
                raise ValidationError("Upload a valid image file (JPG, JPEG, PNG, WEBP, or GIF).")

        content_type = getattr(image, "content_type", "") or ""
        if content_type and not content_type.startswith("image/"):
            raise ValidationError("The selected file must be an image.")

        if getattr(image, "size", 0) > self.MAX_IMAGE_SIZE:
            raise ValidationError("Image size must be 5 MB or less.")

        return image

    def clean(self):
        cd = super().clean()
        k = (cd.get("material_kind") or "").strip()

        mt = cd.get("material_type")
        if self.user is not None and mt and mt.owner_id != self.user.id:
            self.add_error("material_type", "Selected Material Type is not available for this user.")
        if k and mt and mt.material_kind != k:
            self.add_error("material_type", "Selected Material Type does not belong to selected Kind.")

        mst = cd.get("material_sub_type")
        if mst and not mt:
            self.add_error("material_type", "Select Material Type before choosing Material Sub Type.")
        if self.user is not None and mst and mst.owner_id != self.user.id:
            self.add_error("material_sub_type", "Selected Material Sub Type is not available for this user.")
        if k and mst and mst.material_kind != k:
            self.add_error("material_sub_type", "Selected Material Sub Type does not belong to selected Kind.")
        if mt and mst and mst.material_type_id != mt.id:
            self.add_error("material_sub_type", "Selected Material Sub Type does not belong to selected Material Type.")


        ms = cd.get("material_shade")
        if self.user is not None and ms and ms.owner_id != self.user.id:
            self.add_error("material_shade", "Selected Material Shade is not available for this user.")
        if k and ms and (ms.material_kind or "").strip() not in ("", k):
            self.add_error("material_shade", "Selected Material Shade does not belong to selected Kind.")
        if k == "trim" and not mt:
            self.add_error("material_type", "Please select a Material Type for trim materials.")

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

PARTY_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
PARTY_GST_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
PARTY_TAN_RE = re.compile(r"^[A-Z]{4}[0-9]{5}[A-Z]$")
PARTY_PHONE_RE = re.compile(r"^[0-9]{10,15}$")
PARTY_ACCOUNT_RE = re.compile(r"^[0-9]{6,30}$")
PARTY_IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


class PartyForm(forms.ModelForm):
    class Meta:
        model = Party
        fields = "__all__"
        widgets = {
            "party_name": forms.TextInput(attrs={
                "placeholder": "Enter party name",
                "maxlength": "150",
            }),
            "full_name": forms.TextInput(attrs={
                "placeholder": "Enter full name",
                "maxlength": "200",
            }),
            "address": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Enter address",
            }),
            "pan_number": forms.TextInput(attrs={
            "placeholder": "ABCDE1234F",
            "maxlength": "10",
            "autocapitalize": "characters",
            "spellcheck": "false",
            "autocomplete": "off",
            "data-mask-format": "AAAAA9999A",
            }),
            "gst_number": forms.TextInput(attrs={
                "placeholder": "27ABCDE1234F1Z5",
                "maxlength": "15",
                "autocapitalize": "characters",
                "spellcheck": "false",
                "autocomplete": "off",
                "data-mask-format": "99AAAAA9999AXZX",
            }),
            "tan_number": forms.TextInput(attrs={
                "placeholder": "ABCD12345E",
                "maxlength": "10",
                "autocapitalize": "characters",
                "spellcheck": "false",
                "autocomplete": "off",
                "data-mask-format": "AAAA99999A",
            }),
            "state": forms.Select(),
            "phone_number": forms.TextInput(attrs={
            "placeholder": "Enter phone number",
            "inputmode": "numeric",
            "maxlength": "15",
            "autocomplete": "off",
            "data-mask-format": "999999999999999",
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "Enter email",
                "autocomplete": "email",
                "spellcheck": "false",
            }),
            "bank_name": forms.TextInput(attrs={
                "placeholder": "Enter bank name",
                "maxlength": "120",
            }),
            "account_number": forms.TextInput(attrs={
            "placeholder": "Enter account number",
            "inputmode": "numeric",
            "maxlength": "30",
            "autocomplete": "off",
            "data-mask-format": "999999999999999999999999999999",
            }),
            "ifsc_code": forms.TextInput(attrs={
                "placeholder": "SBIN0001234",
                "maxlength": "11",
                "autocapitalize": "characters",
                "spellcheck": "false",
                "autocomplete": "off",
                "data-mask-format": "AAAA0XXXXXX",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            existing_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing_class} jf-input".strip()

        self.fields["party_name"].required = True

        if "state" in self.fields:
            self.fields["state"].required = False

    def clean_party_name(self):
        v = (self.cleaned_data.get("party_name") or "").strip()
        if not v:
            raise forms.ValidationError("Party name is required.")
        return v

    def clean_full_name(self):
        return (self.cleaned_data.get("full_name") or "").strip()

    def clean_address(self):
        return (self.cleaned_data.get("address") or "").strip()

    def clean_pan_number(self):
        v = (self.cleaned_data.get("pan_number") or "").strip().upper()
        if v and not PARTY_PAN_RE.match(v):
            raise forms.ValidationError("Enter a valid PAN number, like ABCDE1234F.")
        return v

    def clean_gst_number(self):
        v = (self.cleaned_data.get("gst_number") or "").strip().upper()
        if v and not PARTY_GST_RE.match(v):
            raise forms.ValidationError("Enter a valid GST number, like 27ABCDE1234F1Z5.")
        return v

    def clean_tan_number(self):
        v = (self.cleaned_data.get("tan_number") or "").strip().upper()
        if v and not PARTY_TAN_RE.match(v):
            raise forms.ValidationError("Enter a valid TAN number, like ABCD12345E.")
        return v

    def clean_phone_number(self):
        v = (self.cleaned_data.get("phone_number") or "").strip()
        if v and not PARTY_PHONE_RE.match(v):
            raise forms.ValidationError("Phone number must contain only digits and be 10 to 15 digits long.")
        return v

    def clean_email(self):
        v = (self.cleaned_data.get("email") or "").strip().lower()
        return v

    def clean_bank_name(self):
        return (self.cleaned_data.get("bank_name") or "").strip()

    def clean_account_number(self):
        v = (self.cleaned_data.get("account_number") or "").strip()
        if v and not PARTY_ACCOUNT_RE.match(v):
            raise forms.ValidationError("Account number must contain only digits and be 6 to 30 digits long.")
        return v

    def clean_ifsc_code(self):
        v = (self.cleaned_data.get("ifsc_code") or "").strip().upper()
        if v and not PARTY_IFSC_RE.match(v):
            raise forms.ValidationError("Enter a valid IFSC code, like SBIN0001234.")
        return v

# ============================================================
# LOCATION
# ============================================================
class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = [
            "name",
            "address_line_1",
            "address_line_2",
            "landmark",
            "city",
            "state",
            "pincode",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Enter location name"}),
            "address_line_1": forms.TextInput(attrs={"placeholder": "Address line 1"}),
            "address_line_2": forms.TextInput(attrs={"placeholder": "Address line 2 (optional)"}),
            "landmark": forms.TextInput(attrs={"placeholder": "Landmark (optional)"}),
            "city": forms.TextInput(attrs={"placeholder": "Enter city"}),
            "state": forms.TextInput(attrs={"placeholder": "Enter state"}),
            "pincode": forms.TextInput(attrs={
                "placeholder": "6-digit pincode",
                "inputmode": "numeric",
                "maxlength": "6"
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    @staticmethod
    def _clean_text(value):
        return re.sub(r"\s+", " ", (value or "").strip())

    def clean_name(self):
        value = self._clean_text(self.cleaned_data.get("name"))
        if not value:
            raise forms.ValidationError("Location name is required.")

        qs = Location.objects.all()
        if self.user is not None:
            qs = qs.filter(owner=self.user)
        elif getattr(self.instance, "owner_id", None):
            qs = qs.filter(owner=self.instance.owner)

        qs = qs.filter(name__iexact=value)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("A location with this name already exists.")
        return value

    def clean_address_line_1(self):
        value = self._clean_text(self.cleaned_data.get("address_line_1"))
        if not value:
            raise forms.ValidationError("Address line 1 is required.")
        return value

    def clean_address_line_2(self):
        return self._clean_text(self.cleaned_data.get("address_line_2"))

    def clean_landmark(self):
        return self._clean_text(self.cleaned_data.get("landmark"))

    def clean_city(self):
        value = self._clean_text(self.cleaned_data.get("city"))
        if not value:
            raise forms.ValidationError("City is required.")
        if not re.fullmatch(r"[A-Za-z .'-]+", value):
            raise forms.ValidationError(
                "City can contain only letters, spaces, dots, apostrophes, and hyphens."
            )
        return value.title()

    def clean_state(self):
        value = self._clean_text(self.cleaned_data.get("state"))
        if not value:
            raise forms.ValidationError("State is required.")
        if not re.fullmatch(r"[A-Za-z .'-]+", value):
            raise forms.ValidationError(
                "State can contain only letters, spaces, dots, apostrophes, and hyphens."
            )
        return value.title()

    def clean_pincode(self):
        value = re.sub(r"\D", "", self.cleaned_data.get("pincode") or "")
        if not value:
            raise forms.ValidationError("Pincode is required.")
        if len(value) != 6:
            raise forms.ValidationError("Pincode must be exactly 6 digits.")
        return value


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




FIRM_GST_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
FIRM_PAN_RE = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")
FIRM_TAN_RE = re.compile(r"^[A-Z]{4}\d{5}[A-Z]$")
FIRM_IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
FIRM_PHONE_RE = re.compile(r"^\d{10}$")
FIRM_PINCODE_RE = re.compile(r"^\d{6}$")
FIRM_ACCOUNT_RE = re.compile(r"^\d{6,30}$")
FIRM_CIN_RE = re.compile(r"^[A-Z][A-Z0-9]{20}$")
FIRM_TEXT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9&.,()'\/\-\s]{1,119}$")
FIRM_PLACE_RE = re.compile(r"^[A-Za-z][A-Za-z.()'\/\-\s]{1,99}$")
PROFILE_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z.'\-\s]{0,79}$")


def _compact_spaces(value):
    return " ".join((value or "").strip().split())
class FirmForm(forms.ModelForm):
    class Meta:
        model = Firm
        fields = [
            "firm_name", "firm_type",
            "address_line", "city", "state", "pincode",
            "phone", "email", "website",
            "gst_number", "pan_number", "tan_number", "cin_number",
            "bank_name", "account_holder_name", "account_number", "ifsc_code", "branch_name",
        ]
        widgets = {
            "firm_name": forms.TextInput(attrs={"placeholder": "Enter firm name", "maxlength": "180"}),
            "firm_type": forms.Select(),
            "address_line": forms.TextInput(attrs={"placeholder": "Address line", "maxlength": "255"}),
            "city": forms.TextInput(attrs={"placeholder": "City", "maxlength": "100"}),
            "state": forms.TextInput(attrs={"placeholder": "State", "maxlength": "100"}),
            "pincode": forms.TextInput(attrs={"placeholder": "395003", "maxlength": "6", "inputmode": "numeric"}),
            "phone": forms.TextInput(attrs={"placeholder": "9876543210", "maxlength": "10", "inputmode": "numeric"}),
            "email": forms.EmailInput(attrs={"placeholder": "name@firm.com", "maxlength": "254"}),
            "website": forms.URLInput(attrs={"placeholder": "https://example.com", "maxlength": "200"}),
            "gst_number": forms.TextInput(attrs={"placeholder": "27ABCDE1234F1Z5", "maxlength": "15", "autocapitalize": "characters"}),
            "pan_number": forms.TextInput(attrs={"placeholder": "ABCDE1234F", "maxlength": "10", "autocapitalize": "characters"}),
            "tan_number": forms.TextInput(attrs={"placeholder": "ABCD12345E", "maxlength": "10", "autocapitalize": "characters"}),
            "cin_number": forms.TextInput(attrs={"placeholder": "L17110MH1973PLC019786", "maxlength": "21", "autocapitalize": "characters"}),
            "bank_name": forms.TextInput(attrs={"placeholder": "Bank name", "maxlength": "120"}),
            "account_holder_name": forms.TextInput(attrs={"placeholder": "Account holder name", "maxlength": "120"}),
            "account_number": forms.TextInput(attrs={"placeholder": "Account number", "maxlength": "30", "inputmode": "numeric"}),
            "ifsc_code": forms.TextInput(attrs={"placeholder": "SBIN0001234", "maxlength": "11", "autocapitalize": "characters"}),
            "branch_name": forms.TextInput(attrs={"placeholder": "Branch name", "maxlength": "120"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing_class} jf-input".strip()

        self.fields["firm_name"].required = True
        self.fields["firm_type"].required = True

    def clean_firm_name(self):
        value = _compact_spaces(self.cleaned_data.get("firm_name"))
        if not value:
            raise forms.ValidationError("Firm name is required.")
        if len(value) < 2:
            raise forms.ValidationError("Firm name must be at least 2 characters long.")
        return value

    def clean_address_line(self):
        value = _compact_spaces(self.cleaned_data.get("address_line"))
        if value and len(value) < 5:
            raise forms.ValidationError("Address line must be at least 5 characters long.")
        return value

    def clean_city(self):
        value = _compact_spaces(self.cleaned_data.get("city"))
        if value and not FIRM_PLACE_RE.match(value):
            raise forms.ValidationError("Enter a valid city name.")
        return value

    def clean_state(self):
        value = _compact_spaces(self.cleaned_data.get("state"))
        if value and not FIRM_PLACE_RE.match(value):
            raise forms.ValidationError("Enter a valid state name.")
        return value

    def clean_pincode(self):
        value = (self.cleaned_data.get("pincode") or "").strip()
        if value and not FIRM_PINCODE_RE.match(value):
            raise forms.ValidationError("Pincode must be exactly 6 digits.")
        return value

    def clean_phone(self):
        value = (self.cleaned_data.get("phone") or "").strip()
        if value and not FIRM_PHONE_RE.match(value):
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        return value

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip().lower()

    def clean_website(self):
        return (self.cleaned_data.get("website") or "").strip()

    def clean_gst_number(self):
        value = (self.cleaned_data.get("gst_number") or "").strip().upper()
        if value and not FIRM_GST_RE.match(value):
            raise forms.ValidationError("Enter a valid GST number, like 27ABCDE1234F1Z5.")
        return value

    def clean_pan_number(self):
        value = (self.cleaned_data.get("pan_number") or "").strip().upper()
        if value and not FIRM_PAN_RE.match(value):
            raise forms.ValidationError("Enter a valid PAN number, like ABCDE1234F.")
        return value

    def clean_tan_number(self):
        value = (self.cleaned_data.get("tan_number") or "").strip().upper()
        if value and not FIRM_TAN_RE.match(value):
            raise forms.ValidationError("Enter a valid TAN number, like ABCD12345E.")
        return value

    def clean_cin_number(self):
        value = (self.cleaned_data.get("cin_number") or "").strip().upper()
        if value and not FIRM_CIN_RE.match(value):
            raise forms.ValidationError("Enter a valid CIN number with 21 characters.")
        return value

    def clean_bank_name(self):
        value = _compact_spaces(self.cleaned_data.get("bank_name"))
        if value and not FIRM_TEXT_RE.match(value):
            raise forms.ValidationError("Enter a valid bank name.")
        return value

    def clean_account_holder_name(self):
        value = _compact_spaces(self.cleaned_data.get("account_holder_name"))
        if value and not FIRM_TEXT_RE.match(value):
            raise forms.ValidationError("Enter a valid account holder name.")
        return value

    def clean_account_number(self):
        value = (self.cleaned_data.get("account_number") or "").strip()
        if value and not FIRM_ACCOUNT_RE.match(value):
            raise forms.ValidationError("Account number must contain only digits and be 6 to 30 digits long.")
        return value

    def clean_ifsc_code(self):
        value = (self.cleaned_data.get("ifsc_code") or "").strip().upper()
        if value and not FIRM_IFSC_RE.match(value):
            raise forms.ValidationError("Enter a valid IFSC code, like SBIN0001234.")
        return value

    def clean_branch_name(self):
        value = _compact_spaces(self.cleaned_data.get("branch_name"))
        if value and not FIRM_TEXT_RE.match(value):
            raise forms.ValidationError("Enter a valid branch name.")
        return value

    def clean(self):
        cleaned = super().clean()
        address_line = cleaned.get("address_line") or ""
        city = cleaned.get("city") or ""
        state = cleaned.get("state") or ""
        pincode = cleaned.get("pincode") or ""

        if any([city, state, pincode]) and not address_line:
            self.add_error("address_line", "Address line is required when city, state, or pincode is filled.")

        return cleaned


class DashboardProfileForm(forms.Form):
    first_name = forms.CharField(required=False, max_length=150)
    last_name = forms.CharField(required=False, max_length=150)
    email = forms.EmailField(required=False, max_length=254)
    phone = forms.CharField(required=False, max_length=10)
    address = forms.CharField(required=False, max_length=500)

    def clean_first_name(self):
        value = _compact_spaces(self.cleaned_data.get("first_name"))
        if value and not PROFILE_NAME_RE.match(value):
            raise forms.ValidationError("First name should contain letters only.")
        return value

    def clean_last_name(self):
        value = _compact_spaces(self.cleaned_data.get("last_name"))
        if value and not PROFILE_NAME_RE.match(value):
            raise forms.ValidationError("Last name should contain letters only.")
        return value

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip().lower()

    def clean_phone(self):
        value = (self.cleaned_data.get("phone") or "").strip()
        if value and not FIRM_PHONE_RE.match(value):
            raise forms.ValidationError("Mobile number must be exactly 10 digits.")
        return value

    def clean_address(self):
        value = _compact_spaces(self.cleaned_data.get("address"))
        if value and len(value) < 5:
            raise forms.ValidationError("Address must be at least 5 characters long.")
        return value
# ============================================================
# UTILITIES: MATERIAL SHADE / MATERIAL TYPE
# ============================================================
class MaterialShadeForm(forms.ModelForm):
    class Meta:
        model = MaterialShade
        fields = ["material_kind", "name", "code", "notes"]
        widgets = {
            "material_kind": forms.RadioSelect(
                choices=[("", "All")] + list(Material.MATERIAL_KIND_CHOICES)
            ),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["material_kind"].required = False


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
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter main category name",
            }),
            "description": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Add short description or notes",
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
    terms_template = forms.ModelChoiceField(
        queryset=TermsCondition.objects.none(),
        required=False,
        empty_label="Select saved terms",
        label="Saved Terms & Conditions",
    )

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
            "po_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date", "readonly": "readonly"}
            ),
            "cancel_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "shipping_address": forms.Textarea(attrs={"rows": 2, "placeholder": "Delivery or shipping address"}),
            "remarks": forms.Textarea(attrs={"rows": 2, "placeholder": "Short note for this PO"}),
            "terms_conditions": forms.Textarea(attrs={"rows": 3, "placeholder": "Payment, delivery, packing, or other terms"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["vendor"].queryset = Vendor.objects.filter(owner=user, is_active=True).order_by("name") if user else Vendor.objects.none()
        self.fields["firm"].queryset = Firm.objects.filter(owner=user).order_by("firm_name") if user else Firm.objects.none()
        self.fields["terms_template"].queryset = TermsCondition.objects.filter(owner=user, is_active=True).order_by("title") if user else TermsCondition.objects.none()
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

        self.fields["terms_template"].widget.attrs.update({
            "data-terms-template-select": "1",
        })

        if self.instance.pk and self.instance.terms_conditions:
            matched = self.fields["terms_template"].queryset.filter(content=self.instance.terms_conditions).first()
            if matched:
                self.initial["terms_template"] = matched.pk

        if not self.is_bound:
            from django.utils import timezone
            today = timezone.localdate()
            self.initial["po_date"] = today
            self.fields["po_date"].initial = today
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
        fields = ["vendor", "inward_type", "inward_date", "notes"]
        widgets = {
            "inward_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional inward notes"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vendor"].required = True
        self.fields["vendor"].queryset = (
            Vendor.objects.filter(owner=user, is_active=True).order_by("name")
            if user is not None else Vendor.objects.none()
        )
        self.fields["vendor"].empty_label = "Select inward vendor"

        self.fields["inward_type"].required = True
        self.fields["inward_type"].queryset = (
            InwardType.objects.filter(owner=user).order_by("name")
            if user is not None else InwardType.objects.none()
        )
        self.fields["inward_type"].empty_label = "Select inward type"
        
class YarnPurchaseOrderItemForm(forms.ModelForm):
    unit = forms.ChoiceField(
        required=False,
        choices=[("", "Select unit")],
    )

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

        unit_choices = _material_unit_choices(user, current_unit)

        self.fields["unit"].required = False
        self.fields["unit"].choices = unit_choices
        self.fields["unit"].widget = forms.Select(choices=unit_choices)

    def clean_unit(self):
        value = (self.cleaned_data.get("unit") or "").strip()
        valid_units = {choice for choice, _label in self.fields["unit"].choices if choice}

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
            "shipping_address",
            "delivery_period",
            "expected_delivery_date",
            "cancel_date",
            "validity_period",
            "delivery_schedule",
        ]
        widgets = {
            "po_date": forms.DateInput(attrs={"type": "date"}),
            "expected_delivery_date": forms.DateInput(attrs={"type": "date"}),
            "cancel_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user=None, source_yarn_po=None, lock_source=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["vendor"].queryset = (
            Vendor.objects.filter(owner=user, is_active=True).order_by("name")
            if user else Vendor.objects.none()
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

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)


class DyeingPurchaseOrderForm(forms.ModelForm):
    source_greige_inward = forms.ModelChoiceField(
        queryset=GreigePOInward.objects.none(),
        required=False,
        widget=forms.HiddenInput(),
    )
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

        source_greige_po = (
            source_greige_po
            or self.initial.get("source_greige_po")
            or getattr(self.instance, "source_greige_po", None)
        )

        if "source_greige_inward" in self.fields:
            if source_greige_po is not None:
                self.fields["source_greige_inward"].queryset = source_greige_po.inwards.all().order_by("-inward_date", "-id")
            else:
                self.fields["source_greige_inward"].queryset = GreigePOInward.objects.none()

        if getattr(self.instance, "source_greige_inward_id", None):
            self.fields["source_greige_inward"].initial = self.instance.source_greige_inward_id

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

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

class GreigePOReviewForm(forms.Form):
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

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

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


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter expense name (e.g. Electricity, Rent)",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Expense name is required.")

        if self.user is not None:
            qs = Expense.objects.filter(owner=self.user, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This expense already exists.")

        return name

class CatalogueForm(forms.ModelForm):
    class Meta:
        model = Catalogue
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Enter catalogue name"}),
            "description": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Add description or notes",
                }
            ),
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
    
class BOMForm(forms.ModelForm):
    class Meta:
        model = BOM
        fields = [
            "sku_code",
            "size_type",
            "catalogue_name",
            "catalogue",
            "brand",
            "category",
            "main_category",
            "gender",
            "sub_category",
            "sub_category_master",
            "pattern_type",
            "character_name",
            "license_name",
            "product_name",
            "color_name",
            "booked_price",
            "color_price",
            "accessories_price",
            "selling_price",
            "maintenance_price",
            "available_stock",
            "damage_percent",
            "product_image",
            "size_chart_image",
            "notes",
            "is_discontinued",
        ]
        widgets = {
            "sku_code": forms.TextInput(attrs={"placeholder": "Enter SKU"}),
            "size_type": forms.Select(),
            "catalogue_name": forms.HiddenInput(),
            "catalogue": forms.Select(),
            "brand": forms.Select(),
            "category": forms.Select(),
            "main_category": forms.Select(),
            "gender": forms.Select(),
            "sub_category": forms.HiddenInput(),
            "sub_category_master": forms.Select(),
            "pattern_type": forms.Select(),
            "character_name": forms.TextInput(attrs={"placeholder": "Enter character name"}),
            "license_name": forms.TextInput(attrs={"placeholder": "Enter license name"}),
            "product_name": forms.TextInput(attrs={"placeholder": "Enter product name"}),
            "color_name": forms.TextInput(attrs={"placeholder": "Enter color"}),
            "booked_price": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "MRP"}),
            "color_price": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Color / Drawcord / Tie Dye Price"}),
            "accessories_price": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Accessories Price"}),
            "selling_price": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Selling Price"}),
            "maintenance_price": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Maintenance Price"}),
            "available_stock": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Available Stock"}),
            "damage_percent": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Damage %"}),
            "product_image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "size_chart_image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "notes": forms.Textarea(attrs={"rows": 4, "placeholder": "Optional notes"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        self.fields["catalogue"].queryset = (
            Catalogue.objects.filter(owner=user).order_by("name")
            if user else Catalogue.objects.none()
        )
        self.fields["brand"].queryset = (
            Brand.objects.filter(owner=user).order_by("name")
            if user else Brand.objects.none()
        )
        self.fields["category"].queryset = (
            Category.objects.filter(owner=user).order_by("name")
            if user else Category.objects.none()
        )
        self.fields["main_category"].queryset = (
            MainCategory.objects.filter(owner=user).order_by("name")
            if user else MainCategory.objects.none()
        )
        self.fields["sub_category_master"].queryset = (
            SubCategory.objects.filter(owner=user).select_related("main_category").order_by("main_category__name", "name")
            if user else SubCategory.objects.none()
        )
        self.fields["pattern_type"].queryset = (
            PatternType.objects.filter(owner=user).order_by("name")
            if user else PatternType.objects.none()
        )

        self.fields["catalogue"].required = False
        self.fields["brand"].required = False
        self.fields["category"].required = False
        self.fields["main_category"].required = False
        self.fields["sub_category_master"].required = False
        self.fields["pattern_type"].required = False

        self.fields["catalogue"].empty_label = "Select catalogue"
        self.fields["brand"].empty_label = "Select brand"
        self.fields["category"].empty_label = "Select category"
        self.fields["main_category"].empty_label = "Select main category"
        self.fields["sub_category_master"].empty_label = "Select sub category"
        self.fields["pattern_type"].empty_label = "Select pattern type"

        for field_name, placeholder in {
            "sku_code": "Enter SKU",
            "character_name": "Enter character name",
            "license_name": "Enter license name",
            "product_name": "Enter product name",
            "color_name": "Enter color",
        }.items():
            self.fields[field_name].widget.attrs.setdefault("placeholder", placeholder)

        for field_name in [
            "booked_price",
            "color_price",
            "accessories_price",
            "selling_price",
            "maintenance_price",
            "available_stock",
            "damage_percent",
        ]:
            self.fields[field_name].widget.attrs.update({"step": "0.01", "min": "0"})

        for field_name in [
            "catalogue",
            "brand",
            "category",
            "main_category",
            "gender",
            "sub_category_master",
            "pattern_type",
            "size_type",
        ]:
            self.fields[field_name].widget.attrs.setdefault("data-master-field", "1")

        if self.instance.pk and self.instance.catalogue_id:
            self.initial["catalogue"] = self.instance.catalogue_id
        if self.instance.pk and self.instance.sub_category_master_id:
            self.initial["sub_category_master"] = self.instance.sub_category_master_id

    def clean_sku_code(self):
        value = (self.cleaned_data.get("sku_code") or "").strip().upper()
        if not value:
            raise forms.ValidationError("SKU is required.")

        qs = BOM.objects.filter(owner=self.user, sku_code__iexact=value) if self.user else BOM.objects.none()
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This SKU already exists.")
        return value

    def clean_product_name(self):
        return (self.cleaned_data.get("product_name") or "").strip()

    def clean_character_name(self):
        return (self.cleaned_data.get("character_name") or "").strip()

    def clean_license_name(self):
        return (self.cleaned_data.get("license_name") or "").strip()

    def clean_color_name(self):
        return (self.cleaned_data.get("color_name") or "").strip()

    def clean(self):
        cleaned = super().clean()
        catalogue = cleaned.get("catalogue")
        sub_category_master = cleaned.get("sub_category_master")
        main_category = cleaned.get("main_category")

        cleaned["catalogue_name"] = catalogue.name if catalogue else (cleaned.get("catalogue_name") or "")
        cleaned["sub_category"] = sub_category_master.name if sub_category_master else (cleaned.get("sub_category") or "")

        if sub_category_master and main_category and sub_category_master.main_category_id != main_category.id:
            self.add_error("sub_category_master", "Selected sub category does not belong to selected main category.")

        return cleaned


class BOMMaterialItemForm(forms.ModelForm):
    class Meta:
        model = BOMMaterialItem
        fields = ["item_type", "material", "unit", "cost_per_uom", "average", "cost", "notes"]
        widgets = {
            "item_type": forms.HiddenInput(),
            "material": forms.Select(),
            "unit": forms.Select(),
            "cost_per_uom": forms.NumberInput(attrs={
                "step": "0.01",
                "min": "0",
                "placeholder": "Cost Per UOM",
                "class": "js-bom-cost-per-uom",
            }),
            "average": forms.NumberInput(attrs={
                "step": "0.01",
                "min": "0",
                "placeholder": "Average",
                "class": "js-bom-average",
            }),
            "cost": forms.NumberInput(attrs={
                "step": "0.01",
                "min": "0",
                "placeholder": "Cost",
                "class": "js-bom-cost",
                "readonly": "readonly",
            }),
            "notes": forms.HiddenInput(),
        }

    def __init__(self, *args, user=None, forced_item_type=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["unit"].queryset = (
            MaterialUnit.objects.filter(owner=user).order_by("name")
            if user else MaterialUnit.objects.none()
        )
        self.fields["unit"].required = False
        self.fields["unit"].empty_label = "Select UOM"

        qs = Material.objects.select_related("material_type", "material_sub_type").order_by("name")

        if forced_item_type == BOMMaterialItem.ItemType.RAW_FABRIC:
            qs = qs.order_by("name")
        elif forced_item_type == BOMMaterialItem.ItemType.ACCESSORY:
            qs = qs.order_by("name")

        self.fields["material"].queryset = qs
        self.fields["material"].empty_label = "Select material"
        self.fields["material"].label_from_instance = (
            lambda obj: f"{obj.name} ({obj.get_material_kind_display()})"
        )

        if forced_item_type:
            self.fields["item_type"].initial = forced_item_type
            self.initial["item_type"] = forced_item_type

    def clean(self):
        cleaned = super().clean()
        cost_per_uom = cleaned.get("cost_per_uom") or 0
        average = cleaned.get("average") or 0
        cleaned["cost"] = cost_per_uom * average
        return cleaned


class BOMJobberItemForm(forms.ModelForm):
    class Meta:
        model = BOMJobberItem
        fields = ["jobber", "jobber_type", "price"]
        widgets = {
            "price": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "class": "js-bom-jobber-price", "placeholder": "Mapped price"}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["jobber"].queryset = (
            Jobber.objects.filter(owner=user).order_by("name")
            if user else Jobber.objects.none()
        )
        self.fields["jobber_type"].queryset = (
            JobberType.objects.filter(owner=user).order_by("name")
            if user else JobberType.objects.none()
        )
        self.fields["jobber"].required = False
        self.fields["jobber_type"].required = False
        self.fields["jobber"].empty_label = "Select jobber"
        self.fields["jobber_type"].empty_label = "Select type"
        self.fields["jobber"].widget.attrs.setdefault("data-jobber-field", "1")
        self.fields["jobber_type"].widget.attrs.setdefault("data-jobber-type-field", "1")
        self.fields["price"].widget.attrs.setdefault("data-jobber-price-field", "1")

    def clean(self):
        cleaned = super().clean()
        jobber = cleaned.get("jobber")
        jobber_type = cleaned.get("jobber_type")

        if jobber and not jobber_type:
            cleaned["jobber_type"] = jobber.jobber_type
            self.instance.jobber_type = jobber.jobber_type

        return cleaned


class BOMProcessItemForm(forms.ModelForm):
    class Meta:
        model = BOMProcessItem
        fields = ["jobber_type", "price"]
        widgets = {
            "price": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "class": "js-bom-process-price", "placeholder": "Type price"}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["jobber_type"].queryset = (
            JobberType.objects.filter(owner=user).order_by("name")
            if user else JobberType.objects.none()
        )
        self.fields["jobber_type"].empty_label = "Select jobber type"
        self.fields["jobber_type"].widget.attrs.setdefault("data-process-jobber-type", "1")
        self.fields["price"].widget.attrs.setdefault("data-process-price", "1")


class BOMExpenseItemForm(forms.ModelForm):
    class Meta:
        model = BOMExpenseItem
        fields = ["expense", "expense_name", "price"]
        widgets = {
            "expense_name": forms.HiddenInput(),
            "price": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "class": "js-bom-expense-price", "placeholder": "Expense price"}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["expense"].queryset = (
            Expense.objects.filter(owner=user).order_by("name")
            if user else Expense.objects.none()
        )
        self.fields["expense"].required = False
        self.fields["expense"].empty_label = "Select Expense Type"

    def clean(self):
        cleaned = super().clean()
        expense = cleaned.get("expense")
        if expense:
            cleaned["expense_name"] = expense.name
            self.instance.expense_name = expense.name
        return cleaned


BOMMaterialItemFormSet = inlineformset_factory(
    BOM,
    BOMMaterialItem,
    form=BOMMaterialItemForm,
    extra=2,
    can_delete=True,
)

BOMJobberItemFormSet = inlineformset_factory(
    BOM,
    BOMJobberItem,
    form=BOMJobberItemForm,
    extra=1,
    can_delete=True,
)

BOMProcessItemFormSet = inlineformset_factory(
    BOM,
    BOMProcessItem,
    form=BOMProcessItemForm,
    extra=1,
    can_delete=True,
)

BOMExpenseItemFormSet = inlineformset_factory(
    BOM,
    BOMExpenseItem,
    form=BOMExpenseItemForm,
    extra=1,
    can_delete=True,
)


class BOMImageForm(forms.ModelForm):
    class Meta:
        model = BOMImage
        fields = ["image", "caption"]
        widgets = {
            "image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "caption": forms.TextInput(attrs={"placeholder": "Optional caption"}),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            return image
        content_type = getattr(image, "content_type", "") or ""
        if content_type and not content_type.startswith("image/"):
            raise forms.ValidationError("The selected file must be an image.")
        return image


BOMImageFormSet = inlineformset_factory(
    BOM,
    BOMImage,
    form=BOMImageForm,
    extra=1,
    can_delete=True,
)

# ============================================================
# PROGRAM
# ============================================================

class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = [
            "program_no",
            "program_date",
            "bom",
            "firm",
            "total_qty",
            "ratio",
            "damage",
        ]
        widgets = {
            "program_no": forms.TextInput(attrs={"placeholder": "Enter program number"}),
            "program_date": forms.DateInput(attrs={"type": "date"}),
            "total_qty": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Total Qty"}),
            "ratio": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Ratio"}),
            "damage": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Damage"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        self.fields["bom"].queryset = (
            BOM.objects.filter(owner=user).order_by("-id")
            if user else BOM.objects.none()
        )
        self.fields["firm"].queryset = (
            Firm.objects.filter(owner=user).order_by("firm_name")
            if user else Firm.objects.none()
        )

        self.fields["bom"].empty_label = "Select SKU"
        self.fields["firm"].empty_label = "Select firm"

        self.fields["bom"].label_from_instance = (
            lambda obj: f"{obj.sku_code} - {obj.product_name}" if obj.product_name else obj.sku_code
        )

        if not self.is_bound:
            from django.utils import timezone
            self.fields["program_date"].initial = timezone.localdate()

            firm = self.fields["firm"].queryset.first()
            if firm and not self.initial.get("firm"):
                self.fields["firm"].initial = firm.pk

    def clean_program_no(self):
        value = (self.cleaned_data.get("program_no") or "").strip()
        if not value:
            raise forms.ValidationError("Program number is required.")

        qs = Program.objects.all()
        if self.user is not None:
            qs = qs.filter(owner=self.user)

        qs = qs.filter(program_no__iexact=value)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("This program number already exists.")

        return value

    def clean_bom(self):
        bom = self.cleaned_data.get("bom")
        if bom and self.user is not None and bom.owner_id != self.user.id:
            raise forms.ValidationError("Selected SKU is not available for this user.")
        return bom

    def clean_firm(self):
        firm = self.cleaned_data.get("firm")
        if firm and self.user is not None and firm.owner_id != self.user.id:
            raise forms.ValidationError("Selected firm is not available for this user.")
        return firm


class ProgramJobberItemForm(forms.ModelForm):
    class Meta:
        model = ProgramJobberItem
        fields = ["jobber", "jobber_type", "jobber_price", "issue_qty", "inward_qty"]
        widgets = {
            "jobber_price": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Jobber Price"}),
            "issue_qty": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Issue"}),
            "inward_qty": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Inward"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["jobber"].queryset = (
            Jobber.objects.filter(owner=user, is_active=True).order_by("name")
            if user else Jobber.objects.none()
        )
        self.fields["jobber_type"].queryset = (
            JobberType.objects.filter(owner=user).order_by("name")
            if user else JobberType.objects.none()
        )

        self.fields["jobber"].required = False
        self.fields["jobber_type"].required = False
        self.fields["jobber"].empty_label = "Select jobber"
        self.fields["jobber_type"].empty_label = "Select jobber type"

    def clean(self):
        cleaned = super().clean()
        jobber = cleaned.get("jobber")
        jobber_type = cleaned.get("jobber_type")

        if jobber and not jobber_type:
            cleaned["jobber_type"] = jobber.jobber_type

        return cleaned


class ProgramSizeDetailForm(forms.ModelForm):
    class Meta:
        model = ProgramSizeDetail
        fields = ["size", "cq", "fq", "dq", "fq_dq", "tp"]
        widgets = {
            "size": forms.Select(),
            "cq": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "CQ"}),
            "fq": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "FQ"}),
            "dq": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "DQ"}),
            "fq_dq": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "FQ-DQ"}),
            "tp": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "TP"}),
        }


ProgramJobberItemFormSet = inlineformset_factory(
    Program,
    ProgramJobberItem,
    form=ProgramJobberItemForm,
    fields=["jobber", "jobber_type", "jobber_price", "issue_qty", "inward_qty"],
    extra=1,
    can_delete=True,
)

ProgramSizeDetailFormSet = inlineformset_factory(
    Program,
    ProgramSizeDetail,
    form=ProgramSizeDetailForm,
    fields=["size", "cq", "fq", "dq", "fq_dq", "tp"],
    extra=9,
    can_delete=True,
)

class DyeingOtherChargeForm(forms.ModelForm):
    class Meta:
        model = DyeingOtherCharge
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter other charge name (e.g. Silicon Wash, Bio Wash)",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Other charge name is required.")

        if self.user is not None:
            qs = DyeingOtherCharge.objects.filter(owner=self.user, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This dyeing other charge already exists.")

        return name


class TermsConditionForm(forms.ModelForm):
    class Meta:
        model = TermsCondition
        fields = ["title", "content"]
        widgets = {
            "title": forms.TextInput(attrs={
                "placeholder": "Enter terms title",
            }),
            "content": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": "Enter terms and conditions content",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_title(self):
        title = (self.cleaned_data.get("title") or "").strip()
        if not title:
            raise forms.ValidationError("Title is required.")

        if self.user is not None:
            qs = TermsCondition.objects.filter(owner=self.user, title__iexact=title)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This terms title already exists.")

        return title

    def clean_content(self):
        content = (self.cleaned_data.get("content") or "").strip()
        if not content:
            raise forms.ValidationError("Terms content is required.")
        return content
    
    
class InwardTypeForm(forms.ModelForm):
    class Meta:
        model = InwardType
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter inward type name (e.g. GRN, Return Inward)",
            }),
            "description": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Optional note about when this inward type should be used",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Inward type name is required.")

        if self.user is not None:
            qs = InwardType.objects.filter(owner=self.user, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This inward type already exists.")

        return name
    
class SubCategoryForm(forms.ModelForm):
    class Meta:
        model = SubCategory
        fields = ["main_category", "name", "description"]
        widgets = {
            "main_category": forms.Select(),
            "name": forms.TextInput(attrs={
                "placeholder": "Enter sub category name",
            }),
            "description": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Add short description or notes",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        main_category_qs = MainCategory.objects.filter(owner=user).order_by("name") if user else MainCategory.objects.none()
        self.fields["main_category"].queryset = main_category_qs
        self.fields["main_category"].empty_label = "Select Main Category"

    def clean(self):
        cleaned_data = super().clean()
        main_category = cleaned_data.get("main_category")
        name = (cleaned_data.get("name") or "").strip()

        if not main_category:
            self.add_error("main_category", "Main category is required.")
        elif self.user is not None and main_category.owner_id != self.user.id:
            self.add_error("main_category", "Selected main category is not available for this user.")

        if not name:
            self.add_error("name", "Sub category name is required.")

        if self.user is not None and main_category and name:
            qs = SubCategory.objects.filter(
                owner=self.user,
                main_category=main_category,
                name__iexact=name,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("name", "This sub category already exists under the selected main category.")

        return cleaned_data