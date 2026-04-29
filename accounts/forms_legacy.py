import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from django.utils import timezone
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Q
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import (
    Accessory,
    BOM,
    BOMAccessoryItem,
    BOMImage,
    BOMMaterialItem,
    BOMJobberTypeProcess,
    BOMJobberDetail,
    BOMExpenseItem,
    Brand,
    Catalogue,
    Category,
    MaintenanceExpenseItem,
    Client,
    DispatchChallan,
    DyeingMaterialLink,
    DyeingMaterialLinkDetail,
    DyeingOtherCharge,
    DyeingPurchaseOrder,
    DyeingPurchaseOrderItem,
    DyeingPOInward,
    Expense,
    FinishedDetail,
    Firm,
    FirmAddress,
    GreigeDetail,
    GreigePOInward,
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
    Program,
    ProgramJobberDetail,
    ProgramStart,
    ProgramStartFabric,
    ProgramStartSize,
    ProgramStartJobber,
    ProgramJobberChallan,
    ProgramJobberChallanSize,
    
    ProgramInvoice,
    ProgramInvoiceItem,
    MaintenanceRecord,
    ReadyPOInward,
    ReadyPurchaseOrder,
    SubCategory,
    TermsCondition,
    TrimDetail,
    Vendor,
    YarnDetail,
    YarnPOInward,
    YarnPurchaseOrder,
    YarnPurchaseOrderItem,
        InventoryLot,
    InventoryRoll,
    QRCodeRecord,
    QualityCheck,
    QualityCheckParameter,
    QualityCheckDefect,
    CostingSnapshot,
    DyeingPOInwardItem,
    ReadyPOInwardItem,
    ReadyPurchaseOrderItem,
        next_quality_check_number,
    next_qr_code_number,
)


# ============================================================
# SHARED REGEX / HELPERS / WIDGETS
# ============================================================

PARTY_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
PARTY_GST_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
PARTY_TAN_RE = re.compile(r"^[A-Z]{4}[0-9]{5}[A-Z]$")
PARTY_PHONE_RE = re.compile(r"^[0-9]{10,15}$")
PARTY_ACCOUNT_RE = re.compile(r"^[0-9]{6,30}$")
PARTY_IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")

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


# ============================================================
# AUTH / DASHBOARD
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
# PEOPLE / COMPANY / MASTER FORMS
# ============================================================

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
                "oninput": "this.value=this.value.replace(/\\D/g,'').slice(0,10)",
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


class JobberTypeForm(forms.ModelForm):
    class Meta:
        model = JobberType
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter process type name",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    @staticmethod
    def _clean_text(value):
        return re.sub(r"\s+", " ", (value or "").strip())

    def clean_name(self):
        name = self._clean_text(self.cleaned_data.get("name"))
        if not name:
            raise forms.ValidationError("Jobber type name is required.")

        qs = JobberType.objects.all()
        if self.user is not None:
            qs = qs.filter(owner=self.user)
        elif getattr(self.instance, "owner_id", None):
            qs = qs.filter(owner=self.instance.owner)

        qs = qs.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("This jobber type already exists.")

        return name


class JobberForm(forms.ModelForm):
    class Meta:
        model = Jobber
        fields = ["name", "jobber_type", "phone", "email", "address", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter process vendor / contractor name",
                "maxlength": "120",
            }),
            "jobber_type": forms.Select(),
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
            "address": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Enter address",
            }),
            "is_active": forms.CheckboxInput(),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        self.fields["jobber_type"].required = False
        self.fields["jobber_type"].empty_label = "Select process type"

        qs = JobberType.objects.all()
        if self.user is not None:
            qs = qs.filter(owner=self.user)
        elif getattr(self.instance, "owner_id", None):
            qs = qs.filter(owner=self.instance.owner)

        self.fields["jobber_type"].queryset = qs.order_by("name")

    @staticmethod
    def _clean_text(value):
        return re.sub(r"\s+", " ", (value or "").strip())

    def clean_name(self):
        name = self._clean_text(self.cleaned_data.get("name"))
        if not name:
            raise forms.ValidationError("Jobber name is required.")
        return name

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()

        if not phone:
            return phone

        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain digits only.")

        if len(phone) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")

        return phone

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        return email

    def clean_address(self):
        return self._clean_text(self.cleaned_data.get("address"))

    def clean_jobber_type(self):
        jobber_type = self.cleaned_data.get("jobber_type")
        if not jobber_type:
            return jobber_type

        if self.user is not None and jobber_type.owner_id != self.user.id:
            raise forms.ValidationError("Invalid jobber type selected.")

        return jobber_type

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get("name")

        if not name:
            return cleaned

        qs = Jobber.objects.all()
        if self.user is not None:
            qs = qs.filter(owner=self.user)
        elif getattr(self.instance, "owner_id", None):
            qs = qs.filter(owner=self.instance.owner)

        qs = qs.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            self.add_error("name", "A jobber with this name already exists.")

        return cleaned


class PartyForm(forms.ModelForm):
    class Meta:
        model = Party
        fields = [
            "party_code",
            "party_name",
            "party_category",
            "contact_person",
            "phone_number",
            "alt_phone",
            "email",
            "gst_number",
            "pan_number",
            "tan_number",
            "bank_name",
            "account_number",
            "ifsc_code",
            "address",
            "city",
            "state",
            "pincode",
            "remarks",
            "is_active",
        ]
        widgets = {
            "party_code": forms.TextInput(attrs={
                "placeholder": "Auto if left blank",
                "maxlength": "20",
            }),
            "party_name": forms.TextInput(attrs={
                "placeholder": "Enter party name",
                "maxlength": "150",
            }),
            "party_category": forms.Select(),
            "contact_person": forms.TextInput(attrs={
                "placeholder": "Enter contact person",
                "maxlength": "120",
            }),
            "phone_number": forms.TextInput(attrs={
                "placeholder": "Enter phone number",
                "inputmode": "numeric",
                "maxlength": "10",
                "oninput": "this.value=this.value.replace(/\\D/g,'').slice(0,10)",
            }),
            "alt_phone": forms.TextInput(attrs={
                "placeholder": "Enter alternate phone",
                "inputmode": "numeric",
                "maxlength": "10",
                "oninput": "this.value=this.value.replace(/\\D/g,'').slice(0,10)",
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "Enter email",
                "autocomplete": "email",
                "spellcheck": "false",
            }),
            "gst_number": forms.TextInput(attrs={
                "placeholder": "27ABCDE1234F1Z5",
                "maxlength": "15",
                "style": "text-transform:uppercase;",
            }),
            "pan_number": forms.TextInput(attrs={
                "placeholder": "ABCDE1234F",
                "maxlength": "10",
                "style": "text-transform:uppercase;",
            }),
            "tan_number": forms.TextInput(attrs={
                "placeholder": "ABCD12345E",
                "maxlength": "10",
                "style": "text-transform:uppercase;",
            }),
            "bank_name": forms.TextInput(attrs={
                "placeholder": "Enter bank name",
                "maxlength": "120",
            }),
            "account_number": forms.TextInput(attrs={
                "placeholder": "Enter account number",
                "inputmode": "numeric",
                "maxlength": "30",
                "oninput": "this.value=this.value.replace(/\\D/g,'').slice(0,30)",
            }),
            "ifsc_code": forms.TextInput(attrs={
                "placeholder": "SBIN0001234",
                "maxlength": "11",
                "style": "text-transform:uppercase;",
            }),
            "address": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Enter address",
            }),
            "city": forms.TextInput(attrs={
                "placeholder": "Enter city",
                "maxlength": "120",
            }),
            "state": forms.Select(),
            "pincode": forms.TextInput(attrs={
                "placeholder": "Enter pincode",
                "inputmode": "numeric",
                "maxlength": "6",
                "oninput": "this.value=this.value.replace(/\\D/g,'').slice(0,6)",
            }),
            "remarks": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Enter remarks",
            }),
            "is_active": forms.CheckboxInput(),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    @staticmethod
    def _clean_text(value):
        return re.sub(r"\s+", " ", (value or "").strip())

    def _scoped_qs(self):
        qs = Party.objects.all()
        if self.user is not None:
            return qs.filter(Q(owner=self.user) | Q(owner__isnull=True))
        if getattr(self.instance, "owner_id", None):
            return qs.filter(owner=self.instance.owner)
        return qs.none()

    def _next_party_code(self):
        max_num = 0
        for code in self._scoped_qs().values_list("party_code", flat=True):
            match = re.fullmatch(r"PTY(\d+)", (code or "").upper())
            if match:
                max_num = max(max_num, int(match.group(1)))
        return f"PTY{max_num + 1:04d}"

    def clean_party_code(self):
        code = (self.cleaned_data.get("party_code") or "").strip().upper()
        if not code:
            code = self._next_party_code()

        if not re.fullmatch(r"[A-Z0-9\\-_\\/]+", code):
            raise forms.ValidationError("Party code can contain only letters, numbers, -, _ or /.")

        qs = self._scoped_qs().filter(party_code__iexact=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("This party code already exists.")

        return code

    def clean_party_name(self):
        value = self._clean_text(self.cleaned_data.get("party_name"))
        if not value:
            raise forms.ValidationError("Party name is required.")
        return value

    def clean_contact_person(self):
        return self._clean_text(self.cleaned_data.get("contact_person"))

    def clean_phone_number(self):
        value = (self.cleaned_data.get("phone_number") or "").strip()
        if not value:
            return value
        if not re.fullmatch(r"^\d{10}$", value):
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        return value

    def clean_alt_phone(self):
        value = (self.cleaned_data.get("alt_phone") or "").strip()
        if not value:
            return value
        if not re.fullmatch(r"^\d{10}$", value):
            raise forms.ValidationError("Alternate phone must be exactly 10 digits.")
        return value

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip().lower()

    def clean_gst_number(self):
        value = (self.cleaned_data.get("gst_number") or "").strip().upper()
        if value and not PARTY_GST_RE.match(value):
            raise forms.ValidationError("Enter a valid GST number, like 27ABCDE1234F1Z5.")
        return value

    def clean_pan_number(self):
        value = (self.cleaned_data.get("pan_number") or "").strip().upper()
        if value and not PARTY_PAN_RE.match(value):
            raise forms.ValidationError("Enter a valid PAN number, like ABCDE1234F.")
        return value

    def clean_tan_number(self):
        value = (self.cleaned_data.get("tan_number") or "").strip().upper()
        if value and not PARTY_TAN_RE.match(value):
            raise forms.ValidationError("Enter a valid TAN number, like ABCD12345E.")
        return value

    def clean_bank_name(self):
        return self._clean_text(self.cleaned_data.get("bank_name"))

    def clean_account_number(self):
        value = (self.cleaned_data.get("account_number") or "").strip()
        if value and not PARTY_ACCOUNT_RE.match(value):
            raise forms.ValidationError("Account number must contain only digits and be 6 to 30 digits long.")
        return value

    def clean_ifsc_code(self):
        value = (self.cleaned_data.get("ifsc_code") or "").strip().upper()
        if value and not PARTY_IFSC_RE.match(value):
            raise forms.ValidationError("Enter a valid IFSC code, like SBIN0001234.")
        return value

    def clean_address(self):
        return self._clean_text(self.cleaned_data.get("address"))

    def clean_city(self):
        return self._clean_text(self.cleaned_data.get("city"))

    def clean_pincode(self):
        value = (self.cleaned_data.get("pincode") or "").strip()
        if not value:
            return value
        if not re.fullmatch(r"^\d{6}$", value):
            raise forms.ValidationError("Pincode must be exactly 6 digits.")
        return value

    def clean_remarks(self):
        return self._clean_text(self.cleaned_data.get("remarks"))

    def clean(self):
        cleaned = super().clean()

        name = cleaned.get("party_name")
        phone = cleaned.get("phone_number")
        alt_phone = cleaned.get("alt_phone")

        if name:
            qs = self._scoped_qs().filter(party_name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("party_name", "A party with this name already exists.")

        if phone and alt_phone and phone == alt_phone:
            self.add_error("alt_phone", "Alternate phone cannot be the same as primary phone.")

        return cleaned


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
                "maxlength": "6",
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


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = [
            "vendor_code",
            "name",
            "vendor_type",
            "contact_person",
            "phone",
            "alt_phone",
            "email",
            "gst_number",
            "pan_number",
            "address",
            "city",
            "state",
            "pincode",
            "payment_terms",
            "credit_days",
            "lead_time_days",
            "remarks",
            "is_active",
        ]
        widgets = {
            "vendor_code": forms.TextInput(attrs={
                "placeholder": "Auto if left blank",
                "maxlength": "20",
            }),
            "name": forms.TextInput(attrs={
                "placeholder": "Enter vendor name",
                "maxlength": "180",
            }),
            "vendor_type": forms.Select(),
            "contact_person": forms.TextInput(attrs={
                "placeholder": "Enter contact person",
                "maxlength": "120",
            }),
            "phone": forms.TextInput(attrs={
                "placeholder": "Enter mobile number",
                "inputmode": "numeric",
                "maxlength": "10",
                "oninput": "this.value=this.value.replace(/\\D/g,'').slice(0,10)",
            }),
            "alt_phone": forms.TextInput(attrs={
                "placeholder": "Enter alternate mobile",
                "inputmode": "numeric",
                "maxlength": "10",
                "oninput": "this.value=this.value.replace(/\\D/g,'').slice(0,10)",
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "Enter email",
            }),
            "gst_number": forms.TextInput(attrs={
                "placeholder": "Enter GST number",
                "maxlength": "15",
                "style": "text-transform:uppercase;",
            }),
            "pan_number": forms.TextInput(attrs={
                "placeholder": "Enter PAN number",
                "maxlength": "10",
                "style": "text-transform:uppercase;",
            }),
            "address": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Enter address",
            }),
            "city": forms.TextInput(attrs={
                "placeholder": "Enter city",
                "maxlength": "120",
            }),
            "state": forms.TextInput(attrs={
                "placeholder": "Enter state",
                "maxlength": "120",
            }),
            "pincode": forms.TextInput(attrs={
                "placeholder": "Enter pincode",
                "inputmode": "numeric",
                "maxlength": "6",
                "oninput": "this.value=this.value.replace(/\\D/g,'').slice(0,6)",
            }),
            "payment_terms": forms.TextInput(attrs={
                "placeholder": "Eg. 30 days credit",
                "maxlength": "120",
            }),
            "credit_days": forms.NumberInput(attrs={
                "min": "0",
                "placeholder": "0",
            }),
            "lead_time_days": forms.NumberInput(attrs={
                "min": "0",
                "placeholder": "0",
            }),
            "remarks": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Enter remarks",
            }),
            "is_active": forms.CheckboxInput(),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    @staticmethod
    def _clean_text(value):
        return re.sub(r"\s+", " ", (value or "").strip())

    def _next_vendor_code(self):
        max_num = 0
        if self.user is None:
            return "VEN0001"

        codes = Vendor.objects.filter(owner=self.user).values_list("vendor_code", flat=True)
        for code in codes:
            match = re.fullmatch(r"VEN(\d+)", (code or "").upper())
            if match:
                max_num = max(max_num, int(match.group(1)))
        return f"VEN{max_num + 1:04d}"

    def clean_vendor_code(self):
        code = (self.cleaned_data.get("vendor_code") or "").strip().upper()
        if not code:
            code = self._next_vendor_code()

        if not re.fullmatch(r"[A-Z0-9\-_/]+", code):
            raise forms.ValidationError("Vendor code can contain only letters, numbers, -, _ or /.")

        qs = Vendor.objects.all()
        if self.user is not None:
            qs = qs.filter(owner=self.user)
        elif getattr(self.instance, "owner_id", None):
            qs = qs.filter(owner=self.instance.owner)

        qs = qs.filter(vendor_code__iexact=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("This vendor code already exists.")

        return code

    def clean_name(self):
        name = self._clean_text(self.cleaned_data.get("name"))
        if not name:
            raise forms.ValidationError("Vendor name is required.")
        return name

    def clean_contact_person(self):
        return self._clean_text(self.cleaned_data.get("contact_person"))

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            return phone
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain digits only.")
        if len(phone) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        return phone

    def clean_alt_phone(self):
        alt_phone = (self.cleaned_data.get("alt_phone") or "").strip()
        if not alt_phone:
            return alt_phone
        if not alt_phone.isdigit():
            raise forms.ValidationError("Alternate phone must contain digits only.")
        if len(alt_phone) != 10:
            raise forms.ValidationError("Alternate phone must be exactly 10 digits.")
        return alt_phone

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip().lower()

    def clean_gst_number(self):
        gst = (self.cleaned_data.get("gst_number") or "").strip().upper()
        if not gst:
            return gst
        if not re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]", gst):
            raise forms.ValidationError("Enter a valid GST number.")
        return gst

    def clean_pan_number(self):
        pan = (self.cleaned_data.get("pan_number") or "").strip().upper()
        if not pan:
            return pan
        if not re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", pan):
            raise forms.ValidationError("Enter a valid PAN number.")
        return pan

    def clean_address(self):
        return self._clean_text(self.cleaned_data.get("address"))

    def clean_city(self):
        return self._clean_text(self.cleaned_data.get("city"))

    def clean_state(self):
        return self._clean_text(self.cleaned_data.get("state"))

    def clean_pincode(self):
        pincode = (self.cleaned_data.get("pincode") or "").strip()
        if not pincode:
            return pincode
        if not pincode.isdigit():
            raise forms.ValidationError("Pincode must contain digits only.")
        if len(pincode) != 6:
            raise forms.ValidationError("Pincode must be exactly 6 digits.")
        return pincode

    def clean_payment_terms(self):
        return self._clean_text(self.cleaned_data.get("payment_terms"))

    def clean_remarks(self):
        return self._clean_text(self.cleaned_data.get("remarks"))

    def clean_credit_days(self):
        value = self.cleaned_data.get("credit_days")
        if value is None:
            return 0
        if value < 0:
            raise forms.ValidationError("Credit days cannot be negative.")
        return value

    def clean_lead_time_days(self):
        value = self.cleaned_data.get("lead_time_days")
        if value is None:
            return 0
        if value < 0:
            raise forms.ValidationError("Lead time cannot be negative.")
        return value

    def clean(self):
        cleaned = super().clean()

        name = cleaned.get("name")
        phone = cleaned.get("phone")
        alt_phone = cleaned.get("alt_phone")

        qs = Vendor.objects.all()
        if self.user is not None:
            qs = qs.filter(owner=self.user)
        elif getattr(self.instance, "owner_id", None):
            qs = qs.filter(owner=self.instance.owner)

        if name:
            dup_qs = qs.filter(name__iexact=name)
            if self.instance.pk:
                dup_qs = dup_qs.exclude(pk=self.instance.pk)
            if dup_qs.exists():
                self.add_error("name", "A vendor with this name already exists.")

        if phone and alt_phone and phone == alt_phone:
            self.add_error("alt_phone", "Alternate phone cannot be the same as primary phone.")

        return cleaned


# ============================================================
# UTILITIES / CLASSIFICATION FORMS
# ============================================================

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


class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter brand name",
                "maxlength": 120,
                "autocomplete": "off",
            }),
            "description": forms.Textarea(attrs={
                "placeholder": "Optional short description",
                "rows": 3,
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        self.fields["name"].required = True
        self.fields["description"].required = False

    def clean_name(self):
        value = (self.cleaned_data.get("name") or "").strip()
        value = " ".join(value.split())

        if not value:
            raise forms.ValidationError("Brand name is required.")

        qs = Brand.objects.filter(owner=self.user, name__iexact=value)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if self.user is not None and qs.exists():
            raise forms.ValidationError("Brand with this name already exists.")

        return value

    def clean_description(self):
        value = (self.cleaned_data.get("description") or "").strip()
        return " ".join(value.split()) if value else ""


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

class AccessoryForm(forms.ModelForm):
    class Meta:
        model = Accessory
        fields = ["name", "default_unit", "description"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter accessory name (e.g. Drawcord, Button, Zipper)",
            }),
            "default_unit": forms.Select(),
            "description": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Optional notes about this accessory",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        if user is not None:
            self.fields["default_unit"].queryset = MaterialUnit.objects.filter(owner=user).order_by("name")
        else:
            self.fields["default_unit"].queryset = MaterialUnit.objects.none()

        self.fields["default_unit"].required = False
        self.fields["default_unit"].empty_label = "Select default unit"

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Accessory name is required.")

        if self.user is not None:
            qs = Accessory.objects.filter(owner=self.user, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This accessory already exists.")

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


# ============================================================
# MATERIAL MASTER
# ============================================================

class MaterialForm(forms.Form):
    MAX_IMAGE_SIZE = 5 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

    material_kind = forms.ChoiceField(
        choices=Material.MATERIAL_KIND_CHOICES,
        label="Material Kind",
        widget=forms.HiddenInput(),
    )

    material_code = forms.CharField(required=False, max_length=30, label="Material Code")
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
    unit = forms.ModelChoiceField(
        queryset=MaterialUnit.objects.none(),
        required=False,
        empty_label="Select Unit",
    )

    name = forms.CharField(max_length=150, label="Material Name")
    composition = forms.CharField(required=False, max_length=160, label="Composition")
    hsn_code = forms.CharField(required=False, max_length=8, label="HSN Code")
    gst_percent = forms.DecimalField(required=False, max_digits=5, decimal_places=2, label="GST %")
    remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    image = forms.ImageField(required=False)
    is_active = forms.BooleanField(required=False, initial=True)

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

        type_qs = MaterialType.objects.filter(owner=user) if user else MaterialType.objects.none()
        if kind:
            type_qs = type_qs.filter(material_kind=kind)
        type_qs = type_qs.order_by("name")

        sub_type_qs = MaterialSubType.objects.filter(owner=user) if user else MaterialSubType.objects.none()
        if kind:
            sub_type_qs = sub_type_qs.filter(material_kind=kind)
        sub_type_qs = sub_type_qs.select_related("material_type").order_by("material_type__name", "name")

        shade_qs = MaterialShade.objects.filter(owner=user) if user else MaterialShade.objects.none()
        if kind:
            shade_qs = shade_qs.filter(Q(material_kind=kind) | Q(material_kind__isnull=True) | Q(material_kind=""))
        shade_qs = shade_qs.order_by("name")

        unit_qs = MaterialUnit.objects.filter(owner=user).order_by("name") if user else MaterialUnit.objects.none()

        self.fields["material_type"].queryset = type_qs
        self.fields["material_sub_type"].queryset = sub_type_qs
        self.fields["material_shade"].queryset = shade_qs
        self.fields["unit"].queryset = unit_qs

        self.fields["material_type"].label_from_instance = lambda o: o.name
        self.fields["material_sub_type"].label_from_instance = lambda o: o.name
        self.fields["material_shade"].label_from_instance = lambda o: o.name
        self.fields["unit"].label_from_instance = lambda o: o.name

        self.fields["material_type"].widget.attrs.update({"data-role": "material-type"})
        self.fields["material_sub_type"].widget.attrs.update({"data-role": "material-sub-type"})
        self.fields["material_shade"].widget.attrs.update({"data-role": "material-shade"})

        self.fields["material_code"].widget.attrs.update({
            "placeholder": "Auto if left blank",
            "maxlength": "30",
        })
        self.fields["name"].widget.attrs.update({
            "placeholder": "Enter material name",
            "maxlength": "150",
        })
        self.fields["composition"].widget.attrs.update({
            "placeholder": "Enter composition",
            "maxlength": "160",
        })
        self.fields["hsn_code"].widget.attrs.update({
            "placeholder": "Enter HSN code",
            "maxlength": "8",
            "inputmode": "numeric",
            "oninput": "this.value=this.value.replace(/\\D/g,'').slice(0,8)",
        })
        self.fields["gst_percent"].widget.attrs.update({
            "placeholder": "Enter GST %",
            "min": "0",
            "max": "100",
            "step": "0.01",
            "inputmode": "decimal",
        })
        self.fields["remarks"].widget.attrs.update({
            "rows": 4,
            "placeholder": "Add remarks if needed",
            "maxlength": "500",
        })
        self.fields["image"].widget.attrs.update({"accept": "image/*"})

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
                "material_code": instance.material_code,
                "material_type": instance.material_type_id,
                "material_sub_type": instance.material_sub_type_id,
                "material_shade": instance.material_shade_id,
                "unit": instance.unit_id,
                "name": instance.name,
                "composition": instance.composition,
                "hsn_code": instance.hsn_code,
                "gst_percent": instance.gst_percent,
                "remarks": instance.remarks,
                "is_active": instance.is_active,
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

    def _scoped_material_qs(self):
        qs = Material.objects.all()
        if self.user is not None:
            return qs.filter(Q(owner=self.user) | Q(owner__isnull=True))
        if getattr(self.instance, "owner_id", None):
            return qs.filter(owner=self.instance.owner)
        return qs.none()

    @staticmethod
    def _clean_text_value(value, *, label, max_length=None, allow_chars_pattern=None):
        value = re.sub(r"\s+", " ", (value or "").strip())
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

    def _next_material_code(self, kind):
        prefix_map = {
            "yarn": "YRN",
            "greige": "GRG",
            "finished": "FNS",
            "trim": "TRM",
        }
        prefix = prefix_map.get(kind or "", "MAT")
        max_num = 0

        for code in self._scoped_material_qs().values_list("material_code", flat=True):
            match = re.fullmatch(rf"{prefix}(\d+)", (code or "").upper())
            if match:
                max_num = max(max_num, int(match.group(1)))

        return f"{prefix}{max_num + 1:04d}"

    def clean_material_kind(self):
        value = (self.cleaned_data.get("material_kind") or "").strip()
        allowed_kinds = {choice[0] for choice in Material.MATERIAL_KIND_CHOICES}
        if value not in allowed_kinds:
            raise ValidationError("Select a valid material kind.")
        return value

    def clean_material_code(self):
        kind = (self.cleaned_data.get("material_kind") or "").strip()
        code = (self.cleaned_data.get("material_code") or "").strip().upper()

        if not code:
            code = self._next_material_code(kind)

        if not re.fullmatch(r"[A-Z0-9\\-_\\/]+", code):
            raise ValidationError("Material code can contain only letters, numbers, -, _ or /.")

        qs = self._scoped_material_qs().filter(material_code__iexact=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("This material code already exists.")

        return code

    def clean_name(self):
        value = self._clean_text_value(
            self.cleaned_data.get("name"),
            label="Material Name",
            max_length=150,
            allow_chars_pattern=r".*[A-Za-z0-9].*",
        )
        if not value:
            raise ValidationError("Material Name is required.")
        if len(value) < 2:
            raise ValidationError("Material Name must be at least 2 characters long.")
        return value

    def clean_composition(self):
        return self._clean_text_value(
            self.cleaned_data.get("composition"),
            label="Composition",
            max_length=160,
        )

    def clean_hsn_code(self):
        value = (self.cleaned_data.get("hsn_code") or "").strip()
        if not value:
            return value
        if not re.fullmatch(r"\d{4,8}", value):
            raise ValidationError("HSN code must be 4 to 8 digits.")
        return value

    def clean_gst_percent(self):
        value = self.cleaned_data.get("gst_percent")
        if value in (None, ""):
            return Decimal("0")
        if value < 0 or value > 100:
            raise ValidationError("GST % must be between 0 and 100.")
        return value

    def clean_remarks(self):
        return self._clean_text_value(self.cleaned_data.get("remarks"), label="Remarks", max_length=500)

    def clean_count_denier(self):
        return self._clean_text_value(
            self.cleaned_data.get("count_denier"),
            label="Count / Denier",
            max_length=40,
            allow_chars_pattern=r"[A-Za-z0-9\s./()_%+-]+",
        )

    def clean_yarn_color(self):
        return self._clean_text_value(
            self.cleaned_data.get("yarn_color"),
            label="Color",
            max_length=60,
            allow_chars_pattern=r"[A-Za-z0-9\s.,()/#&+-]+",
        )

    def clean_fabric_type(self):
        return self._clean_text_value(
            self.cleaned_data.get("fabric_type"),
            label="Fabric Type",
            max_length=120,
        )

    def clean_construction(self):
        return self._clean_text_value(
            self.cleaned_data.get("construction"),
            label="Construction",
            max_length=120,
            allow_chars_pattern=r"[A-Za-z0-9\s.,()/%xX+-]+",
        )

    def clean_base_fabric_type(self):
        return self._clean_text_value(
            self.cleaned_data.get("base_fabric_type"),
            label="Base Fabric Type",
            max_length=120,
        )

    def clean_end_use(self):
        return self._clean_text_value(
            self.cleaned_data.get("end_use"),
            label="End Use",
            max_length=120,
        )

    def clean_trim_size(self):
        return self._clean_text_value(
            self.cleaned_data.get("trim_size"),
            label="Size",
            max_length=60,
            allow_chars_pattern=r"[A-Za-z0-9\s.,()/#xX+-]+",
        )

    def clean_trim_color(self):
        return self._clean_text_value(
            self.cleaned_data.get("trim_color"),
            label="Color",
            max_length=60,
            allow_chars_pattern=r"[A-Za-z0-9\s.,()/#&+-]+",
        )

    def clean_brand(self):
        return self._clean_text_value(
            self.cleaned_data.get("brand"),
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
        kind = (cd.get("material_kind") or "").strip()

        material_type = cd.get("material_type")
        material_sub_type = cd.get("material_sub_type")
        material_shade = cd.get("material_shade")
        unit = cd.get("unit")
        name = cd.get("name")

        if self.user is not None and material_type and material_type.owner_id != self.user.id:
            self.add_error("material_type", "Selected Material Type is not available for this user.")
        if kind and material_type and material_type.material_kind != kind:
            self.add_error("material_type", "Selected Material Type does not belong to selected Kind.")

        if material_sub_type and not material_type:
            self.add_error("material_type", "Select Material Type before choosing Material Sub Type.")
        if self.user is not None and material_sub_type and material_sub_type.owner_id != self.user.id:
            self.add_error("material_sub_type", "Selected Material Sub Type is not available for this user.")
        if kind and material_sub_type and material_sub_type.material_kind != kind:
            self.add_error("material_sub_type", "Selected Material Sub Type does not belong to selected Kind.")
        if material_type and material_sub_type and material_sub_type.material_type_id != material_type.id:
            self.add_error("material_sub_type", "Selected Material Sub Type does not belong to selected Material Type.")

        if self.user is not None and material_shade and material_shade.owner_id != self.user.id:
            self.add_error("material_shade", "Selected Material Shade is not available for this user.")
        if kind and material_shade and (material_shade.material_kind or "").strip() not in ("", kind):
            self.add_error("material_shade", "Selected Material Shade does not belong to selected Kind.")

        if self.user is not None and unit and unit.owner_id != self.user.id:
            self.add_error("unit", "Selected Unit is not available for this user.")

        if kind == "trim" and not material_type:
            self.add_error("material_type", "Please select a Material Type for trim materials.")

        if name:
            dup_qs = self._scoped_material_qs().filter(material_kind=kind, name__iexact=name)
            if self.instance and self.instance.pk:
                dup_qs = dup_qs.exclude(pk=self.instance.pk)
            if dup_qs.exists():
                self.add_error("name", "A material with this name already exists for this kind.")

        return cd

    def save(self) -> Material:
        if not self.is_valid():
            raise ValueError("Call is_valid() before save().")

        cd = self.cleaned_data
        kind = cd["material_kind"]

        material = self.instance or Material()
        if self.user is not None:
            material.owner = self.user

        material.material_code = cd["material_code"]
        material.material_kind = kind
        material.material_type = cd.get("material_type")
        material.material_sub_type = cd.get("material_sub_type")
        material.material_shade = cd.get("material_shade")
        material.unit = cd.get("unit")
        material.name = cd["name"]
        material.composition = cd.get("composition", "")
        material.hsn_code = cd.get("hsn_code", "")
        material.gst_percent = cd.get("gst_percent") or Decimal("0")
        material.remarks = cd.get("remarks", "")
        material.is_active = bool(cd.get("is_active"))

        image = cd.get("image")
        if image:
            material.image = image

        material.save()

        YarnDetail.objects.filter(material=material).delete()
        GreigeDetail.objects.filter(material=material).delete()
        FinishedDetail.objects.filter(material=material).delete()
        TrimDetail.objects.filter(material=material).delete()

        if kind == "yarn":
            selected_material_type = cd.get("material_type")
            selected_material_sub_type = cd.get("material_sub_type")

            YarnDetail.objects.create(
                material=material,
                yarn_type=selected_material_type.name if selected_material_type else "",
                yarn_subtype=selected_material_sub_type.name if selected_material_sub_type else "",
                count_denier=cd.get("count_denier", ""),
                color=cd.get("yarn_color", ""),
            )

        elif kind == "greige":
            GreigeDetail.objects.create(
                material=material,
                fabric_type=cd.get("fabric_type", ""),
                gsm=cd.get("gsm"),
                width=cd.get("width"),
                construction=cd.get("construction", ""),
            )

        elif kind == "finished":
            FinishedDetail.objects.create(
                material=material,
                base_fabric_type=cd.get("base_fabric_type", ""),
                finish_type=cd.get("finish_type", ""),
                gsm=cd.get("finished_gsm"),
                width=cd.get("finished_width"),
                end_use=cd.get("end_use", ""),
            )

        elif kind == "trim":
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
# FIRM ADDRESS
# ============================================================
class FirmAddressForm(forms.ModelForm):
    class Meta:
        model = FirmAddress
        fields = ["label", "address_line", "city", "state", "pincode", "is_default"]
        widgets = {
            "label": forms.TextInput(attrs={"placeholder": "Head Office / Warehouse / Branch", "maxlength": "80"}),
            "address_line": forms.TextInput(attrs={"placeholder": "Address line", "maxlength": "255"}),
            "city": forms.TextInput(attrs={"placeholder": "City", "maxlength": "100"}),
            "state": forms.TextInput(attrs={"placeholder": "State", "maxlength": "100"}),
            "pincode": forms.TextInput(attrs={"placeholder": "395003", "maxlength": "6", "inputmode": "numeric"}),
        }

    def clean_label(self):
        return _compact_spaces(self.cleaned_data.get("label"))

    def clean_address_line(self):
        value = _compact_spaces(self.cleaned_data.get("address_line"))
        if not value:
            raise forms.ValidationError("Address line is required.")
        if len(value) < 5:
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
        value = re.sub(r"\D", "", self.cleaned_data.get("pincode") or "")
        if value and len(value) != 6:
            raise forms.ValidationError("Pincode must be exactly 6 digits.")
        return value


class BaseFirmAddressFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        default_count = 0
        active_rows = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue

            label = form.cleaned_data.get("label")
            address_line = form.cleaned_data.get("address_line")
            city = form.cleaned_data.get("city")
            state = form.cleaned_data.get("state")
            pincode = form.cleaned_data.get("pincode")
            is_default = form.cleaned_data.get("is_default")

            has_any_data = any([label, address_line, city, state, pincode, is_default])
            if not has_any_data:
                continue

            active_rows += 1
            if not address_line:
                form.add_error("address_line", "Address line is required.")
            if is_default:
                default_count += 1

        if default_count > 1:
            raise forms.ValidationError("Only one shipping address can be marked as default.")
        if active_rows and default_count == 0:
            raise forms.ValidationError("Mark one shipping address as default.")


FirmAddressFormSet = inlineformset_factory(
    Firm,
    FirmAddress,
    form=FirmAddressForm,
    formset=BaseFirmAddressFormSet,
    extra=1,
    can_delete=True,
)

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
    shipping_address_choice = forms.ChoiceField(
        required=False,
        choices=[("", "Select shipping address")],
    )

    class Meta:
        model = YarnPurchaseOrder
        fields = [
            "po_number",                # Reference No.
            "internal_po_number",
            "po_date",
            "expected_delivery_date",
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
            "po_number": forms.TextInput(attrs={"placeholder": "Reference number"}),
            "internal_po_number": forms.TextInput(attrs={"placeholder": "Internal PO number"}),
            "po_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date", "readonly": "readonly"},
            ),
            "expected_delivery_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
            "cancel_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "shipping_address": forms.Textarea(attrs={"rows": 2, "placeholder": "Delivery or shipping address"}),
            "remarks": forms.Textarea(attrs={"rows": 2, "placeholder": "Notes / remarks"}),
            "terms_conditions": forms.Textarea(attrs={"rows": 3, "placeholder": "Terms & conditions"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.shipping_address_map = {}

        self.fields["vendor"].queryset = (
            Vendor.objects.filter(owner=user, is_active=True).order_by("name")
            if user else Vendor.objects.none()
        )
        self.fields["firm"].queryset = (
            Firm.objects.filter(owner=user).prefetch_related("addresses").order_by("firm_name")
            if user else Firm.objects.none()
        )
        self.fields["terms_template"].queryset = (
            TermsCondition.objects.filter(owner=user, is_active=True).order_by("title")
            if user else TermsCondition.objects.none()
        )

        self.fields["vendor"].empty_label = "Select vendor"
        self.fields["firm"].empty_label = "Select firm"
        self.fields["firm"].widget = forms.HiddenInput()

        compact_attrs = {
            "po_number": {"placeholder": "Reference number"},
            "internal_po_number": {"placeholder": "Internal PO number"},
            "shipping_address": {"rows": 2, "placeholder": "Delivery or shipping address"},
            "remarks": {"rows": 2, "placeholder": "Notes / remarks"},
            "terms_conditions": {"rows": 3, "placeholder": "Terms & conditions"},
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

        firm = self.instance.firm or self.fields["firm"].queryset.first()
        if firm and not self.instance.pk:
            self.initial.setdefault("firm", firm.pk)
            self.fields["firm"].initial = firm.pk

        if not self.is_bound:
            today = timezone.localdate()
            self.initial["po_date"] = today
            self.fields["po_date"].initial = today
            self.initial.setdefault("expected_delivery_date", self.instance.expected_delivery_date)
            self.fields["expected_delivery_date"].initial = self.initial.get("expected_delivery_date")
            self.fields["discount_percent"].initial = self.initial.get("discount_percent", 0)
            self.fields["others"].initial = self.initial.get("others", 0)
            self.fields["cgst_percent"].initial = self.initial.get("cgst_percent", 2.5)
            self.fields["sgst_percent"].initial = self.initial.get("sgst_percent", 2.5)

        self._setup_shipping_addresses(firm)

    def _setup_shipping_addresses(self, firm):
        choices = [("", "Select shipping address")]
        address_map = {}

        if firm is not None:
            addresses = list(firm.addresses.order_by("-is_default", "id")) if hasattr(firm, "addresses") else []
            for address in addresses:
                key = str(address.pk)
                title = address.label or f"Address {address.pk}"
                full_address = address.full_address
                if address.is_default:
                    title = f"{title} (Default)"
                choices.append((key, title))
                address_map[key] = full_address

            if not address_map and getattr(firm, "full_address", ""):
                choices.append(("firm-default", f"{firm.firm_name} (Default)"))
                address_map["firm-default"] = firm.full_address

        self.shipping_address_map = address_map
        self.fields["shipping_address_choice"].choices = choices

        current_shipping_address = (
            self.initial.get("shipping_address")
            or getattr(self.instance, "shipping_address", "")
            or ""
        ).strip()

        selected_choice = ""
        for key, value in address_map.items():
            if value == current_shipping_address:
                selected_choice = key
                break

        if not selected_choice and len(choices) > 1 and not current_shipping_address:
            selected_choice = choices[1][0]
            current_shipping_address = address_map.get(selected_choice, "")

        self.initial.setdefault("shipping_address_choice", selected_choice)
        if current_shipping_address:
            self.initial.setdefault("shipping_address", current_shipping_address)

    def clean_po_date(self):
        return timezone.localdate()

    def clean_internal_po_number(self):
        return (self.cleaned_data.get("internal_po_number") or "").strip()
    
    def clean_shipping_address(self):
        value = _compact_spaces(self.cleaned_data.get("shipping_address"))
        if not value:
            selected_key = (self.cleaned_data.get("shipping_address_choice") or "").strip()
            value = _compact_spaces(self.shipping_address_map.get(selected_key, ""))
        if not value:
            raise forms.ValidationError("Shipping address is required.")
        return value

    def clean(self):
        cleaned_data = super().clean()

        # ✅ Existing validation (keep this)
        for field_name in ["discount_percent", "others", "cgst_percent", "sgst_percent"]:
            value = cleaned_data.get(field_name)
            if value is not None and value < 0:
                self.add_error(field_name, "Value cannot be negative.")

        # ✅ ADD THIS BLOCK (date validation)
        expected_delivery_date = cleaned_data.get("expected_delivery_date")
        po_date = cleaned_data.get("po_date")

        if expected_delivery_date and po_date and expected_delivery_date < po_date:
            self.add_error(
                "expected_delivery_date",
                "Expected delivery date cannot be before PO date."
            )

        return cleaned_data


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

class ReadyPOReviewForm(forms.Form):
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
            "material", "unit", "quantity", "value", "dia", "gauge", "rolls",
            "count", "gsm", "sl", "hsn_code", "remark", "rate", "final_amount",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        qs = Material.objects.filter(material_kind="yarn").select_related("material_type").order_by("name")
        self.fields["material"].queryset = qs
        self.fields["material"].empty_label = "Select Yarn"
        self.fields["material"].label_from_instance = (
            lambda obj: f"{obj.name}{f' ({obj.material_type.name})' if obj.material_type else ''}"
        )

        current_unit = (self.initial.get("unit") or getattr(self.instance, "unit", "") or "").strip()
        if self.is_bound:
            bound_unit = (self.data.get(self.add_prefix("unit")) or "").strip()
            if bound_unit:
                current_unit = bound_unit

        unit_choices = _material_unit_choices(user, current_unit)

        self.fields["unit"].required = False
        self.fields["unit"].choices = unit_choices
        self.fields["unit"].widget = forms.Select(choices=unit_choices)
        self.fields["final_amount"].widget.attrs.update({"readonly": "readonly"})

    def clean_unit(self):
        value = (self.cleaned_data.get("unit") or "").strip()
        valid_units = {choice for choice, _label in self.fields["unit"].choices if choice}
        if value and value not in valid_units:
            raise forms.ValidationError("Select a valid unit.")
        return value

    def clean(self):
        cleaned_data = super().clean()
        material = cleaned_data.get("material")
        quantity = cleaned_data.get("quantity")
        rate = cleaned_data.get("rate")
        value = cleaned_data.get("value")

        has_other_data = any([
            cleaned_data.get("unit"), value, quantity, rate,
            cleaned_data.get("dia"), cleaned_data.get("gauge"), cleaned_data.get("rolls"),
            cleaned_data.get("count"), cleaned_data.get("gsm"), cleaned_data.get("sl"),
            cleaned_data.get("hsn_code"), cleaned_data.get("remark"),
        ])

        if not material and not has_other_data:
            cleaned_data["final_amount"] = Decimal("0")
            return cleaned_data

        if not material:
            self.add_error("material", "Select a yarn item.")
            return cleaned_data

        if quantity in (None, ""):
            self.add_error("quantity", "Quantity is required.")
        elif quantity <= 0:
            self.add_error("quantity", "Quantity must be greater than 0.")

        if rate in (None, ""):
            rate = Decimal("0")
            cleaned_data["rate"] = rate
        elif rate < 0:
            self.add_error("rate", "Rate cannot be negative.")

        if value not in (None, "") and value < 0:
            self.add_error("value", "Value cannot be negative.")

        if material is not None and material.material_kind != "yarn":
            self.add_error("material", "Only yarn materials are allowed.")

        quantity = cleaned_data.get("quantity") or Decimal("0")
        rate = cleaned_data.get("rate") or Decimal("0")
        cleaned_data["final_amount"] = (quantity * rate).quantize(Decimal("0.01"))
        cleaned_data["material_type"] = material.material_type if material else None
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.material_type = instance.material.material_type if instance.material else None
        instance.final_amount = (instance.quantity or Decimal("0")) * (instance.rate or Decimal("0"))
        if commit:
            instance.save()
        return instance


class BaseYarnPurchaseOrderItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen_material_ids = set()
        has_active_line = False

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            should_delete = form.cleaned_data.get("DELETE")
            instance = form.instance

            if should_delete:
                if instance.pk and (
                    instance.inward_items.exists()
                    or instance.generated_greige_items.exists()
                ):
                    raise forms.ValidationError(
                        "You cannot delete a yarn line that is already used in inward or greige generation."
                    )
                continue

            material = form.cleaned_data.get("material")
            quantity = form.cleaned_data.get("quantity")
            rate = form.cleaned_data.get("rate")

            has_other_data = any([
                form.cleaned_data.get("unit"), form.cleaned_data.get("value"), quantity, rate,
                form.cleaned_data.get("dia"), form.cleaned_data.get("gauge"), form.cleaned_data.get("rolls"),
                form.cleaned_data.get("count"), form.cleaned_data.get("gsm"), form.cleaned_data.get("sl"),
                form.cleaned_data.get("hsn_code"), form.cleaned_data.get("remark"),
            ])

            if not material and not has_other_data:
                continue

            has_active_line = True

            if material:
                if material.pk in seen_material_ids:
                    form.add_error("material", "This yarn item is already added in the PO.")
                seen_material_ids.add(material.pk)

        if not has_active_line:
            raise forms.ValidationError("Add at least one yarn item row.")


YarnPurchaseOrderItemFormSet = inlineformset_factory(
    YarnPurchaseOrder,
    YarnPurchaseOrderItem,
    form=YarnPurchaseOrderItemForm,
    formset=BaseYarnPurchaseOrderItemFormSet,
    fields=[
        "material", "unit", "quantity", "value", "dia", "gauge", "rolls",
        "count", "gsm", "sl", "hsn_code", "remark", "rate", "final_amount",
    ],
    extra=1,
    can_delete=True,
)

# ============================================================
# GREIGE PURCHASE ORDER
# ============================================================
class GreigePurchaseOrderItemForm(forms.ModelForm):
    unit = forms.ChoiceField(
        required=False,
        choices=[("", "Select unit")],
    )

    class Meta:
        model = GreigePurchaseOrderItem
        fields = [
            "material", "unit", "quantity", "value", "dia", "gauge", "rolls",
            "count", "gsm", "sl", "hsn_code", "remark", "rate", "final_amount",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        qs = (
            Material.objects
            .filter(Q(owner=user) | Q(owner__isnull=True), material_kind="greige", is_active=True)
            .order_by("name")
            if user else Material.objects.none()
        )
        self.fields["material"].queryset = qs
        self.fields["material"].empty_label = "Select Greige Type"
        self.fields["material"].label_from_instance = lambda obj: obj.name

        current_unit = (self.initial.get("unit") or getattr(self.instance, "unit", "") or "").strip()
        if self.is_bound:
            bound_unit = (self.data.get(self.add_prefix("unit")) or "").strip()
            if bound_unit:
                current_unit = bound_unit

        unit_choices = _material_unit_choices(user, current_unit)

        self.fields["unit"].required = False
        self.fields["unit"].choices = unit_choices
        self.fields["unit"].widget = forms.Select(choices=unit_choices)
        self.fields["final_amount"].widget.attrs.update({"readonly": "readonly"})

    def clean_unit(self):
        value = (self.cleaned_data.get("unit") or "").strip()
        valid_units = {choice for choice, _label in self.fields["unit"].choices if choice}
        if value and value not in valid_units:
            raise forms.ValidationError("Select a valid unit.")
        return value

    def clean(self):
        cleaned_data = super().clean()
        material = cleaned_data.get("material")
        quantity = cleaned_data.get("quantity")
        rate = cleaned_data.get("rate")
        value = cleaned_data.get("value")

        has_other_data = any([
            cleaned_data.get("unit"), value, quantity, rate,
            cleaned_data.get("dia"), cleaned_data.get("gauge"), cleaned_data.get("rolls"),
            cleaned_data.get("count"), cleaned_data.get("gsm"), cleaned_data.get("sl"),
            cleaned_data.get("hsn_code"), cleaned_data.get("remark"),
        ])

        if not material and not has_other_data:
            cleaned_data["final_amount"] = Decimal("0")
            return cleaned_data

        if not material:
            self.add_error("material", "Select a greige item.")
            return cleaned_data

        if quantity in (None, ""):
            self.add_error("quantity", "Quantity is required.")
        elif quantity <= 0:
            self.add_error("quantity", "Quantity must be greater than 0.")

        if rate in (None, ""):
            rate = Decimal("0")
            cleaned_data["rate"] = rate
        elif rate < 0:
            self.add_error("rate", "Rate cannot be negative.")

        if value not in (None, "") and value < 0:
            self.add_error("value", "Value cannot be negative.")

        if material is not None and material.material_kind != "greige":
            self.add_error("material", "Only greige materials are allowed.")

        quantity = cleaned_data.get("quantity") or Decimal("0")
        rate = cleaned_data.get("rate") or Decimal("0")
        cleaned_data["final_amount"] = (quantity * rate).quantize(Decimal("0.01"))
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.final_amount = (instance.quantity or Decimal("0")) * (instance.rate or Decimal("0"))
        if commit:
            instance.save()
        return instance


class BaseGreigePurchaseOrderItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen_material_ids = set()
        has_active_line = False

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            should_delete = form.cleaned_data.get("DELETE")
            if should_delete:
                continue

            material = form.cleaned_data.get("material")
            quantity = form.cleaned_data.get("quantity")
            rate = form.cleaned_data.get("rate")

            has_other_data = any([
                form.cleaned_data.get("unit"), form.cleaned_data.get("value"), quantity, rate,
                form.cleaned_data.get("dia"), form.cleaned_data.get("gauge"), form.cleaned_data.get("rolls"),
                form.cleaned_data.get("count"), form.cleaned_data.get("gsm"), form.cleaned_data.get("sl"),
                form.cleaned_data.get("hsn_code"), form.cleaned_data.get("remark"),
            ])

            if not material and not has_other_data:
                continue

            has_active_line = True

            if material:
                if material.pk in seen_material_ids:
                    form.add_error("material", "This greige item is already added in the PO.")
                seen_material_ids.add(material.pk)

        if not has_active_line:
            raise forms.ValidationError("Add at least one greige item row.")


GreigePurchaseOrderItemFormSet = inlineformset_factory(
    GreigePurchaseOrder,
    GreigePurchaseOrderItem,
    form=GreigePurchaseOrderItemForm,
    formset=BaseGreigePurchaseOrderItemFormSet,
    fields=[
        "material", "unit", "quantity", "value", "dia", "gauge", "rolls",
        "count", "gsm", "sl", "hsn_code", "remark", "rate", "final_amount",
    ],
    extra=1,
    can_delete=True,
)


class GreigePurchaseOrderForm(forms.ModelForm):
    terms_template = forms.ModelChoiceField(
        queryset=TermsCondition.objects.none(),
        required=False,
        empty_label="Select saved terms",
        label="Saved Terms & Conditions",
    )
    shipping_address_choice = forms.ChoiceField(
        required=False,
        choices=[("", "Select shipping address")],
    )

    class Meta:
        model = GreigePurchaseOrder
        fields = [
            "po_number",
            "internal_po_number",
            "source_yarn_po",
            "firm",
            "po_date",
            "available_qty",
            "vendor",
            "shipping_address",
            "expected_delivery_date",
            "cancel_date",
            "remarks",
            "terms_conditions",
            "delivery_period",
            "validity_period",
            "delivery_schedule",
        ]
        widgets = {
            "po_number": forms.TextInput(attrs={"placeholder": "Reference number"}),
            "internal_po_number": forms.TextInput(attrs={"placeholder": "Internal PO number"}),
            "po_date": forms.DateInput(attrs={"type": "date", "readonly": "readonly"}),
            "expected_delivery_date": forms.DateInput(attrs={"type": "date"}),
            "cancel_date": forms.DateInput(attrs={"type": "date"}),
            "shipping_address": forms.Textarea(attrs={"rows": 2, "placeholder": "Delivery or shipping address"}),
            "remarks": forms.Textarea(attrs={"rows": 2, "placeholder": "Notes / remarks"}),
            "terms_conditions": forms.Textarea(attrs={"rows": 3, "placeholder": "Terms & conditions"}),
            "available_qty": forms.NumberInput(attrs={"readonly": "readonly", "step": "0.01"}),
        }

    def __init__(self, *args, user=None, source_yarn_po=None, lock_source=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.shipping_address_map = {}

        self.fields["vendor"].queryset = (
            Vendor.objects.filter(owner=user, is_active=True).order_by("name")
            if user else Vendor.objects.none()
        )
        self.fields["firm"].queryset = (
            Firm.objects.filter(owner=user).prefetch_related("addresses").order_by("firm_name")
            if user else Firm.objects.none()
        )
        self.fields["terms_template"].queryset = (
            TermsCondition.objects.filter(owner=user, is_active=True).order_by("title")
            if user else TermsCondition.objects.none()
        )

        source_ids_qs = YarnPurchaseOrder.objects.filter(items__inward_items__isnull=False)
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

        self.fields["source_yarn_po"].required = source_yarn_po is None
        self.fields["vendor"].required = True
        self.fields["firm"].required = False
        self.fields["po_number"].required = False
        self.fields["internal_po_number"].required = False
        self.fields["po_date"].required = True
        self.fields["available_qty"].required = False
        self.fields["shipping_address"].required = False
        self.fields["expected_delivery_date"].required = False
        self.fields["cancel_date"].required = False
        self.fields["remarks"].required = False
        self.fields["terms_conditions"].required = False
        self.fields["delivery_period"].required = False
        self.fields["validity_period"].required = False
        self.fields["delivery_schedule"].required = False

        self.fields["terms_template"].widget.attrs.update({
            "data-terms-template-select": "1",
        })

        if self.instance.pk and self.instance.terms_conditions:
            matched = self.fields["terms_template"].queryset.filter(
                content=self.instance.terms_conditions
            ).first()
            if matched:
                self.initial["terms_template"] = matched.pk

        if lock_source:
            self.fields["source_yarn_po"].disabled = True

        if not self.is_bound:
            today = self.instance.po_date or timezone.localdate()
            self.fields["po_date"].initial = today

            if self.instance.pk and not self.initial.get("available_qty"):
                self.fields["available_qty"].initial = self.instance.remaining_qty_total

            if source_yarn_po is not None:
                if getattr(source_yarn_po, "vendor_id", None):
                    self.fields["vendor"].initial = source_yarn_po.vendor_id
                    self.initial.setdefault("vendor", source_yarn_po.vendor_id)

                if getattr(source_yarn_po, "firm_id", None):
                    self.fields["firm"].initial = source_yarn_po.firm_id
                    self.initial.setdefault("firm", source_yarn_po.firm_id)

                source_shipping = getattr(source_yarn_po, "shipping_address", "") or ""
                if not source_shipping and getattr(source_yarn_po, "firm", None):
                    source_shipping = self._firm_address_text(source_yarn_po.firm)

                if source_shipping:
                    self.fields["shipping_address"].initial = source_shipping
                    self.initial.setdefault("shipping_address", source_shipping)

        firm = self.instance.firm

        if self.is_bound:
            firm_id = (
                self.data.get(self.add_prefix("firm"))
                or self.data.get("firm")
                or ""
            ).strip()

            if firm_id:
                try:
                    firm = self.fields["firm"].queryset.get(pk=firm_id)
                except:
                    firm = None
        else:
            initial_firm_id = self.initial.get("firm") or self.fields["firm"].initial
            if initial_firm_id:
                firm = firm or self.fields["firm"].queryset.filter(pk=initial_firm_id).first()

        self._setup_shipping_addresses(firm)

    def _firm_address_text(self, firm):
        if not firm:
            return ""

        default_address = None
        if hasattr(firm, "addresses"):
            default_address = firm.addresses.order_by("-is_default", "id").first()

        if default_address:
            return default_address.full_address

        return getattr(firm, "full_address", "") or ""

    def _setup_shipping_addresses(self, firm):
        choices = [("", "Select shipping address")]
        address_map = {}

        if firm is not None:
            addresses = list(firm.addresses.order_by("-is_default", "id")) if hasattr(firm, "addresses") else []

            for address in addresses:
                key = str(address.pk)
                title = address.label or f"Address {address.pk}"
                full_address = address.full_address

                if address.is_default:
                    title = f"{title} (Default)"

                choices.append((key, title))
                address_map[key] = full_address

            if not address_map and getattr(firm, "full_address", ""):
                choices.append(("firm-default", f"{firm.firm_name} (Default)"))
                address_map["firm-default"] = firm.full_address

        self.shipping_address_map = address_map
        self.fields["shipping_address_choice"].choices = choices

        current_shipping_address = (
            self.data.get(self.add_prefix("shipping_address"))
            if self.is_bound
            else (
                self.initial.get("shipping_address")
                or getattr(self.instance, "shipping_address", "")
                or ""
            )
        )
        current_shipping_address = (current_shipping_address or "").strip()

        selected_choice = (
            self.data.get(self.add_prefix("shipping_address_choice"))
            if self.is_bound
            else self.initial.get("shipping_address_choice", "")
        )
        selected_choice = (selected_choice or "").strip()

        if selected_choice and selected_choice in address_map:
            current_shipping_address = address_map[selected_choice]

        if not selected_choice:
            for key, value in address_map.items():
                if value == current_shipping_address:
                    selected_choice = key
                    break

        if not selected_choice and len(choices) > 1 and not current_shipping_address:
            selected_choice = choices[1][0]
            current_shipping_address = address_map.get(selected_choice, "")

        self.initial["shipping_address_choice"] = selected_choice
        if current_shipping_address:
            self.initial["shipping_address"] = current_shipping_address

    def clean_po_number(self):
        return (self.cleaned_data.get("po_number") or "").strip()

    def clean_internal_po_number(self):
        return (self.cleaned_data.get("internal_po_number") or "").strip()

    def clean_shipping_address(self):
        value = _compact_spaces(self.cleaned_data.get("shipping_address"))

        if not value:
            selected_key = (self.cleaned_data.get("shipping_address_choice") or "").strip()
            value = _compact_spaces(self.shipping_address_map.get(selected_key, ""))

        return value

    def clean_available_qty(self):
        value = self.cleaned_data.get("available_qty")

        if value in (None, ""):
            return Decimal("0")

        if value < 0:
            raise forms.ValidationError("Available quantity cannot be negative.")

        return value

    def clean(self):
        cleaned_data = super().clean()

        po_date = cleaned_data.get("po_date")
        expected_delivery_date = cleaned_data.get("expected_delivery_date")
        cancel_date = cleaned_data.get("cancel_date")

        if expected_delivery_date and po_date and expected_delivery_date < po_date:
            self.add_error("expected_delivery_date", "Expected delivery date cannot be before PO date.")

        if cancel_date and po_date and cancel_date < po_date:
            self.add_error("cancel_date", "Cancel date cannot be before PO date.")

        return cleaned_data


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


class GreigePOInwardForm(forms.ModelForm):
    class Meta:
        model = GreigePOInward
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
            if user else Vendor.objects.none()
        )
        self.fields["vendor"].empty_label = "Select vendor"

        self.fields["inward_type"].required = True
        self.fields["inward_type"].queryset = (
            InwardType.objects.filter(owner=user).order_by("name")
            if user else InwardType.objects.none()
        )
        self.fields["inward_type"].empty_label = "Select inward type"

# ============================================================
# DYEING PURCHASE ORDER
# ============================================================

class DyeingPurchaseOrderForm(forms.ModelForm):
    terms_template = forms.ModelChoiceField(
        queryset=TermsCondition.objects.none(),
        required=False,
        empty_label="Select saved terms",
        label="Saved Terms & Conditions",
    )
    shipping_address_choice = forms.ChoiceField(
        required=False,
        choices=[("", "Select shipping address")],
    )

    class Meta:
        model = DyeingPurchaseOrder
        fields = [
            "source_greige_po",
            "vendor",
            "firm",
            "po_number",                # Reference No.
            "internal_po_number",
            "po_date",
            "expected_delivery_date",
            "cancel_date",
            "shipping_address",
            "remarks",
            "terms_conditions",
            "discount_percent",
            "others",
            "gst_percent",
            "tcs_percent",
        ]
        widgets = {
            "po_number": forms.TextInput(attrs={"placeholder": "Reference number"}),
            "internal_po_number": forms.TextInput(attrs={"placeholder": "Internal PO number"}),
            "po_date": forms.DateInput(attrs={"type": "date", "readonly": "readonly"}),
            "expected_delivery_date": forms.DateInput(attrs={"type": "date"}),
            "cancel_date": forms.DateInput(attrs={"type": "date"}),
            "shipping_address": forms.Textarea(attrs={"rows": 2, "placeholder": "Delivery or shipping address"}),
            "remarks": forms.Textarea(attrs={"rows": 2, "placeholder": "Notes / remarks"}),
            "terms_conditions": forms.Textarea(attrs={"rows": 3, "placeholder": "Terms & conditions"}),
        }

    def __init__(self, *args, user=None, source_greige_po=None, lock_source=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.shipping_address_map = {}

        self.fields["vendor"].queryset = (
            Vendor.objects.filter(owner=user, is_active=True).order_by("name")
            if user else Vendor.objects.none()
        )
        self.fields["firm"].queryset = (
            Firm.objects.filter(owner=user).prefetch_related("addresses").order_by("firm_name")
            if user else Firm.objects.none()
        )
        self.fields["terms_template"].queryset = (
            TermsCondition.objects.filter(owner=user, is_active=True).order_by("title")
            if user else TermsCondition.objects.none()
        )

        source_ids_qs = GreigePurchaseOrder.objects.filter(items__inward_items__isnull=False)
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

        self.fields["source_greige_po"].required = source_greige_po is None
        self.fields["vendor"].required = True
        self.fields["firm"].required = False
        self.fields["po_number"].required = False
        self.fields["internal_po_number"].required = False
        self.fields["po_date"].required = True
        self.fields["expected_delivery_date"].required = False
        self.fields["cancel_date"].required = False
        self.fields["shipping_address"].required = False
        self.fields["remarks"].required = False
        self.fields["terms_conditions"].required = False
        self.fields["discount_percent"].required = False
        self.fields["others"].required = False
        self.fields["gst_percent"].required = False
        self.fields["tcs_percent"].required = False

        self.fields["terms_template"].widget.attrs.update({
            "data-terms-template-select": "1",
        })

        if self.instance.pk and self.instance.terms_conditions:
            matched = self.fields["terms_template"].queryset.filter(content=self.instance.terms_conditions).first()
            if matched:
                self.initial["terms_template"] = matched.pk

        if lock_source:
            self.fields["source_greige_po"].disabled = True

        if not self.is_bound:
            self.fields["po_date"].initial = self.instance.po_date or timezone.localdate()

            if source_greige_po is not None:
                self.fields["vendor"].initial = source_greige_po.vendor_id
                if getattr(source_greige_po, "source_yarn_po", None) and getattr(source_greige_po.source_yarn_po, "firm_id", None):
                    self.fields["firm"].initial = source_greige_po.source_yarn_po.firm_id
                self.fields["shipping_address"].initial = source_greige_po.shipping_address or ""

        firm = self.instance.firm or self.fields["firm"].queryset.filter(pk=self.initial.get("firm")).first()
        self._setup_shipping_addresses(firm)

    def _setup_shipping_addresses(self, firm):
        choices = [("", "Select shipping address")]
        address_map = {}

        selected_choice = ""
        current_shipping_address = ""

        if self.is_bound:
            selected_choice = (
                self.data.get(self.add_prefix("shipping_address_choice"))
                or self.data.get("shipping_address_choice")
                or ""
            ).strip()

            current_shipping_address = (
                self.data.get(self.add_prefix("shipping_address"))
                or self.data.get("shipping_address")
                or ""
            ).strip()
        else:
            selected_choice = (self.initial.get("shipping_address_choice") or "").strip()
            current_shipping_address = (
                self.initial.get("shipping_address")
                or getattr(self.instance, "shipping_address", "")
                or ""
            ).strip()

        if firm is not None:
            addresses = list(firm.addresses.order_by("-is_default", "id")) if hasattr(firm, "addresses") else []

            for address in addresses:
                key = str(address.pk)
                title = address.label or f"Address {address.pk}"
                full_address = address.full_address

                if address.is_default:
                    title = f"{title} (Default)"

                choices.append((key, title))
                address_map[key] = full_address

            if not address_map and getattr(firm, "full_address", ""):
                choices.append(("firm-default", f"{firm.firm_name} (Default)"))
                address_map["firm-default"] = firm.full_address

        # IMPORTANT: if POST submitted a choice but firm choices did not rebuild,
        # still allow it when shipping address text exists.
        if self.is_bound and selected_choice and selected_choice not in address_map and current_shipping_address:
            choices.append((selected_choice, "Selected shipping address"))
            address_map[selected_choice] = current_shipping_address

        if selected_choice and selected_choice in address_map:
            current_shipping_address = address_map[selected_choice]

        if not selected_choice:
            for key, value in address_map.items():
                if value == current_shipping_address:
                    selected_choice = key
                    break

        if not selected_choice and len(choices) > 1 and not current_shipping_address:
            selected_choice = choices[1][0]
            current_shipping_address = address_map.get(selected_choice, "")

        self.shipping_address_map = address_map
        self.fields["shipping_address_choice"].choices = choices

        self.initial["shipping_address_choice"] = selected_choice
        if current_shipping_address:
            self.initial["shipping_address"] = current_shipping_address

    def clean_po_number(self):
        return (self.cleaned_data.get("po_number") or "").strip()

    def clean_internal_po_number(self):
        return (self.cleaned_data.get("internal_po_number") or "").strip()

    def clean_shipping_address(self):
        value = _compact_spaces(self.cleaned_data.get("shipping_address"))
        if not value:
            selected_key = (self.cleaned_data.get("shipping_address_choice") or "").strip()
            value = _compact_spaces(self.shipping_address_map.get(selected_key, ""))
        return value

    def clean(self):
        cleaned_data = super().clean()

        po_date = cleaned_data.get("po_date")
        source_greige_po = cleaned_data.get("source_greige_po")
        vendor = cleaned_data.get("vendor")
        expected_delivery_date = cleaned_data.get("expected_delivery_date")

        if source_greige_po and vendor and source_greige_po.vendor_id != vendor.id:
            self.add_error("vendor", "Vendor must match the selected Greige PO vendor.")

        if expected_delivery_date and po_date and expected_delivery_date < po_date:
            self.add_error("expected_delivery_date", "Expected delivery date cannot be before PO date.")

        for field_name in ["discount_percent", "others", "gst_percent", "tcs_percent"]:
            value = cleaned_data.get(field_name)
            if value is not None and value < 0:
                self.add_error(field_name, "Value cannot be negative.")

        if not po_date:
            cleaned_data["po_date"] = timezone.localdate()

        return cleaned_data

class DyeingPOReviewForm(forms.Form):
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

class ReadyPOReviewForm(forms.Form):
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

class DyeingPOInwardForm(forms.ModelForm):
    class Meta:
        model = DyeingPOInward
        fields = ["vendor", "inward_date", "notes"]
        widgets = {
            "inward_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional inward notes"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["vendor"].required = True
        self.fields["vendor"].queryset = (
            Vendor.objects.filter(owner=user, is_active=True).order_by("name")
            if user else Vendor.objects.none()
        )
        self.fields["vendor"].empty_label = "Select vendor"

class DyeingPurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = DyeingPurchaseOrderItem
        fields = [
            "source_greige_po_item",
            "greige_name",
            "dyeing_master_detail",
            "finished_material",
            "fabric_name",
            "dyeing_type",
            "dyeing_name",
            "unit",
            "total_qty",
            "source_input_qty",
            "expected_loss_percent",
            "expected_output_qty",
            "rate",
            "line_final_amount",
            "remark",
        ]
        widgets = {
            "source_greige_po_item": forms.Select(attrs={"class": "form-select"}),
            "greige_name": forms.TextInput(attrs={"class": "form-control"}),
            "dyeing_master_detail": forms.Select(attrs={"class": "form-select"}),
            "finished_material": forms.Select(attrs={"class": "form-select"}),
            "fabric_name": forms.TextInput(attrs={"class": "form-control"}),
            "dyeing_type": forms.TextInput(attrs={"class": "form-control"}),
            "dyeing_name": forms.TextInput(attrs={"class": "form-control"}),
            "unit": forms.TextInput(attrs={"class": "form-control"}),
            "total_qty": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "source_input_qty": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "expected_loss_percent": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "expected_output_qty": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "rate": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "line_final_amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "remark": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, user=None, source_greige_po=None, selected_source_inward=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.source_greige_po = source_greige_po
        self.selected_source_inward = selected_source_inward
        self.po_instance = getattr(self.instance, "po", None)

        for field_name in self.fields:
            self.fields[field_name].required = False

        # -----------------------------
        # Source greige item queryset
        # -----------------------------
        source_item_qs = GreigePurchaseOrderItem.objects.none()

        if selected_source_inward is not None:
            source_item_qs = GreigePurchaseOrderItem.objects.filter(
                pk__in=selected_source_inward.items.values_list("po_item_id", flat=True)
            ).select_related("material").order_by("id")
        elif source_greige_po is not None:
            source_item_qs = source_greige_po.items.select_related("material").order_by("id")
        elif self.instance.pk and self.instance.source_greige_po_item_id:
            source_item_qs = GreigePurchaseOrderItem.objects.filter(
                pk=self.instance.source_greige_po_item_id
            ).select_related("material")

        self.fields["source_greige_po_item"].queryset = source_item_qs
        self.fields["source_greige_po_item"].label_from_instance = (
            lambda obj: obj.fabric_name or (obj.material.name if obj.material_id else f"Item {obj.pk}")
        )

        vendor_id = None
        greige_material_id = None

        # -----------------------------
        # Detect vendor
        # -----------------------------
        if self.instance.pk and self.instance.po_id and self.instance.po.vendor_id:
            vendor_id = self.instance.po.vendor_id
        elif self.po_instance and self.po_instance.vendor_id:
            vendor_id = self.po_instance.vendor_id

        if self.is_bound:
            bound_vendor = (self.data.get("vendor") or self.data.get("po-vendor") or "").strip()
            if bound_vendor.isdigit():
                vendor_id = int(bound_vendor)

        # -----------------------------
        # Detect current selected source item
        # -----------------------------
        current_source_item = None

        if self.instance.pk and self.instance.source_greige_po_item_id:
            current_source_item = self.instance.source_greige_po_item

        if self.is_bound:
            bound_source_item = (self.data.get(self.add_prefix("source_greige_po_item")) or "").strip()
            if bound_source_item.isdigit():
                try:
                    current_source_item = source_item_qs.get(pk=int(bound_source_item))
                except GreigePurchaseOrderItem.DoesNotExist:
                    current_source_item = None
        elif self.initial.get("source_greige_po_item"):
            try:
                current_source_item = source_item_qs.get(pk=int(self.initial.get("source_greige_po_item")))
            except (TypeError, ValueError, GreigePurchaseOrderItem.DoesNotExist):
                current_source_item = None

        # -----------------------------
        # Detect greige material
        # Priority:
        # 1. selected inward item
        # 2. current row source item
        # -----------------------------
        if self.selected_source_inward and self.selected_source_inward.items.exists():
            inward_item = self.selected_source_inward.items.select_related("po_item__material").first()
            if inward_item and inward_item.po_item and inward_item.po_item.material_id:
                greige_material_id = inward_item.po_item.material_id
        elif current_source_item and current_source_item.material_id:
            greige_material_id = current_source_item.material_id

        # -----------------------------
        # Dyeing master queryset
        # -----------------------------
        master_qs = (
            DyeingMaterialLinkDetail.objects
            .select_related("link__vendor", "link__material", "finished_material__unit")
            .filter(link__is_active=True)
            .order_by("dyeing_name", "pk")
        )

        if vendor_id:
            master_qs = master_qs.filter(link__vendor_id=vendor_id)



        current_master_id = None
        if self.instance.pk and self.instance.dyeing_master_detail_id:
            current_master_id = self.instance.dyeing_master_detail_id

        if self.is_bound:
            bound_master = (self.data.get(self.add_prefix("dyeing_master_detail")) or "").strip()
            if bound_master.isdigit():
                current_master_id = int(bound_master)

        current_finished_material_id = None
        if self.instance.pk and self.instance.finished_material_id:
            current_finished_material_id = self.instance.finished_material_id

        if self.is_bound:
            bound_finished = (self.data.get(self.add_prefix("finished_material")) or "").strip()
            if bound_finished.isdigit():
                current_finished_material_id = int(bound_finished)
        elif self.initial.get("finished_material"):
            try:
                current_finished_material_id = int(self.initial.get("finished_material"))
            except (TypeError, ValueError):
                current_finished_material_id = None

        if current_finished_material_id:
            master_qs = master_qs.filter(finished_material_id=current_finished_material_id)

        if current_master_id:
            master_ids = list(master_qs.values_list("pk", flat=True))
            if current_master_id not in master_ids:
                master_ids.append(current_master_id)

            master_qs = (
                DyeingMaterialLinkDetail.objects
                .select_related("link__vendor", "link__material", "finished_material__unit")
                .filter(pk__in=master_ids)
                .order_by("dyeing_name", "pk")
            )

        self.fields["dyeing_master_detail"].queryset = master_qs
        self.fields["dyeing_master_detail"].label_from_instance = (
            lambda obj: f"{obj.dyeing_name} | {obj.get_dyeing_type_display()} | {obj.finished_material.name if obj.finished_material_id else '-'}"
        )

        # -----------------------------
        # Finished material queryset
        # -----------------------------
        allowed_finished_material_ids = list(
            master_qs.exclude(finished_material_id__isnull=True)
            .values_list("finished_material_id", flat=True)
            .distinct()
        )

        if user:
            finished_qs = (
                Material.objects
                .filter(
                    Q(owner=user) | Q(owner__isnull=True),
                    material_kind="finished",
                    is_active=True,
                    pk__in=allowed_finished_material_ids,
                )
                .distinct()
            )
        else:
            finished_qs = Material.objects.none()

        if current_finished_material_id:
            finished_ids = list(finished_qs.values_list("pk", flat=True))
            if current_finished_material_id not in finished_ids:
                finished_ids.append(current_finished_material_id)

            finished_qs = Material.objects.filter(pk__in=finished_ids)

        self.fields["finished_material"].queryset = finished_qs.order_by("name")

        # -----------------------------
        # Readonly fields
        # -----------------------------
        self.fields["fabric_name"].widget.attrs["readonly"] = True
        self.fields["dyeing_type"].widget.attrs["readonly"] = True
        self.fields["dyeing_name"].widget.attrs["readonly"] = True
        self.fields["unit"].widget.attrs["readonly"] = True
        self.fields["source_input_qty"].widget.attrs["readonly"] = True
        self.fields["expected_output_qty"].widget.attrs["readonly"] = True
        self.fields["line_final_amount"].widget.attrs["readonly"] = True

        if self.instance.pk and self.instance.dyeing_master_detail_id:
            detail = self.instance.dyeing_master_detail
            if detail:
                self.fields["dyeing_master_detail"].initial = detail.pk

    def clean(self):
        cleaned_data = super().clean()

        source_item = cleaned_data.get("source_greige_po_item")
        master_detail = cleaned_data.get("dyeing_master_detail")
        finished_material = cleaned_data.get("finished_material")

        total_qty = cleaned_data.get("total_qty") or Decimal("0")
        rate = cleaned_data.get("rate") or Decimal("0")
        loss_percent = cleaned_data.get("expected_loss_percent") or Decimal("0")

        greige_material_id = source_item.material_id if source_item and source_item.material_id else None
        vendor_id = None

        if self.po_instance and self.po_instance.vendor_id:
            vendor_id = self.po_instance.vendor_id
        elif self.instance.pk and self.instance.po_id and self.instance.po.vendor_id:
            vendor_id = self.instance.po.vendor_id

        if self.is_bound:
            bound_vendor = (self.data.get("vendor") or self.data.get("po-vendor") or "").strip()
            if bound_vendor.isdigit():
                vendor_id = int(bound_vendor)

        if finished_material and finished_material.material_kind != "finished":
            self.add_error("finished_material", "Only finished material is allowed.")

        allowed_master_qs = DyeingMaterialLinkDetail.objects.filter(link__is_active=True)

        if vendor_id:
            allowed_master_qs = allowed_master_qs.filter(link__vendor_id=vendor_id)



        if finished_material:
            allowed_master_qs = allowed_master_qs.filter(finished_material_id=finished_material.pk)

        allowed_master_ids = set(allowed_master_qs.values_list("pk", flat=True))
        allowed_finished_ids = set(
            DyeingMaterialLinkDetail.objects.filter(
                pk__in=allowed_master_ids
            ).exclude(
                finished_material_id__isnull=True
            ).values_list("finished_material_id", flat=True)
        )

        if finished_material and allowed_finished_ids and finished_material.pk not in allowed_finished_ids:
            self.add_error(
                "finished_material",
                "Selected finished material is not linked with this vendor."
            )

        if master_detail and master_detail.pk not in allowed_master_ids:
            self.add_error(
                "dyeing_master_detail",
               "Selected dyeing master is not linked with the selected vendor/finished material."
            )

        if master_detail and finished_material and master_detail.finished_material_id:
            if master_detail.finished_material_id != finished_material.pk:
                self.add_error(
                    "dyeing_master_detail",
                    "Selected dyeing master is not linked with the selected finished material."
                )
                self.add_error(
                    "finished_material",
                    "Selected finished material does not match the chosen dyeing master."
                )

        if master_detail and not finished_material and master_detail.finished_material_id:
            cleaned_data["finished_material"] = master_detail.finished_material
            finished_material = cleaned_data["finished_material"]

        if master_detail:
            cleaned_data["dyeing_type"] = master_detail.dyeing_type or ""
            cleaned_data["dyeing_name"] = master_detail.dyeing_name or ""

            if not cleaned_data.get("rate"):
                cleaned_data["rate"] = master_detail.price or Decimal("0")

            if not cleaned_data.get("expected_loss_percent"):
                cleaned_data["expected_loss_percent"] = master_detail.weight_loss or Decimal("0")

            if master_detail.finished_material_id:
                cleaned_data["fabric_name"] = master_detail.finished_material.name or ""
                if getattr(master_detail.finished_material, "unit", None):
                    cleaned_data["unit"] = master_detail.finished_material.unit.name or ""
            elif finished_material:
                cleaned_data["fabric_name"] = finished_material.name or ""
                if getattr(finished_material, "unit", None):
                    cleaned_data["unit"] = finished_material.unit.name or ""

        elif finished_material:
            cleaned_data["fabric_name"] = finished_material.name or ""
            if getattr(finished_material, "unit", None):
                cleaned_data["unit"] = finished_material.unit.name or ""

        if total_qty < 0:
            self.add_error("total_qty", "Quantity cannot be negative.")

        if rate < 0:
            self.add_error("rate", "Rate cannot be negative.")

        if loss_percent < 0:
            self.add_error("expected_loss_percent", "Loss percent cannot be negative.")

        if loss_percent > 100:
            self.add_error("expected_loss_percent", "Loss percent cannot exceed 100.")

        cleaned_data["source_input_qty"] = total_qty
        cleaned_data["expected_output_qty"] = total_qty - (total_qty * loss_percent / Decimal("100"))
        cleaned_data["line_final_amount"] = total_qty * rate

        if not cleaned_data.get("greige_name") and source_item:
            cleaned_data["greige_name"] = (
                source_item.fabric_name
                or (source_item.material.name if source_item.material_id else "")
            )

        return cleaned_data


DyeingPurchaseOrderItemFormSet = inlineformset_factory(
    DyeingPurchaseOrder,
    DyeingPurchaseOrderItem,
    form=DyeingPurchaseOrderItemForm,
    fields=[
        "source_greige_po_item",
        "greige_name",
        "dyeing_master_detail",
        "finished_material",
        "fabric_name",
        "dyeing_type",
        "dyeing_name",
        "unit",
        "total_qty",
        "source_input_qty",
        "expected_loss_percent",
        "expected_output_qty",
        "rate",
        "line_final_amount",
        "remark",
    ],
    extra=0,
    can_delete=True,
)   


# ============================================================
# READY PURCHASE ORDER
# ============================================================

def _ready_finished_material_queryset(user):
    qs = Material.objects.filter(is_active=True, material_kind="finished")

    if user is not None:
        qs = qs.filter(Q(owner=user) | Q(owner__isnull=True))

    return qs.order_by("name")


class ReadyPurchaseOrderForm(forms.ModelForm):
    terms_template = forms.ModelChoiceField(
        queryset=TermsCondition.objects.none(),
        required=False,
        empty_label="Select saved terms",
        label="Saved Terms & Conditions",
    )
    shipping_address_choice = forms.ChoiceField(
        required=False,
        choices=[("", "Select shipping address")],
    )

    class Meta:
        model = ReadyPurchaseOrder
        fields = [
            "source_dyeing_po",
            "vendor",
            "firm",
            "po_number",                # Reference No.
            "internal_po_number",
            "po_date",
            "expected_delivery_date",
            "cancel_date",
            "shipping_address",
            "remarks",
            "terms_conditions",
        ]
        widgets = {
            "po_number": forms.TextInput(attrs={"placeholder": "Reference number"}),
            "internal_po_number": forms.TextInput(attrs={"placeholder": "Internal PO number"}),
            "po_date": forms.DateInput(attrs={"type": "date", "readonly": "readonly"}),
            "expected_delivery_date": forms.DateInput(attrs={"type": "date"}),
            "cancel_date": forms.DateInput(attrs={"type": "date"}),
            "shipping_address": forms.Textarea(attrs={"rows": 2, "placeholder": "Delivery or shipping address"}),
            "remarks": forms.Textarea(attrs={"rows": 3, "placeholder": "Notes / remarks"}),
            "terms_conditions": forms.Textarea(attrs={"rows": 3, "placeholder": "Terms & conditions"}),
        }

    def __init__(self, *args, user=None, source_dyeing_po=None, lock_source=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.shipping_address_map = {}

        self.fields["vendor"].queryset = (
            Vendor.objects.filter(owner=user, is_active=True).order_by("name")
            if user else Vendor.objects.none()
        )
        self.fields["firm"].queryset = (
            Firm.objects.filter(owner=user).prefetch_related("addresses").order_by("firm_name")
            if user else Firm.objects.none()
        )
        self.fields["terms_template"].queryset = (
            TermsCondition.objects.filter(owner=user, is_active=True).order_by("title")
            if user else TermsCondition.objects.none()
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

        self.fields["source_dyeing_po"].required = False
        self.fields["vendor"].required = True
        self.fields["firm"].required = False
        self.fields["internal_po_number"].required = False
        self.fields["po_date"].required = True
        self.fields["expected_delivery_date"].required = False
        self.fields["cancel_date"].required = False
        self.fields["shipping_address"].required = False
        self.fields["remarks"].required = False
        self.fields["terms_conditions"].required = False

        self.fields["source_dyeing_po"].empty_label = "Select source dyeing PO"
        self.fields["vendor"].empty_label = "Select vendor"
        self.fields["firm"].empty_label = "Select firm"

        self.fields["terms_template"].widget.attrs.update({
            "data-terms-template-select": "1",
        })

        if self.instance.pk and self.instance.terms_conditions:
            matched = self.fields["terms_template"].queryset.filter(content=self.instance.terms_conditions).first()
            if matched:
                self.initial["terms_template"] = matched.pk

        if source_dyeing_po is not None:
            self.fields["source_dyeing_po"].initial = source_dyeing_po
            if lock_source:
                self.fields["source_dyeing_po"].queryset = DyeingPurchaseOrder.objects.filter(pk=source_dyeing_po.pk)
                self.fields["source_dyeing_po"].disabled = True

            if not self.is_bound:
                if source_dyeing_po.vendor_id:
                    self.fields["vendor"].initial = source_dyeing_po.vendor_id
                if getattr(source_dyeing_po, "firm_id", None):
                    self.fields["firm"].initial = source_dyeing_po.firm_id
                self.fields["shipping_address"].initial = source_dyeing_po.shipping_address or ""
                self.fields["terms_conditions"].initial = getattr(source_dyeing_po, "terms_conditions", "") or ""

        if not self.is_bound:
            self.initial.setdefault("po_date", timezone.localdate())

        firm = self.instance.firm

        if self.is_bound:
            firm_id = (
                self.data.get(self.add_prefix("firm"))
                or self.data.get("firm")
                or ""
            ).strip()

            if firm_id:
                try:
                    firm = self.fields["firm"].queryset.get(pk=firm_id)
                except:
                    firm = None
        else:
            initial_firm_id = self.initial.get("firm") or self.fields["firm"].initial
            if initial_firm_id:
                firm = firm or self.fields["firm"].queryset.filter(pk=initial_firm_id).first()
        self._setup_shipping_addresses(firm)

    def _setup_shipping_addresses(self, firm):
        choices = [("", "Select shipping address")]
        address_map = {}

        if firm is not None:
            addresses = list(firm.addresses.order_by("-is_default", "id")) if hasattr(firm, "addresses") else []

            for address in addresses:
                key = str(address.pk)
                title = address.label or f"Address {address.pk}"
                full_address = address.full_address

                if address.is_default:
                    title = f"{title} (Default)"

                choices.append((key, title))
                address_map[key] = full_address

            if not address_map and getattr(firm, "full_address", ""):
                choices.append(("firm-default", f"{firm.firm_name} (Default)"))
                address_map["firm-default"] = firm.full_address

        # ✅ FIX: handle POST correctly
        if self.is_bound:
            selected_choice = (
                self.data.get(self.add_prefix("shipping_address_choice"))
                or self.data.get("shipping_address_choice")
                or ""
            ).strip()

            current_shipping_address = (
                self.data.get(self.add_prefix("shipping_address"))
                or self.data.get("shipping_address")
                or ""
            ).strip()
        else:
            selected_choice = (self.initial.get("shipping_address_choice") or "").strip()
            current_shipping_address = (
                self.initial.get("shipping_address")
                or getattr(self.instance, "shipping_address", "")
                or ""
            ).strip()

        if selected_choice and selected_choice in address_map:
            current_shipping_address = address_map[selected_choice]

        if not selected_choice:
            for key, value in address_map.items():
                if value == current_shipping_address:
                    selected_choice = key
                    break

        if not selected_choice and len(choices) > 1 and not current_shipping_address:
            selected_choice = choices[1][0]
            current_shipping_address = address_map.get(selected_choice, "")

        self.shipping_address_map = address_map
        self.fields["shipping_address_choice"].choices = choices

        self.initial["shipping_address_choice"] = selected_choice
        if current_shipping_address:
            self.initial["shipping_address"] = current_shipping_address

    def clean_po_number(self):
        return (self.cleaned_data.get("po_number") or "").strip()

    def clean_internal_po_number(self):
        return (self.cleaned_data.get("internal_po_number") or "").strip()

    def clean_shipping_address(self):
        value = _compact_spaces(self.cleaned_data.get("shipping_address"))
        if not value:
            selected_key = (self.cleaned_data.get("shipping_address_choice") or "").strip()
            value = _compact_spaces(self.shipping_address_map.get(selected_key, ""))
        return value

    def clean(self):
        # 🔥 FIX: ensure posted shipping choice is accepted
        if self.is_bound:
            posted_choice = (
                self.data.get(self.add_prefix("shipping_address_choice"))
                or self.data.get("shipping_address_choice")
                or ""
            ).strip()

            if posted_choice and posted_choice not in dict(self.fields["shipping_address_choice"].choices):
                self.fields["shipping_address_choice"].choices.append(
                    (posted_choice, "Selected shipping address")
                )
        cleaned_data = super().clean()

        source_dyeing_po = cleaned_data.get("source_dyeing_po")
        vendor = cleaned_data.get("vendor")
        po_date = cleaned_data.get("po_date")
        expected_delivery_date = cleaned_data.get("expected_delivery_date")
        shipping_address = (cleaned_data.get("shipping_address") or "").strip()

        if source_dyeing_po and vendor and source_dyeing_po.vendor_id != vendor.id:
            self.add_error("vendor", "Vendor must match the selected Dyeing PO vendor.")

        if expected_delivery_date and po_date and expected_delivery_date < po_date:
            self.add_error("expected_delivery_date", "Expected delivery date cannot be before PO date.")

        if not source_dyeing_po and not vendor:
            self.add_error("vendor", "Vendor is required for standalone Ready PO.")

        if not source_dyeing_po and not shipping_address and cleaned_data.get("firm"):
            cleaned_data["shipping_address"] = cleaned_data["firm"].full_address

        return cleaned_data


class ReadyPOInwardForm(forms.ModelForm):
    class Meta:
        model = ReadyPOInward
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
            if user else Vendor.objects.none()
        )
        self.fields["vendor"].empty_label = "Select vendor"

        self.fields["inward_type"].required = True
        self.fields["inward_type"].queryset = (
            InwardType.objects.filter(owner=user).order_by("name")
            if user else InwardType.objects.none()
        )
        self.fields["inward_type"].empty_label = "Select inward type"


# ============================================================
# READY PURCHASE ORDER
# ============================================================

def _ready_finished_material_queryset(user):
    qs = Material.objects.filter(is_active=True)

    if user is not None:
        qs = qs.filter(Q(owner=user) | Q(owner__isnull=True))

    try:
        qs = qs.filter(material_kind="finished")
    except Exception:
        pass

    return qs.order_by("name")



class ReadyPurchaseOrderItemForm(forms.ModelForm):
    finished_material = forms.ModelChoiceField(
        queryset=Material.objects.none(),
        required=False,
        empty_label="Select finished material",
    )
    unit = forms.ChoiceField(required=False, choices=[("", "Select unit")])

    class Meta:
        model = ReadyPurchaseOrderItem
        fields = [
            "finished_material",
            "fabric_name",
            "dyeing_name",
            "unit",
            "quantity",
            "remark",
        ]
        widgets = {
            "finished_material": forms.Select(),
            "fabric_name": forms.TextInput(attrs={
                "placeholder": "Auto from selected material",
                "readonly": "readonly",
            }),
            "dyeing_name": forms.TextInput(attrs={"placeholder": "Enter process / dyeing reference"}),
            "quantity": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "0.00"}),
            "remark": forms.TextInput(attrs={"placeholder": "Enter remark"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        material_qs = _ready_finished_material_queryset(user)
        self.fields["finished_material"].queryset = material_qs

        current_unit = (self.initial.get("unit") or getattr(self.instance, "unit", "") or "").strip()
        if self.is_bound:
            bound_unit = (self.data.get(self.add_prefix("unit")) or "").strip()
            if bound_unit:
                current_unit = bound_unit

        unit_choices = _material_unit_choices(user, current_unit)
        self.fields["unit"].choices = unit_choices
        self.fields["unit"].widget = forms.Select(choices=unit_choices)

        self.fields["finished_material"].required = False
        self.fields["fabric_name"].required = False
        self.fields["dyeing_name"].required = False
        self.fields["unit"].required = False
        self.fields["quantity"].required = False
        self.fields["remark"].required = False

        if not self.is_bound:
            instance_name = (getattr(self.instance, "fabric_name", "") or "").strip()
            if instance_name:
                matched_material = material_qs.filter(name__iexact=instance_name).first()
                if matched_material:
                    self.fields["finished_material"].initial = matched_material.pk
                    self.initial["fabric_name"] = matched_material.name
                    if not self.initial.get("unit"):
                        material_unit = getattr(matched_material, "unit", None)
                        if hasattr(material_unit, "name"):
                            self.initial["unit"] = material_unit.name
                        elif material_unit:
                            self.initial["unit"] = str(material_unit)

    def clean_unit(self):
        value = (self.cleaned_data.get("unit") or "").strip()
        valid_units = {choice for choice, _label in self.fields["unit"].choices if choice}
        if value and value not in valid_units:
            raise forms.ValidationError("Select a valid unit.")
        return value

    def clean(self):
        cleaned_data = super().clean()

        finished_material = cleaned_data.get("finished_material")
        fabric_name = _compact_spaces(cleaned_data.get("fabric_name"))
        dyeing_name = _compact_spaces(cleaned_data.get("dyeing_name"))
        quantity = cleaned_data.get("quantity")
        remark = _compact_spaces(cleaned_data.get("remark"))
        unit = (cleaned_data.get("unit") or "").strip()

        has_any_data = any([
            finished_material,
            fabric_name,
            dyeing_name,
            unit,
            quantity,
            remark,
        ])

        if not has_any_data:
            cleaned_data["fabric_name"] = ""
            cleaned_data["dyeing_name"] = ""
            cleaned_data["remark"] = ""
            cleaned_data["unit"] = ""
            return cleaned_data

        if not finished_material:
            self.add_error("finished_material", "Select finished material.")

        if finished_material:
            cleaned_data["fabric_name"] = finished_material.name

            if not unit:
                material_unit = getattr(finished_material, "unit", None)
                if hasattr(material_unit, "name"):
                    cleaned_data["unit"] = material_unit.name
                elif material_unit:
                    cleaned_data["unit"] = str(material_unit)

        if quantity in (None, ""):
            self.add_error("quantity", "Quantity is required.")
        elif quantity <= 0:
            self.add_error("quantity", "Quantity must be greater than 0.")

        cleaned_data["fabric_name"] = _compact_spaces(cleaned_data.get("fabric_name"))
        cleaned_data["dyeing_name"] = dyeing_name
        cleaned_data["remark"] = remark
        return cleaned_data


class BaseReadyPurchaseOrderItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        seen_rows = set()
        has_active_row = False

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            finished_material = form.cleaned_data.get("finished_material")
            finished_material_id = finished_material.pk if finished_material else None
            fabric_name = (form.cleaned_data.get("fabric_name") or "").strip().lower()
            dyeing_name = (form.cleaned_data.get("dyeing_name") or "").strip().lower()
            unit = (form.cleaned_data.get("unit") or "").strip().lower()
            quantity = form.cleaned_data.get("quantity")
            remark = (form.cleaned_data.get("remark") or "").strip()

            has_any_data = any([finished_material_id, fabric_name, dyeing_name, unit, quantity, remark])
            if not has_any_data:
                continue

            has_active_row = True

            duplicate_key = (finished_material_id or fabric_name, dyeing_name, unit)
            if (finished_material_id or fabric_name) and duplicate_key in seen_rows:
                form.add_error("finished_material", "Duplicate ready item row.")
            seen_rows.add(duplicate_key)

        if not has_active_row:
            raise forms.ValidationError("Add at least one ready item row.")


ReadyPurchaseOrderItemFormSet = inlineformset_factory(
    ReadyPurchaseOrder,
    ReadyPurchaseOrderItem,
    form=ReadyPurchaseOrderItemForm,
    formset=BaseReadyPurchaseOrderItemFormSet,
    fields=[
        "finished_material",
        "fabric_name",
        "dyeing_name",
        "unit",
        "quantity",
        "remark",
    ],
    extra=1,
    can_delete=True,
)


class ReadyPOInwardForm(forms.ModelForm):
    class Meta:
        model = ReadyPOInward
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
            if user else Vendor.objects.none()
        )
        self.fields["vendor"].empty_label = "Select vendor"

        self.fields["inward_type"].required = True
        self.fields["inward_type"].queryset = (
            InwardType.objects.filter(owner=user).order_by("name")
            if user else InwardType.objects.none()
        )
        self.fields["inward_type"].empty_label = "Select inward type"


def _dyeing_material_link_usage_rows(link):
    rows = []

    used_in_po_items = DyeingPurchaseOrderItem.objects.filter(
        dyeing_master_detail__link=link
    ).count()
    if used_in_po_items:
        rows.append({"label": "Dyeing PO Items", "count": used_in_po_items})

    return rows


class DyeingMaterialLinkForm(forms.ModelForm):
    class Meta:
        model = DyeingMaterialLink
        fields = ["vendor", "material_type", "material", "notes", "is_active"]
        widgets = {
            "vendor": forms.Select(),
            "material_type": forms.Select(),
            "material": forms.Select(),
            "notes": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Optional notes about vendor capability or process remarks",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        vendor_qs = Vendor.objects.filter(owner=user).order_by("name") if user else Vendor.objects.none()
        material_type_qs = MaterialType.objects.filter(
            owner=user,
            material_kind="greige",
        ).order_by("name") if user else MaterialType.objects.none()

        material_qs = (
            Material.objects
            .filter(Q(owner=user) | Q(owner__isnull=True), material_kind="greige", is_active=True)
            .select_related("material_type")
            .order_by("name")
            if user else Material.objects.none()
        )

        self.fields["vendor"].queryset = vendor_qs
        self.fields["vendor"].empty_label = "Select Vendor"

        self.fields["material_type"].queryset = material_type_qs
        self.fields["material_type"].empty_label = "Select Material Type"

        self.fields["material"].queryset = material_qs
        self.fields["material"].empty_label = "Select Material"

    def clean(self):
        cleaned_data = super().clean()

        vendor = cleaned_data.get("vendor")
        material_type = cleaned_data.get("material_type")
        material = cleaned_data.get("material")

        if self.user is not None and vendor and getattr(vendor, "owner_id", None) != self.user.id:
            self.add_error("vendor", "Selected vendor is not available for this user.")

        if self.user is not None and material_type and getattr(material_type, "owner_id", None) != self.user.id:
            self.add_error("material_type", "Selected material type is not available for this user.")

        if material_type and getattr(material_type, "material_kind", "") != "greige":
            self.add_error("material_type", "Only greige material type is allowed in Dyeing Master.")

        if material and getattr(material, "material_kind", "") != "greige":
            self.add_error("material", "Only greige material is allowed in Dyeing Master.")

        if material and material_type and getattr(material, "material_type_id", None) != material_type.id:
            self.add_error("material", "Selected material does not belong to selected material type.")

        if self.user is not None and vendor and material:
            qs = DyeingMaterialLink.objects.filter(
                owner=self.user,
                vendor=vendor,
                material=material,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                self.add_error("material", "This vendor-greige link already exists.")

        return cleaned_data


class DyeingMaterialLinkDetailForm(forms.ModelForm):
    class Meta:
        model = DyeingMaterialLinkDetail
        fields = [
            "finished_material",
            "dyeing_type",
            "dyeing_name",
            "percentage_no_of_colors",
            "weight_loss",
            "price",
            "sort_order",
            "is_active",
        ]
        widgets = {
            "finished_material": forms.Select(),
            "dyeing_type": forms.Select(),
            "dyeing_name": forms.TextInput(attrs={
                "placeholder": "Enter dyeing name / process name",
            }),
            "percentage_no_of_colors": forms.NumberInput(attrs={
                "placeholder": "e.g. 5 or 2",
                "step": "0.01",
                "min": "0",
            }),
            "weight_loss": forms.NumberInput(attrs={
                "placeholder": "e.g. 5.00",
                "step": "0.01",
                "min": "0",
            }),
            "price": forms.NumberInput(attrs={
                "placeholder": "Enter price",
                "step": "0.01",
                "min": "0",
            }),
            "sort_order": forms.NumberInput(attrs={
                "step": "1",
                "min": "0",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        self.fields["finished_material"].required = True

        # ✅ Important: new rows should be active by default
        self.fields["is_active"].initial = True
        if not self.instance.pk:
            self.initial["is_active"] = True

        finished_qs = Material.objects.filter(material_kind="finished", is_active=True)

        if self.user is not None:
            finished_qs = finished_qs.filter(
                Q(owner=self.user) | Q(owner__isnull=True)
            )

        self.fields["finished_material"].queryset = finished_qs.order_by("name")

    def clean_finished_material(self):
        finished_material = self.cleaned_data.get("finished_material")

        if not finished_material:
            raise forms.ValidationError("Finished material is required.")

        if getattr(finished_material, "material_kind", "") != "finished":
            raise forms.ValidationError("Only finished material is allowed here.")

        if self.user is not None:
            owner_id = getattr(finished_material, "owner_id", None)
            if owner_id not in (self.user.id, None):
                raise forms.ValidationError("Selected finished material is not available for this user.")

        return finished_material

    def clean_dyeing_name(self):
        value = (self.cleaned_data.get("dyeing_name") or "").strip()
        if not value:
            raise forms.ValidationError("Dyeing name is required.")
        return value

    def clean_percentage_no_of_colors(self):
        value = self.cleaned_data.get("percentage_no_of_colors")
        if value is not None and value < 0:
            raise forms.ValidationError("Percentage / no. of colors cannot be negative.")
        return value

    def clean_weight_loss(self):
        value = self.cleaned_data.get("weight_loss")
        if value is not None and value < 0:
            raise forms.ValidationError("Weight loss cannot be negative.")
        return value

    def clean_price(self):
        value = self.cleaned_data.get("price")
        if value is not None and value < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return value


class BaseDyeingMaterialLinkDetailFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        if any(self.errors):
            return

        seen_keys = set()
        active_rows = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue

            active_rows += 1

            finished_material = form.cleaned_data.get("finished_material")
            dyeing_type = (form.cleaned_data.get("dyeing_type") or "").strip().lower()
            dyeing_name = (form.cleaned_data.get("dyeing_name") or "").strip().lower()

            key = (
                finished_material.pk if finished_material else None,
                dyeing_type,
                dyeing_name,
            )

            if key in seen_keys:
                raise forms.ValidationError(
                    "Duplicate dyeing row found. Same finished material, dyeing type, and dyeing name cannot be repeated."
                )

            seen_keys.add(key)

        if active_rows == 0:
            raise forms.ValidationError("Add at least one dyeing detail row.")


DyeingMaterialLinkDetailFormSet = inlineformset_factory(
    DyeingMaterialLink,
    DyeingMaterialLinkDetail,
    form=DyeingMaterialLinkDetailForm,
    formset=BaseDyeingMaterialLinkDetailFormSet,
    extra=1,
    can_delete=True,
)


# ============================================================
# BOM
# ============================================================

class BOMForm(forms.ModelForm):
    class Meta:
        model = BOM
        fields = [
            "bom_code",
            "sku",
            "product_name",
            "character_name",
            "license_name",
            "catalogue",
            "brand",
            "category",
            "main_category",
            "sub_category",
            "pattern_type",
            "gender",
            "size_type",
            "mrp",
            "color",
            "drawcord",
            "tie_dye_price",
            "price",
            "selling_price",
            "maintenance_price",
            "damage_percent",
            "final_price",
            "notes",
            "status",
        ]
        widgets = {
            "bom_code": forms.TextInput(attrs={"placeholder": "Enter BOM code"}),
            "sku": forms.TextInput(attrs={"placeholder": "Enter SKU"}),
            "product_name": forms.TextInput(attrs={"placeholder": "Enter product name"}),
            "character_name": forms.TextInput(attrs={"placeholder": "Enter character name"}),
            "license_name": forms.TextInput(attrs={"placeholder": "Enter license name"}),
            "catalogue": forms.Select(),
            "brand": forms.Select(),
            "category": forms.Select(),
            "main_category": forms.Select(),
            "sub_category": forms.Select(),
            "pattern_type": forms.Select(),
            "gender": forms.TextInput(attrs={"placeholder": "Enter gender"}),
            "size_type": forms.Select(),
            "mrp": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Enter MRP"}),
            "color": forms.TextInput(attrs={"placeholder": "Enter color"}),
            "drawcord": forms.TextInput(attrs={"placeholder": "Enter drawcord details"}),
            "tie_dye_price": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Enter tie dye price"}),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Enter price"}),
            "selling_price": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Enter selling price"}),
            "maintenance_price": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Enter maintenance price"}),
            "damage_percent": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Damage %"}),
            "final_price": forms.NumberInput(attrs={"step": "0.01", "min": "0", "readonly": "readonly", "placeholder": "Final price"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Enter notes"}),
            "status": forms.Select(),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if user:
            self.fields["catalogue"].queryset = Catalogue.objects.filter(owner=user).order_by("name")
            self.fields["brand"].queryset = Brand.objects.filter(owner=user).order_by("name")
            self.fields["category"].queryset = Category.objects.filter(owner=user).order_by("name")
            self.fields["main_category"].queryset = MainCategory.objects.filter(owner=user).order_by("name")
            self.fields["sub_category"].queryset = SubCategory.objects.filter(owner=user).select_related("main_category").order_by("main_category__name", "name")
            self.fields["pattern_type"].queryset = PatternType.objects.filter(owner=user).order_by("name")
        else:
            self.fields["catalogue"].queryset = Catalogue.objects.none()
            self.fields["brand"].queryset = Brand.objects.none()
            self.fields["category"].queryset = Category.objects.none()
            self.fields["main_category"].queryset = MainCategory.objects.none()
            self.fields["sub_category"].queryset = SubCategory.objects.none()
            self.fields["pattern_type"].queryset = PatternType.objects.none()

        self.fields["catalogue"].required = False
        self.fields["brand"].required = False
        self.fields["category"].required = False
        self.fields["main_category"].required = False
        self.fields["sub_category"].required = False
        self.fields["pattern_type"].required = False
        self.fields["notes"].required = False
        self.fields["character_name"].required = False
        self.fields["license_name"].required = False
        self.fields["mrp"].required = False
        self.fields["color"].required = False
        self.fields["drawcord"].required = False
        self.fields["tie_dye_price"].required = False
        self.fields["price"].required = False
        self.fields["selling_price"].required = False
        self.fields["maintenance_price"].required = False
        self.fields["damage_percent"].required = False
        self.fields["final_price"].required = False
        self.fields["catalogue"].empty_label = "Select catalogue"
        self.fields["brand"].empty_label = "Select brand"
        self.fields["category"].empty_label = "Select category"
        self.fields["main_category"].empty_label = "Select main category"
        self.fields["sub_category"].empty_label = "Select sub category"
        self.fields["pattern_type"].empty_label = "Select pattern type"

    def clean_bom_code(self):
        value = (self.cleaned_data.get("bom_code") or "").strip().upper()
        if not value:
            raise forms.ValidationError("BOM code is required.")

        qs = BOM.objects.filter(owner=self.user, bom_code__iexact=value) if self.user else BOM.objects.none()
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("This BOM code already exists.")
        return value

    def clean_sku(self):
        value = (self.cleaned_data.get("sku") or "").strip().upper()
        if not value:
            raise forms.ValidationError("SKU is required.")

        qs = BOM.objects.filter(owner=self.user, sku__iexact=value) if self.user else BOM.objects.none()
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("This SKU already exists.")
        return value

    def clean_product_name(self):
        value = (self.cleaned_data.get("product_name") or "").strip()
        if not value:
            raise forms.ValidationError("Product name is required.")
        return value

    def clean_character_name(self):
        return (self.cleaned_data.get("character_name") or "").strip()

    def clean_license_name(self):
        return (self.cleaned_data.get("license_name") or "").strip()

    def clean_color(self):
        return (self.cleaned_data.get("color") or "").strip()

    def clean_drawcord(self):
        return (self.cleaned_data.get("drawcord") or "").strip()

    def clean_mrp(self):
        value = self.cleaned_data.get("mrp") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("MRP cannot be negative.")
        return value

    def clean_tie_dye_price(self):
        value = self.cleaned_data.get("tie_dye_price") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Tie dye price cannot be negative.")
        return value

    def clean_price(self):
        value = self.cleaned_data.get("price") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return value

    def clean_selling_price(self):
        value = self.cleaned_data.get("selling_price") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Selling price cannot be negative.")
        return value

    def clean_maintenance_price(self):
        value = self.cleaned_data.get("maintenance_price") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Maintenance price cannot be negative.")
        return value

    def clean(self):
        cleaned = super().clean()
        main_category = cleaned.get("main_category")
        sub_category = cleaned.get("sub_category")

        if sub_category and main_category and sub_category.main_category_id != main_category.id:
            self.add_error("sub_category", "Selected sub category does not belong to selected main category.")

        return cleaned

    def clean_damage_percent(self):
        value = self.cleaned_data.get("damage_percent") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Damage percent cannot be negative.")
        return value

    def clean_final_price(self):
        value = self.cleaned_data.get("final_price") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Final price cannot be negative.")
        return value

class BOMImageForm(forms.ModelForm):
    MAX_IMAGE_SIZE = 5 * 1024 * 1024

    class Meta:
        model = BOMImage
        fields = ["image", "sort_order"]
        widgets = {
            "image": forms.ClearableFileInput(attrs={"accept": "image/*", "class": "bom-image-input"}),
            "sort_order": forms.HiddenInput(),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            return image

        file_name = (getattr(image, "name", "") or "").lower()
        allowed_ext = (".jpg", ".jpeg", ".png", ".webp", ".gif")
        if file_name and not file_name.endswith(allowed_ext):
            raise forms.ValidationError("Upload a valid image file (JPG, JPEG, PNG, WEBP, or GIF).")

        content_type = getattr(image, "content_type", "") or ""
        if content_type and not content_type.startswith("image/"):
            raise forms.ValidationError("The selected file must be an image.")

        if getattr(image, "size", 0) > self.MAX_IMAGE_SIZE:
            raise forms.ValidationError("Image size must be 5 MB or less.")

        return image


class BOMMaterialItemForm(forms.ModelForm):
    class Meta:
        model = BOMMaterialItem
        fields = [
            "material",
            "unit",
            "cost_per_unit",
            "avg",
            "cost",
            "sort_order",
        ]
        widgets = {
            "material": forms.Select(),
            "unit": forms.Select(),
            "cost_per_unit": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "avg": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "cost": forms.NumberInput(attrs={"step": "0.01", "min": "0", "readonly": "readonly"}),
            "sort_order": forms.HiddenInput(),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        self.fields["material"].queryset = (
            Material.objects
            .filter(
                Q(owner=user) | Q(owner__isnull=True),
                material_kind__in=["yarn", "greige", "finished", "trim"],
                is_active=True,
            )
            .select_related("material_type")
            .order_by("name")
            if user else Material.objects.none()
        )

        self.fields["unit"].queryset = (
            MaterialUnit.objects.filter(owner=user).order_by("name")
            if user else MaterialUnit.objects.none()
        )

        self.fields["material"].empty_label = "Select material"
        self.fields["unit"].empty_label = "Select unit"
        self.fields["unit"].required = False

    def clean_material(self):
        value = self.cleaned_data.get("material")
        if not value:
            return value

        if getattr(value, "material_kind", "") not in {"yarn", "greige", "finished", "trim"}:
            raise forms.ValidationError("Select a valid material.")

        if self.user is not None and getattr(value, "owner_id", None) not in (self.user.id, None):
            raise forms.ValidationError("Selected material is not available for this user.")

        return value

    def clean_unit(self):
        value = self.cleaned_data.get("unit")
        if not value:
            return value

        if self.user is not None and getattr(value, "owner_id", None) != self.user.id:
            raise forms.ValidationError("Selected unit is not available for this user.")

        return value

    def clean_cost_per_unit(self):
        value = self.cleaned_data.get("cost_per_unit") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Cost per unit cannot be negative.")
        return value

    def clean_avg(self):
        value = self.cleaned_data.get("avg") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Average / consumption cannot be negative.")
        return value

    def clean(self):
        cleaned = super().clean()
        cost_per_unit = cleaned.get("cost_per_unit") or Decimal("0")
        avg = cleaned.get("avg") or Decimal("0")
        cleaned["cost"] = (cost_per_unit * avg).quantize(Decimal("0.01"))
        return cleaned


class BOMAccessoryItemForm(forms.ModelForm):
    class Meta:
        model = BOMAccessoryItem
        fields = [
            "accessory",
            "unit",
            "cost_per_unit",
            "avg",
            "cost",
            "sort_order",
        ]
        widgets = {
            "accessory": forms.Select(),
            "unit": forms.Select(),
            "cost_per_unit": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "avg": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "cost": forms.NumberInput(attrs={"step": "0.01", "min": "0", "readonly": "readonly"}),
            "sort_order": forms.HiddenInput(),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        self.fields["accessory"].queryset = (
            Accessory.objects.filter(owner=user).order_by("name")
            if user else Accessory.objects.none()
        )
        self.fields["unit"].queryset = (
            MaterialUnit.objects.filter(owner=user).order_by("name")
            if user else MaterialUnit.objects.none()
        )

        self.fields["accessory"].empty_label = "Select accessory"
        self.fields["unit"].empty_label = "Select unit"
        self.fields["unit"].required = False

    def clean_accessory(self):
        value = self.cleaned_data.get("accessory")
        if not value:
            return value

        if self.user is not None and getattr(value, "owner_id", None) != self.user.id:
            raise forms.ValidationError("Selected accessory is not available for this user.")

        return value

    def clean_unit(self):
        value = self.cleaned_data.get("unit")
        if not value:
            return value

        if self.user is not None and getattr(value, "owner_id", None) != self.user.id:
            raise forms.ValidationError("Selected unit is not available for this user.")

        return value

    def clean_cost_per_unit(self):
        value = self.cleaned_data.get("cost_per_unit") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Cost per unit cannot be negative.")
        return value

    def clean_avg(self):
        value = self.cleaned_data.get("avg") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Average / consumption cannot be negative.")
        return value

    def clean(self):
        cleaned = super().clean()
        cost_per_unit = cleaned.get("cost_per_unit") or Decimal("0")
        avg = cleaned.get("avg") or Decimal("0")
        cleaned["cost"] = (cost_per_unit * avg).quantize(Decimal("0.01"))
        return cleaned

def _bom_row_has_any_value(cleaned_data, field_names):
    for field_name in field_names:
        value = cleaned_data.get(field_name)
        if isinstance(value, str):
            if value.strip():
                return True
        elif value not in (None, ""):
            return True
    return False


class BaseBOMMaterialItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        seen_material_ids = set()

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue

            if not _bom_row_has_any_value(form.cleaned_data, ["material", "unit", "cost_per_unit", "avg"]):
                continue

            material = form.cleaned_data.get("material")
            if not material:
                form.add_error("material", "Select material.")
                continue

            if material.pk in seen_material_ids:
                form.add_error("material", "This material is already added in the BOM.")
            seen_material_ids.add(material.pk)


class BaseBOMAccessoryItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        seen_accessory_ids = set()

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue

            if not _bom_row_has_any_value(form.cleaned_data, ["accessory", "unit", "cost_per_unit", "avg"]):
                continue

            accessory = form.cleaned_data.get("accessory")
            if not accessory:
                form.add_error("accessory", "Select accessory.")
                continue

            if accessory.pk in seen_accessory_ids:
                form.add_error("accessory", "This accessory is already added in the BOM.")
            seen_accessory_ids.add(accessory.pk)








class BaseBOMExpenseItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        seen_expense_ids = set()

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue

            if not _bom_row_has_any_value(form.cleaned_data, ["expense", "price"]):
                continue

            expense = form.cleaned_data.get("expense")
            if not expense:
                form.add_error("expense", "Select expense.")
                continue

            if expense.pk in seen_expense_ids:
                form.add_error("expense", "This expense is already added in the BOM.")
            seen_expense_ids.add(expense.pk)


BOMMaterialItemFormSet = inlineformset_factory(
    BOM,
    BOMMaterialItem,
    form=BOMMaterialItemForm,
    extra=1,
    can_delete=True,
)

BOMImageFormSet = inlineformset_factory(
    BOM,
    BOMImage,
    form=BOMImageForm,
    extra=1,
    can_delete=True,
)

BOMAccessoryItemFormSet = inlineformset_factory(
    BOM,
    BOMAccessoryItem,
    form=BOMAccessoryItemForm,
    extra=1,
    can_delete=True,
)

def _bom_truthy_flag(value):
    return str(value or "").strip().lower() in {"1", "true", "on", "yes"}


class BOMJobberTypeProcessForm(forms.ModelForm):
    class Meta:
        model = BOMJobberTypeProcess
        fields = ["jobber_type", "price", "sort_order"]
        widgets = {
            "jobber_type": forms.Select(),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "sort_order": forms.HiddenInput(),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["jobber_type"].queryset = (
            JobberType.objects.filter(owner=user).order_by("name")
            if user else JobberType.objects.none()
        )
        self.fields["jobber_type"].empty_label = "Select jobber type"

    def clean_price(self):
        value = self.cleaned_data.get("price") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return value


class BOMJobberDetailForm(forms.ModelForm):
    class Meta:
        model = BOMJobberDetail
        fields = ["jobber", "jobber_type", "price", "sort_order"]
        widgets = {
            "jobber": forms.Select(),
            "jobber_type": forms.Select(),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0", "readonly": "readonly"}),
            "sort_order": forms.HiddenInput(),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["jobber"].queryset = (
            Jobber.objects.filter(owner=user, is_active=True)
            .select_related("jobber_type")
            .order_by("name")
            if user else Jobber.objects.none()
        )
        self.fields["jobber_type"].queryset = (
            JobberType.objects.filter(owner=user).order_by("name")
            if user else JobberType.objects.none()
        )

        self.fields["jobber"].empty_label = "Select jobber"
        self.fields["jobber_type"].empty_label = "Select jobber type"

    def clean_price(self):
        value = self.cleaned_data.get("price") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return value

    def clean(self):
        cleaned = super().clean()

        jobber = cleaned.get("jobber")
        jobber_type = cleaned.get("jobber_type")

        if not jobber:
            return cleaned

        if not jobber.jobber_type_id:
            self.add_error("jobber", "Selected jobber does not have a jobber type assigned in masters.")
            return cleaned

        expected_type = jobber.jobber_type

        if jobber_type and jobber_type.pk != expected_type.pk:
            self.add_error(
                "jobber_type",
                f'"{jobber.name}" belongs to "{expected_type.name}". Please select the matching jobber type.',
            )

        cleaned["jobber_type"] = expected_type
        return cleaned


class BaseBOMJobberTypeProcessFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        seen_types = set()

        for form in self.forms:
            if not getattr(form, "cleaned_data", None):
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            jobber_type = form.cleaned_data.get("jobber_type")
            price = form.cleaned_data.get("price")

            if not jobber_type and price in [None, "", Decimal("0"), 0]:
                continue

            if not jobber_type:
                form.add_error("jobber_type", "Select jobber type.")
                continue

            if jobber_type.pk in seen_types:
                form.add_error(
                    "jobber_type",
                    "This jobber type is already added in process mapping."
                )
                continue

            seen_types.add(jobber_type.pk)

            if price is not None and price < 0:
                form.add_error("price", "Price cannot be negative.")


class BaseBOMJobberDetailFormSet(BaseInlineFormSet):
    process_prefix = "jobber_processes"

    def _get_process_price_map(self):
        if self.is_bound:
            price_map = {}
            total_forms = 0

            try:
                total_forms = int(self.data.get(f"{self.process_prefix}-TOTAL_FORMS") or 0)
            except (TypeError, ValueError):
                total_forms = 0

            for index in range(total_forms):
                if _bom_truthy_flag(self.data.get(f"{self.process_prefix}-{index}-DELETE")):
                    continue

                jobber_type_id = (self.data.get(f"{self.process_prefix}-{index}-jobber_type") or "").strip()
                if not jobber_type_id:
                    continue

                raw_price = (self.data.get(f"{self.process_prefix}-{index}-price") or "").strip()

                try:
                    price_map[jobber_type_id] = Decimal(raw_price or "0")
                except Exception:
                    price_map[jobber_type_id] = Decimal("0")

            return price_map

        return {
            str(row.jobber_type_id): (row.price or Decimal("0"))
            for row in self.instance.jobber_type_processes.all()
            if row.jobber_type_id
        }

    def clean(self):
        super().clean()

        process_price_map = self._get_process_price_map()
        seen_jobber_processes = set()

        for form in self.forms:
            if not getattr(form, "cleaned_data", None):
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            jobber = form.cleaned_data.get("jobber")
            jobber_type = form.cleaned_data.get("jobber_type")

            if not jobber and not jobber_type:
                continue

            if not jobber:
                form.add_error("jobber", "Select jobber.")
                continue

            if not getattr(jobber, "jobber_type_id", None):
                form.add_error(
                    "jobber",
                    f'"{jobber.name}" does not have a jobber type assigned in masters.'
                )
                continue

            expected_type = jobber.jobber_type

            duplicate_key = (jobber.pk, expected_type.pk)
            if duplicate_key in seen_jobber_processes:
                form.add_error(
                    "jobber",
                    "This jobber is already added for this process in this BOM."
                )
                continue

            seen_jobber_processes.add(duplicate_key)

            if jobber_type and jobber_type.pk != expected_type.pk:
                form.add_error(
                    "jobber_type",
                    f'"{jobber.name}" belongs to "{expected_type.name}". Please select the matching jobber type.',
                )
                continue

            mapped_price = process_price_map.get(str(expected_type.pk))

            if mapped_price is None:
                form.add_error(
                    "jobber_type",
                    f'Add a Jobber Type Process row for "{expected_type.name}" first.',
                )
                continue

            form.cleaned_data["jobber_type"] = expected_type
            form.cleaned_data["price"] = mapped_price
            form.instance.jobber_type = expected_type
            form.instance.price = mapped_price


BOMJobberTypeProcessFormSet = inlineformset_factory(
    BOM,
    BOMJobberTypeProcess,
    form=BOMJobberTypeProcessForm,
    formset=BaseBOMJobberTypeProcessFormSet,
    extra=1,
    can_delete=True,
)

BOMJobberDetailFormSet = inlineformset_factory(
    BOM,
    BOMJobberDetail,
    form=BOMJobberDetailForm,
    formset=BaseBOMJobberDetailFormSet,
    extra=1,
    can_delete=True,
)
    
BOMMaterialItemFormSet = inlineformset_factory(
    BOM,
    BOMMaterialItem,
    form=BOMMaterialItemForm,
    formset=BaseBOMMaterialItemFormSet,
    extra=1,
    can_delete=True,
)

BOMImageFormSet = inlineformset_factory(
    BOM,
    BOMImage,
    form=BOMImageForm,
    extra=1,
    can_delete=True,
)

BOMAccessoryItemFormSet = inlineformset_factory(
    BOM,
    BOMAccessoryItem,
    form=BOMAccessoryItemForm,
    formset=BaseBOMAccessoryItemFormSet,
    extra=1,
    can_delete=True,
)




class BOMExpenseItemForm(forms.ModelForm):
    class Meta:
        model = BOMExpenseItem
        fields = ["expense", "price", "sort_order"]
        widgets = {
            "expense": forms.Select(),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Price (₹)"}),
            "sort_order": forms.HiddenInput(),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["expense"].queryset = (
            Expense.objects.filter(owner=user).order_by("name")
            if user else Expense.objects.none()
        )
        self.fields["expense"].empty_label = "Select factory expense"

    def clean_price(self):
        value = self.cleaned_data.get("price") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return value
    
BOMExpenseItemFormSet = inlineformset_factory(
    BOM,
    BOMExpenseItem,
    form=BOMExpenseItemForm,
    formset=BaseBOMExpenseItemFormSet,
    extra=1,
    can_delete=True,
)


class ProgramBOMChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        sku = (obj.sku or "").strip()
        product = (obj.product_name or "").strip()
        if sku and product:
            return f"{sku} - {product}"
        return sku or product or str(obj.pk)


class ProgramForm(forms.ModelForm):
    bom = ProgramBOMChoiceField(queryset=BOM.objects.none(), label="SKU Name")

    class Meta:
        model = Program
        fields = [
            "program_no",
            "program_date",
            "finishing_date",
            "bom",
            "firm",
            "total_qty",
            "ratio",
            "damage",
            "glt_days",
            "glt_on_100_days",
            "status",
            "is_verified",
        ]
        widgets = {
            "program_no": forms.TextInput(
                attrs={
                    "readonly": "readonly",
                    "placeholder": "Auto generated",
                }
            ),
            "program_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "readonly": "readonly",
                }
            ),
            "finishing_date": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
            "bom": forms.Select(),
            "firm": forms.Select(),
            "total_qty": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Enter total quantity",
                }
            ),
            "ratio": forms.TextInput(
                attrs={
                    "placeholder": "Enter ratio (example: 1:2:2:1)",
                }
            ),
            "damage": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Enter damage",
                }
            ),
            "glt_days": forms.NumberInput(
                attrs={
                    "min": "0",
                    "placeholder": "Enter GLT days",
                }
            ),
            "glt_on_100_days": forms.NumberInput(
                attrs={
                    "min": "0",
                    "placeholder": "Enter GLT on 100 days",
                }
            ),
            "status": forms.Select(),
            "is_verified": forms.CheckboxInput(),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if user:
            self.fields["firm"].queryset = Firm.objects.filter(owner=user).order_by("firm_name")
            self.fields["bom"].queryset = (
                BOM.objects.filter(owner=user)
                .select_related(
                    "brand",
                    "category",
                    "main_category",
                    "sub_category",
                    "pattern_type",
                    "catalogue",
                )
                .order_by("sku")
            )
        else:
            self.fields["firm"].queryset = Firm.objects.none()
            self.fields["bom"].queryset = BOM.objects.none()

        self.fields["firm"].empty_label = "Select firm"
        self.fields["bom"].empty_label = "Select SKU"

        self.fields["finishing_date"].required = False
        self.fields["ratio"].required = False
        self.fields["damage"].required = False
        self.fields["glt_days"].required = False
        self.fields["glt_on_100_days"].required = False
        self.fields["is_verified"].required = False

        if not self.instance.pk and user:
            self.initial.setdefault("program_no", Program.next_program_no(user))
            self.initial.setdefault("program_date", timezone.localdate())
            self.initial.setdefault("status", "open")
            self.initial.setdefault("is_verified", False)

            user_firm = Firm.objects.filter(owner=user).first()
            if user_firm:
                self.initial.setdefault("firm", user_firm.pk)

    def clean_program_no(self):
        if self.instance.pk:
            return (self.cleaned_data.get("program_no") or self.instance.program_no or "").strip().upper()

        if self.user:
            return Program.next_program_no(self.user)

        return (self.cleaned_data.get("program_no") or "").strip().upper()

    def clean_program_date(self):
        if self.instance.pk:
            return self.cleaned_data.get("program_date") or self.instance.program_date
        return timezone.localdate()

    def clean_total_qty(self):
        value = self.cleaned_data.get("total_qty") or Decimal("0")
        if value <= 0:
            raise forms.ValidationError("Total quantity must be greater than 0.")
        return value

    def clean_ratio(self):
        return (self.cleaned_data.get("ratio") or "").strip()

    def clean_damage(self):
        value = self.cleaned_data.get("damage") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Damage cannot be negative.")
        return value

    def clean_glt_days(self):
        value = self.cleaned_data.get("glt_days")
        if value is None:
            return 0
        if value < 0:
            raise forms.ValidationError("GLT days cannot be negative.")
        return value

    def clean_glt_on_100_days(self):
        value = self.cleaned_data.get("glt_on_100_days")
        if value is None:
            return 0
        if value < 0:
            raise forms.ValidationError("GLT on 100 days cannot be negative.")
        return value

    def clean(self):
        cleaned = super().clean()

        program_date = cleaned.get("program_date")
        finishing_date = cleaned.get("finishing_date")
        bom = cleaned.get("bom")
        firm = cleaned.get("firm")

        if not bom:
            self.add_error("bom", "SKU is required.")

        if not firm:
            self.add_error("firm", "Firm is required.")

        if finishing_date and program_date and finishing_date < program_date:
            self.add_error("finishing_date", "Finishing date cannot be before program date.")

        return cleaned

class DispatchChallanForm(forms.ModelForm):
    class Meta:
        model = DispatchChallan
        fields = [
            "challan_no",
            "challan_date",
            "program",
            "client",
            "firm",
            "driver_name",
            "lr_no",
            "transport_name",
            "vehicle_no",
            "remarks",
        ]
        widgets = {
            "challan_no": forms.TextInput(attrs={"placeholder": "Auto / challan number"}),
            "challan_date": forms.DateInput(attrs={"type": "date"}),
            "program": forms.Select(),
            "client": forms.Select(),
            "firm": forms.Select(),
            "driver_name": forms.TextInput(attrs={"placeholder": "Driver name"}),
            "lr_no": forms.TextInput(attrs={"placeholder": "LR number"}),
            "transport_name": forms.TextInput(attrs={"placeholder": "Transport name"}),
            "vehicle_no": forms.TextInput(attrs={"placeholder": "Vehicle number"}),
            "remarks": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional remarks"}),
        }

    def __init__(self, *args, user=None, program=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.program_obj = program

        self.fields["program"].queryset = (
            Program.objects.filter(owner=user).select_related("bom", "firm").order_by("-id")
            if user else Program.objects.none()
        )
        self.fields["client"].queryset = (
            Client.objects.filter(owner=user, is_active=True).order_by("name")
            if user else Client.objects.none()
        )
        self.fields["firm"].queryset = (
            Firm.objects.filter(owner=user).order_by("firm_name")
            if user else Firm.objects.none()
        )

        self.fields["program"].empty_label = "Select program"
        self.fields["client"].empty_label = "Select client"
        self.fields["firm"].empty_label = "Select firm"

        if program is not None:
            self.fields["program"].queryset = Program.objects.filter(pk=program.pk, owner=user)
            self.fields["program"].initial = program
            self.fields["program"].disabled = True

            if getattr(program, "firm_id", None):
                self.fields["firm"].queryset = Firm.objects.filter(pk=program.firm_id, owner=user)
                self.fields["firm"].initial = program.firm
                self.fields["firm"].disabled = True

        if not self.is_bound:
            self.fields["challan_date"].initial = timezone.localdate()

    def clean_driver_name(self):
        return (self.cleaned_data.get("driver_name") or "").strip()

    def clean_lr_no(self):
        return (self.cleaned_data.get("lr_no") or "").strip()

    def clean_transport_name(self):
        return (self.cleaned_data.get("transport_name") or "").strip()

    def clean_vehicle_no(self):
        return (self.cleaned_data.get("vehicle_no") or "").strip().upper()

    def clean_remarks(self):
        return (self.cleaned_data.get("remarks") or "").strip()

class ProgramJobberChallanForm(forms.ModelForm):
    class Meta:
        model = ProgramJobberChallan
        fields = [
            "challan_date",
            "driver_name",
            "lr_no",
            "transport_name",
            "vehicle_no",
            "gate_pass_no",
            "expected_return_date",
            "remarks",
        ]
        widgets = {
            "challan_date": forms.DateInput(attrs={"type": "date"}),
            "expected_return_date": forms.DateInput(attrs={"type": "date"}),
            "remarks": forms.Textarea(attrs={"rows": 3, "placeholder": "Remarks"}),
            "driver_name": forms.TextInput(attrs={"placeholder": "Driver name"}),
            "lr_no": forms.TextInput(attrs={"placeholder": "LR No"}),
            "transport_name": forms.TextInput(attrs={"placeholder": "Transport"}),
            "vehicle_no": forms.TextInput(attrs={"placeholder": "Vehicle no"}),
            "gate_pass_no": forms.TextInput(attrs={"placeholder": "Gate pass no"}),
        }

    def __init__(self, *args, user=None, program=None, start_jobber=None, **kwargs):
        self.user = user
        self.program = program
        self.start_jobber = start_jobber
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} jf-input".strip()

        self.fields["challan_date"].required = True
        self.fields["driver_name"].required = False
        self.fields["lr_no"].required = False
        self.fields["transport_name"].required = False
        self.fields["vehicle_no"].required = False
        self.fields["gate_pass_no"].required = False
        self.fields["expected_return_date"].required = False
        self.fields["remarks"].required = False

        if not self.instance.pk and not self.initial.get("challan_date"):
            self.initial["challan_date"] = timezone.localdate()

    def clean_driver_name(self):
        return _compact_spaces(self.cleaned_data.get("driver_name"))

    def clean_lr_no(self):
        return (self.cleaned_data.get("lr_no") or "").strip()

    def clean_transport_name(self):
        return _compact_spaces(self.cleaned_data.get("transport_name"))

    def clean_vehicle_no(self):
        return (self.cleaned_data.get("vehicle_no") or "").strip().upper()

    def clean_gate_pass_no(self):
        return (self.cleaned_data.get("gate_pass_no") or "").strip().upper()

    def clean(self):
        cleaned = super().clean()

        challan_date = cleaned.get("challan_date")
        expected_return_date = cleaned.get("expected_return_date")

        if expected_return_date and challan_date and expected_return_date < challan_date:
            self.add_error("expected_return_date", "Expected return date cannot be before challan date.")

        if self.program is not None:
            start_record = getattr(self.program, "start_record", None)
            if not start_record or not start_record.is_started:
                raise forms.ValidationError("Program must be started before creating a challan.")

        if self.start_jobber is not None:
            if self.program is not None and self.start_jobber.start_record.program_id != self.program.id:
                raise forms.ValidationError("Selected jobber row does not belong to this program.")

        if self.instance.pk and self.instance.status in {"approved", "closed"}:
            raise forms.ValidationError("Approved or closed challan cannot be edited.")

        return cleaned

class ProgramJobberChallanSizeForm(forms.ModelForm):
    class Meta:
        model = ProgramJobberChallanSize
        fields = ["size_name", "issued_qty", "inward_qty", "sort_order"]
        widgets = {
            "size_name": forms.TextInput(attrs={"readonly": "readonly"}),
            "issued_qty": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "inward_qty": forms.NumberInput(attrs={"step": "0.01", "min": "0", "readonly": "readonly"}),
            "sort_order": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} jf-input".strip()

        self.fields["size_name"].required = True
        self.fields["issued_qty"].required = False
        self.fields["inward_qty"].required = False

    def clean_size_name(self):
        value = (self.cleaned_data.get("size_name") or "").strip()
        if not value:
            raise forms.ValidationError("Size name is required.")
        return value

    def clean_issued_qty(self):
        value = self.cleaned_data.get("issued_qty") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Issued quantity cannot be negative.")
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def clean_inward_qty(self):
        value = self.cleaned_data.get("inward_qty") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Inward quantity cannot be negative.")
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


ProgramJobberChallanSizeFormSet = inlineformset_factory(
    ProgramJobberChallan,
    ProgramJobberChallanSize,
    form=ProgramJobberChallanSizeForm,
    extra=0,
    can_delete=False,
)


class ProgramJobberChallanApprovalForm(forms.ModelForm):
    approve = forms.ChoiceField(
        choices=(
            ("approved", "Approve"),
            ("rejected", "Reject"),
        ),
        widget=forms.RadioSelect,
        initial="approved",
    )

    class Meta:
        model = ProgramJobberChallan
        fields = ["approve", "rejection_reason"]
        widgets = {
            "rejection_reason": forms.Textarea(attrs={"rows": 3, "placeholder": "Reason for rejection"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} jf-input".strip()

        self.fields["rejection_reason"].required = False

        if not self.is_bound:
            self.fields["approve"].initial = "approved"

    def clean(self):
        cleaned = super().clean()
        approve = cleaned.get("approve")
        rejection_reason = _compact_spaces(cleaned.get("rejection_reason"))

        if approve == "rejected" and not rejection_reason:
            self.add_error("rejection_reason", "Rejection reason is required when rejecting challan.")

        cleaned["rejection_reason"] = rejection_reason
        return cleaned


def validate_program_jobber_challan_size_formset(formset):
    total_issued = Decimal("0")
    has_row = False

    for form in formset.forms:
        if not hasattr(form, "cleaned_data"):
            continue

        cleaned = form.cleaned_data
        if not cleaned:
            continue

        size_name = (cleaned.get("size_name") or "").strip()
        issued_qty = cleaned.get("issued_qty") or Decimal("0")

        if size_name:
            has_row = True

        if issued_qty < 0:
            raise forms.ValidationError("Issued quantity cannot be negative.")

        total_issued += issued_qty

    if not has_row:
        raise forms.ValidationError("At least one size row is required.")

    if total_issued <= 0:
        raise forms.ValidationError("At least one size row must have issued quantity greater than zero.")

    return total_issued.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

class ProgramInvoiceForm(forms.ModelForm):
    items_json = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = ProgramInvoice
        fields = [
            "invoice_no", "invoice_date", "firm", "client", "program", "vehicle_no", "remarks",
            "discount_percent", "other_charges", "gst_percent", "igst_percent",
        ]
        widgets = {
            "invoice_date": forms.DateInput(attrs={"type": "date"}),
            "invoice_no": forms.TextInput(attrs={"placeholder": "Auto / invoice number"}),
            "vehicle_no": forms.TextInput(attrs={"placeholder": "Vehicle number"}),
            "remarks": forms.Textarea(attrs={"rows": 3, "placeholder": "Remarks"}),
            "discount_percent": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "other_charges": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "gst_percent": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "igst_percent": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["program"].queryset = Program.objects.filter(owner=user).select_related("bom", "firm").order_by("-id") if user else Program.objects.none()
        self.fields["client"].queryset = Client.objects.filter(owner=user, is_active=True).order_by("name") if user else Client.objects.none()
        self.fields["firm"].queryset = Firm.objects.filter(owner=user).order_by("firm_name") if user else Firm.objects.none()
        self.fields["program"].empty_label = "Select program"
        self.fields["client"].empty_label = "Select client"
        self.fields["firm"].empty_label = "Select firm"
        if not self.is_bound:
            self.fields["invoice_date"].initial = timezone.localdate()

    def clean_items_json(self):
        return (self.cleaned_data.get("items_json") or "").strip()


class MaintenanceRecordForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRecord
        fields = ["month_key", "inward_total", "remarks"]
        widgets = {
            "month_key": forms.TextInput(attrs={"type": "month"}),
            "inward_total": forms.NumberInput(attrs={"step": "0.01", "min": "0", "readonly": "readonly"}),
            "remarks": forms.Textarea(attrs={"rows": 3, "placeholder": "Notes"}),
        }

    def clean_month_key(self):
        value = (self.cleaned_data.get("month_key") or "").strip()
        if not re.match(r"^\d{4}-\d{2}$", value):
            raise forms.ValidationError("Month must be in YYYY-MM format.")
        return value
    
class MaintenanceExpenseItemForm(forms.ModelForm):
    class Meta:
        model = MaintenanceExpenseItem
        fields = ["expense", "price", "sort_order"]
        widgets = {
            "expense": forms.Select(),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "Enter price"}),
            "sort_order": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields["expense"].queryset = Expense.objects.filter(owner=user)

    def clean_price(self):
        value = self.cleaned_data.get("price") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
class BaseMaintenanceExpenseItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        has_any_row = False

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue

            expense = form.cleaned_data.get("expense")
            price = form.cleaned_data.get("price")

            if expense or price not in (None, "", Decimal("0"), 0):
                has_any_row = True

            if expense and price is None:
                form.add_error("price", "Enter price.")
            if price not in (None, "") and not expense:
                form.add_error("expense", "Select expense.")

        if not has_any_row:
            raise forms.ValidationError("Add at least one maintenance expense row.")
        
MaintenanceExpenseItemFormSet = inlineformset_factory(
    MaintenanceRecord,
    MaintenanceExpenseItem,
    form=MaintenanceExpenseItemForm,
    formset=BaseMaintenanceExpenseItemFormSet,
    extra=1,
    can_delete=True,
)

class ProgramJobberDetailForm(forms.ModelForm):
    class Meta:
        model = ProgramJobberDetail
        fields = ["jobber", "jobber_type", "price", "sort_order"]
        widgets = {
            "jobber": forms.Select(),
            "jobber_type": forms.Select(),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "sort_order": forms.HiddenInput(),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["jobber"].queryset = (
            Jobber.objects.filter(owner=user, is_active=True)
            .select_related("jobber_type")
            .order_by("name")
            if user else Jobber.objects.none()
        )
        self.fields["jobber_type"].queryset = (
            JobberType.objects.filter(owner=user).order_by("name")
            if user else JobberType.objects.none()
        )

        self.fields["jobber"].empty_label = "Select jobber"
        self.fields["jobber_type"].empty_label = "Select jobber type"

    def clean_price(self):
        value = self.cleaned_data.get("price") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Jobber price cannot be negative.")
        return value


ProgramJobberDetailFormSet = inlineformset_factory(
    Program,
    ProgramJobberDetail,
    form=ProgramJobberDetailForm,
    extra=1,
    can_delete=True,
)

# ============================================================
# PHASE 2 FORMS
# ============================================================
class ProgramStartForm(forms.ModelForm):
    class Meta:
        model = ProgramStart
        fields = ["is_started", "remarks"]
        widgets = {"remarks": forms.Textarea(attrs={"rows": 3, "placeholder": "Execution notes"})}
class ProgramStartFabricForm(forms.ModelForm):
    class Meta:
        model = ProgramStartFabric
        fields = ["material", "unit", "used", "avg", "length", "width", "count", "pp_count", "lot_no", "lot_count", "available_qty", "used_qty", "sort_order"]
        widgets = {"sort_order": forms.HiddenInput()}
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["material"].queryset = (
            Material.objects
            .filter(Q(owner=user) | Q(owner__isnull=True), is_active=True)
            .order_by("name")
            if user else Material.objects.none()
        )
        self.fields["unit"].queryset = MaterialUnit.objects.filter(owner=user).order_by("name") if user else MaterialUnit.objects.none()
        self.fields["material"].required = False
        self.fields["unit"].required = False
class ProgramStartSizeForm(forms.ModelForm):
    class Meta:
        model = ProgramStartSize
        fields = ["size_name", "qty", "sort_order"]
        widgets = {"sort_order": forms.HiddenInput()}
class ProgramStartJobberForm(forms.ModelForm):
    class Meta:
        model = ProgramStartJobber
        fields = [
            "jobber",
            "jobber_type",
            "jobber_price",
            "allocation_date",
            "sort_order",
        ]
        widgets = {
            "allocation_date": forms.DateInput(attrs={"type": "date"}),
            "sort_order": forms.HiddenInput(),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
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
        self.fields["allocation_date"].required = False

    def clean_jobber_price(self):
        value = self.cleaned_data.get("jobber_price") or Decimal("0")
        if value < 0:
            raise forms.ValidationError("Jobber price cannot be negative.")
        return value

    def clean(self):
        cleaned = super().clean()
        jobber = cleaned.get("jobber")
        jobber_type = cleaned.get("jobber_type")

        if jobber and self.user is not None and getattr(jobber, "owner_id", None) != self.user.id:
            self.add_error("jobber", "Selected jobber is not available for this user.")

        if jobber and not jobber_type and getattr(jobber, "jobber_type_id", None):
            try:
                jobber_type = jobber.jobber_type
                cleaned["jobber_type"] = jobber_type
                self.instance.jobber_type = jobber_type
            except Exception:
                jobber_type = None

        if jobber_type and self.user is not None and getattr(jobber_type, "owner_id", None) != self.user.id:
            self.add_error("jobber_type", "Selected jobber type is not available for this user.")

        if jobber and jobber_type and getattr(jobber, "jobber_type_id", None):
            if jobber.jobber_type_id != jobber_type.id:
                self.add_error("jobber_type", "Selected jobber does not belong to the selected jobber type.")

        return cleaned

class BaseProgramStartFabricFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        valid_rows = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            material = form.cleaned_data.get("material")
            unit = form.cleaned_data.get("unit")
            used = form.cleaned_data.get("used")
            avg = form.cleaned_data.get("avg")
            length = form.cleaned_data.get("length")
            width = form.cleaned_data.get("width")
            count = form.cleaned_data.get("count")
            pp_count = form.cleaned_data.get("pp_count")
            lot_no = form.cleaned_data.get("lot_no")
            lot_count = form.cleaned_data.get("lot_count")
            available_qty = form.cleaned_data.get("available_qty")
            used_qty = form.cleaned_data.get("used_qty")

            has_data = any([
                material,
                unit,
                used not in (None, "", 0),
                avg not in (None, "", 0),
                length not in (None, "", 0),
                width not in (None, "", 0),
                count not in (None, "", 0),
                pp_count not in (None, "", 0),
                lot_no,
                lot_count not in (None, "", 0),
                available_qty not in (None, "", 0),
                used_qty not in (None, "", 0),
            ])

            if has_data:
                valid_rows += 1

        if valid_rows == 0:
            raise ValidationError("At least one valid fabric row is required.")


class BaseProgramStartSizeFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        valid_rows = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            size_name = (form.cleaned_data.get("size_name") or "").strip()
            qty = form.cleaned_data.get("qty")

            has_data = bool(size_name or qty not in (None, "", 0))

            if has_data:
                valid_rows += 1

            if size_name and qty in (None, ""):
                form.add_error("qty", "Quantity is required.")

            if qty not in (None, "") and qty < 0:
                form.add_error("qty", "Quantity cannot be negative.")

        if valid_rows == 0:
            raise ValidationError("At least one valid size row is required.")


class BaseProgramStartJobberFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        valid_rows = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            jobber = form.cleaned_data.get("jobber")
            jobber_type = form.cleaned_data.get("jobber_type")
            jobber_price = form.cleaned_data.get("jobber_price")
            allocation_date = form.cleaned_data.get("allocation_date")

            has_data = any([
                jobber,
                jobber_type,
                jobber_price not in (None, "", 0),
                allocation_date,
            ])

            if has_data:
                valid_rows += 1

            if jobber and not jobber_type and getattr(jobber, "jobber_type_id", None):
                form.cleaned_data["jobber_type"] = jobber.jobber_type

            if jobber_price not in (None, "") and jobber_price < 0:
                form.add_error("jobber_price", "Jobber price cannot be negative.")

        if valid_rows == 0:
            raise ValidationError("At least one valid jobber row is required.")
    
ProgramStartFabricFormSet = inlineformset_factory(
    ProgramStart,
    ProgramStartFabric,
    form=ProgramStartFabricForm,
    formset=BaseProgramStartFabricFormSet,
    extra=0,
    can_delete=True,
)

ProgramStartSizeFormSet = inlineformset_factory(
    ProgramStart,
    ProgramStartSize,
    form=ProgramStartSizeForm,
    formset=BaseProgramStartSizeFormSet,
    extra=0,
    can_delete=True,
)

ProgramStartJobberFormSet = inlineformset_factory(
    ProgramStart,
    ProgramStartJobber,
    form=ProgramStartJobberForm,
    formset=BaseProgramStartJobberFormSet,
    extra=0,
    can_delete=True,
)

class InventoryLotForm(forms.ModelForm):
    class Meta:
        model = InventoryLot
        fields = ["stage", "material", "unit", "dye_lot_no", "batch_no", "shade_reference", "location_name", "received_qty", "accepted_qty", "rejected_qty", "hold_qty", "used_qty", "qc_status", "is_closed"]
class InventoryRollForm(forms.ModelForm):
    class Meta:
        model = InventoryRoll
        fields = ["roll_no", "length_qty", "width", "gsm", "weight_qty", "accepted_qty", "status"]
InventoryRollFormSet = inlineformset_factory(InventoryLot, InventoryRoll, form=InventoryRollForm, extra=1, can_delete=True)
class QRCodeRecordForm(forms.ModelForm):
    class Meta:
        model = QRCodeRecord
        fields = ["qr_code", "qr_type", "lot", "roll", "status", "payload_url", "notes"]
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["lot"].queryset = InventoryLot.objects.filter(owner=user).order_by("-id")
            self.fields["roll"].queryset = InventoryRoll.objects.filter(lot__owner=user).order_by("-id")
class QualityCheckForm(forms.ModelForm):
    class Meta:
        model = QualityCheck
        fields = ["qc_number", "stage", "lot", "roll", "dyeing_inward_item", "ready_inward_item", "inspection_date", "status", "result", "remarks"]
        widgets = {"inspection_date": forms.DateInput(attrs={"type": "date"}), "remarks": forms.Textarea(attrs={"rows": 3})}
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["qc_number"].required = False
        if not self.is_bound and not self.instance.pk:
            self.fields["qc_number"].initial = next_quality_check_number()
        if user:
            self.fields["lot"].queryset = InventoryLot.objects.filter(owner=user).order_by("-id")
            self.fields["roll"].queryset = InventoryRoll.objects.filter(lot__owner=user).order_by("-id")
            self.fields["dyeing_inward_item"].queryset = DyeingPOInwardItem.objects.filter(inward__owner=user).order_by("-id")
            self.fields["ready_inward_item"].queryset = ReadyPOInwardItem.objects.filter(inward__owner=user).order_by("-id")
class QualityCheckParameterForm(forms.ModelForm):
    class Meta:
        model = QualityCheckParameter
        fields = ["parameter_name", "expected_value", "actual_value", "tolerance", "is_pass", "remarks"]
class QualityCheckDefectForm(forms.ModelForm):
    class Meta:
        model = QualityCheckDefect
        fields = ["defect_name", "severity", "affected_qty", "remarks"]
QualityCheckParameterFormSet = inlineformset_factory(QualityCheck, QualityCheckParameter, form=QualityCheckParameterForm, extra=1, can_delete=True)
QualityCheckDefectFormSet = inlineformset_factory(QualityCheck, QualityCheckDefect, form=QualityCheckDefectForm, extra=1, can_delete=True)
class CostingSnapshotForm(forms.ModelForm):
    class Meta:
        model = CostingSnapshot
        fields = ["bom", "program", "material_cost", "accessory_cost", "process_cost", "expense_cost", "overhead_cost", "wastage_cost", "target_margin_percent", "target_selling_price", "mrp", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["bom"].queryset = BOM.objects.filter(owner=user).order_by("-id")
            self.fields["program"].queryset = Program.objects.filter(owner=user).order_by("-id")
