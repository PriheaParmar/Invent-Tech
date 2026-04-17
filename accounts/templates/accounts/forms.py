import re

from decimal import Decimal
from django.utils import timezone
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Q
from django.forms import inlineformset_factory

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
                "placeholder": "Enter type name",
            }),
        }


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
                attrs={"type": "date", "readonly": "readonly"},
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

        qs = Material.objects.filter(material_kind="greige").order_by("name")
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

    def clean_unit(self):
        value = (self.cleaned_data.get("unit") or "").strip()
        valid_units = {choice for choice, _label in self.fields["unit"].choices if choice}

        if value and value not in valid_units:
            raise forms.ValidationError("Select a valid unit.")

        return value


GreigePurchaseOrderItemFormSet = inlineformset_factory(
    GreigePurchaseOrder,
    GreigePurchaseOrderItem,
    form=GreigePurchaseOrderItemForm,
    fields=[
        "material", "unit", "quantity", "value", "dia", "gauge", "rolls",
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
    class Meta:
        model = DyeingPurchaseOrder
        fields = [
            "source_greige_po",
            "vendor",
            "firm",
            "po_number",
            "internal_po_number",
            "po_date",
            "expected_delivery_date",
            "cancel_date",
            "shipping_address",
            "address",
            "remarks",
            "terms_conditions",
            "description",
            "discount_percent",
            "others",
            "gst_percent",
            "tcs_percent",
        ]
        widgets = {
            "po_date": forms.DateInput(attrs={"type": "date"}),
            "expected_delivery_date": forms.DateInput(attrs={"type": "date"}),
            "cancel_date": forms.DateInput(attrs={"type": "date"}),
            "shipping_address": forms.Textarea(attrs={"rows": 2}),
            "address": forms.Textarea(attrs={"rows": 2}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
            "terms_conditions": forms.Textarea(attrs={"rows": 4}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, source_greige_po=None, lock_source=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["source_greige_po"].queryset = (
            GreigePurchaseOrder.objects.filter(owner=user).order_by("-id")
            if user else GreigePurchaseOrder.objects.none()
        )
        self.fields["vendor"].queryset = (
            Vendor.objects.filter(owner=user).order_by("name")
            if user else Vendor.objects.none()
        )
        self.fields["firm"].queryset = (
            Firm.objects.filter(owner=user).order_by("firm_name")
            if user else Firm.objects.none()
        )

        self.fields["source_greige_po"].required = source_greige_po is None
        self.fields["vendor"].required = True
        self.fields["firm"].required = False
        self.fields["po_number"].required = False
        self.fields["internal_po_number"].required = False
        self.fields["po_date"].required = True
        self.fields["expected_delivery_date"].required = False
        self.fields["cancel_date"].required = False
        self.fields["shipping_address"].required = False
        self.fields["address"].required = False
        self.fields["remarks"].required = False
        self.fields["terms_conditions"].required = False
        self.fields["description"].required = False
        self.fields["discount_percent"].required = False
        self.fields["others"].required = False
        self.fields["gst_percent"].required = False
        self.fields["tcs_percent"].required = False

        self.fields["source_greige_po"].empty_label = "Select Greige PO"
        self.fields["vendor"].empty_label = "Select Vendor"
        self.fields["firm"].empty_label = "Select Firm"

        if source_greige_po is not None:
            self.fields["source_greige_po"].initial = source_greige_po
            if lock_source:
                self.fields["source_greige_po"].queryset = GreigePurchaseOrder.objects.filter(pk=source_greige_po.pk)
                self.fields["source_greige_po"].disabled = True

            if not self.is_bound:
                if source_greige_po.vendor_id:
                    self.fields["vendor"].initial = source_greige_po.vendor_id
                if source_greige_po.source_yarn_po and source_greige_po.source_yarn_po.firm_id:
                    self.fields["firm"].initial = source_greige_po.source_yarn_po.firm_id

        if not self.is_bound:
            if not self.initial.get("po_date"):
                self.initial["po_date"] = timezone.localdate()
            self.initial.setdefault("discount_percent", Decimal("0"))
            self.initial.setdefault("others", Decimal("0"))
            self.initial.setdefault("gst_percent", Decimal("0"))
            self.initial.setdefault("tcs_percent", Decimal("0"))

    def clean(self):
        cleaned_data = super().clean()

        source_greige_po = cleaned_data.get("source_greige_po")
        vendor = cleaned_data.get("vendor")

        if source_greige_po and vendor and source_greige_po.vendor_id != vendor.id:
            self.add_error("vendor", "Vendor must match the selected Greige PO vendor.")

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

class DyeingPOInwardForm(forms.ModelForm):
    class Meta:
        model = DyeingPOInward
        fields = ["vendor", "inward_type", "inward_date", "notes"]
        widgets = {
            "inward_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional inward notes"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["vendor"].required = False
        self.fields["inward_type"].required = False

        self.fields["vendor"].queryset = (
            Vendor.objects.filter(owner=user, is_active=True).order_by("name")
            if user else Vendor.objects.none()
        )
        self.fields["inward_type"].queryset = (
            InwardType.objects.filter(owner=user).order_by("name")
            if user else InwardType.objects.none()
        )

        self.fields["vendor"].empty_label = "Select vendor"
        self.fields["inward_type"].empty_label = "Select inward type"

        if not self.is_bound:
            self.fields["inward_date"].initial = self.instance.inward_date or timezone.localdate()
            if getattr(self.instance, "po_id", None) and not self.instance.vendor_id:
                po_vendor_id = getattr(getattr(self.instance, "po", None), "vendor_id", None)
                if po_vendor_id:
                    self.fields["vendor"].initial = po_vendor_id


class DyeingPurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = DyeingPurchaseOrderItem
        fields = [
            "quantity",
            "source_input_qty",
            "expected_loss_percent",
            "expected_output_qty",
            "actual_output_qty",
            "balance_output_qty",
            "dyeing_master_detail",
            "finished_material",
            "unit",
            "total_qty",
            "remaining_qty",
            "value",
            "rolls",
            "dyeing_type",
            "dyeing_name",
            "rate",
            "dyeing_other_charge",
            "other_charge_amount",
            "job_work_charges",
            "description",
            "remark",
            "line_subtotal",
            "line_final_amount",
        ]
        widgets = {
            "quantity": forms.HiddenInput(),
            "source_input_qty": forms.HiddenInput(),
            "expected_loss_percent": forms.HiddenInput(),
            "expected_output_qty": forms.HiddenInput(),
            "actual_output_qty": forms.HiddenInput(),
            "balance_output_qty": forms.HiddenInput(),
            "description": forms.Textarea(attrs={"rows": 2}),
            "remark": forms.TextInput(attrs={"placeholder": "Enter remarks"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        optional_fields = [
            "quantity",
            "source_input_qty",
            "expected_loss_percent",
            "expected_output_qty",
            "actual_output_qty",
            "balance_output_qty",
            "dyeing_master_detail",
            "finished_material",
            "unit",
            "total_qty",
            "remaining_qty",
            "value",
            "rolls",
            "dyeing_type",
            "dyeing_name",
            "rate",
            "dyeing_other_charge",
            "other_charge_amount",
            "job_work_charges",
            "description",
            "remark",
            "line_subtotal",
            "line_final_amount",
        ]
        for field_name in optional_fields:
            self.fields[field_name].required = False

        self.fields["dyeing_master_detail"].queryset = (
            DyeingMaterialLinkDetail.objects
            .select_related("link__vendor", "link__material", "finished_material")
            .filter(link__owner=user, is_active=True)
            .order_by("link__vendor__name", "link__material__name", "sort_order", "id")
            if user else DyeingMaterialLinkDetail.objects.none()
        )

        self.fields["finished_material"].queryset = (
            Material.objects.filter(material_kind="finished").order_by("name")
        )

        self.fields["dyeing_other_charge"].queryset = (
            DyeingOtherCharge.objects.filter(owner=user).order_by("name")
            if user else DyeingOtherCharge.objects.none()
        )

        self.fields["dyeing_master_detail"].empty_label = "Select Dyeing Master"
        self.fields["finished_material"].empty_label = "Select Finished Material"
        self.fields["dyeing_other_charge"].empty_label = "Select Other Charge"

        current_unit = (self.initial.get("unit") or getattr(self.instance, "unit", "") or "").strip()
        if self.is_bound:
            bound_unit = (self.data.get(self.add_prefix("unit")) or "").strip()
            if bound_unit:
                current_unit = bound_unit

        unit_choices = _material_unit_choices(user, current_unit)
        self.fields["unit"] = forms.ChoiceField(required=False, choices=unit_choices)
        self.fields["unit"].widget = forms.Select(choices=unit_choices)

        self.fields["total_qty"].label = "Process Qty"
        self.fields["remaining_qty"].label = "Balance Qty"

    def clean_unit(self):
        value = (self.cleaned_data.get("unit") or "").strip()
        valid_units = {choice for choice, _label in self.fields["unit"].choices if choice}
        if value and value not in valid_units:
            raise forms.ValidationError("Select a valid unit.")
        return value

    def clean(self):
        cleaned_data = super().clean()

        master_detail = cleaned_data.get("dyeing_master_detail")

        if master_detail:
            if not cleaned_data.get("finished_material") and master_detail.finished_material_id:
                cleaned_data["finished_material"] = master_detail.finished_material

            if not cleaned_data.get("dyeing_type"):
                cleaned_data["dyeing_type"] = master_detail.dyeing_type or ""

            if not cleaned_data.get("dyeing_name"):
                cleaned_data["dyeing_name"] = master_detail.dyeing_name or ""

            if not cleaned_data.get("rate"):
                cleaned_data["rate"] = master_detail.price or Decimal("0")

            if not cleaned_data.get("expected_loss_percent"):
                cleaned_data["expected_loss_percent"] = master_detail.weight_loss or Decimal("0")

        process_qty = cleaned_data.get("source_input_qty") or cleaned_data.get("total_qty") or Decimal("0")
        expected_loss_percent = cleaned_data.get("expected_loss_percent") or Decimal("0")
        rate = cleaned_data.get("rate") or Decimal("0")
        other_charge_amount = cleaned_data.get("other_charge_amount") or Decimal("0")
        job_work_charges = cleaned_data.get("job_work_charges") or Decimal("0")

        numeric_fields = {
            "process_qty": process_qty,
            "expected_loss_percent": expected_loss_percent,
            "rate": rate,
            "other_charge_amount": other_charge_amount,
            "job_work_charges": job_work_charges,
        }
        for label, value in numeric_fields.items():
            if value < 0:
                raise forms.ValidationError(f"{label.replace('_', ' ').title()} cannot be negative.")

        if expected_loss_percent > Decimal("100"):
            raise forms.ValidationError("Expected loss percent cannot be greater than 100.")

        expected_output_qty = cleaned_data.get("expected_output_qty")
        if not expected_output_qty:
            expected_output_qty = process_qty - (process_qty * expected_loss_percent / Decimal("100"))
            if expected_output_qty < 0:
                expected_output_qty = Decimal("0")

        cleaned_data["source_input_qty"] = process_qty
        cleaned_data["total_qty"] = process_qty
        cleaned_data["quantity"] = process_qty
        cleaned_data["expected_output_qty"] = expected_output_qty

        current_balance = cleaned_data.get("balance_output_qty")
        if current_balance in (None, Decimal("0")):
            cleaned_data["balance_output_qty"] = expected_output_qty

        current_remaining = cleaned_data.get("remaining_qty")
        if current_remaining in (None, Decimal("0")):
            cleaned_data["remaining_qty"] = expected_output_qty

        line_subtotal = process_qty * rate
        line_final_amount = line_subtotal + other_charge_amount + job_work_charges

        cleaned_data["line_subtotal"] = line_subtotal
        cleaned_data["line_final_amount"] = line_final_amount

        return cleaned_data


DyeingPurchaseOrderItemFormSet = inlineformset_factory(
    DyeingPurchaseOrder,
    DyeingPurchaseOrderItem,
    form=DyeingPurchaseOrderItemForm,
    fields=[
        "quantity",
        "source_input_qty",
        "expected_loss_percent",
        "expected_output_qty",
        "actual_output_qty",
        "balance_output_qty",
        "dyeing_master_detail",
        "finished_material",
        "unit",
        "total_qty",
        "remaining_qty",
        "value",
        "rolls",
        "dyeing_type",
        "dyeing_name",
        "rate",
        "dyeing_other_charge",
        "other_charge_amount",
        "job_work_charges",
        "description",
        "remark",
        "line_subtotal",
        "line_final_amount",
    ],
    extra=1,
    can_delete=True,
)


# ============================================================
# READY PURCHASE ORDER
# ============================================================

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


# ============================================================
# DYEING MATERIAL LINK
# ============================================================

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

        material_qs = Material.objects.filter(
            material_kind="greige",
        ).select_related("material_type").order_by("name")

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

        if self.user is not None and vendor and vendor.owner_id != self.user.id:
            self.add_error("vendor", "Selected vendor is not available for this user.")

        if self.user is not None and material_type and material_type.owner_id != self.user.id:
            self.add_error("material_type", "Selected material type is not available for this user.")

        if material_type and material_type.material_kind != "greige":
            self.add_error("material_type", "Only greige material type is allowed in Dyeing Master.")

        if material and material.material_kind != "greige":
            self.add_error("material", "Only greige material is allowed in Dyeing Master.")
            
        if material and material_type and material.material_type_id != material_type.id:
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
                self.add_error("material", "This vendor-material dyeing link already exists.")

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["finished_material"].required = True
        self.fields["finished_material"].queryset = (
            Material.objects.filter(material_kind="finished")
            .select_related("material_type")
            .order_by("name")
        )
        self.fields["finished_material"].empty_label = "Select Finished Material"

    def clean_finished_material(self):
        value = self.cleaned_data.get("finished_material")
        if value is None:
            raise forms.ValidationError("Finished material is required.")
        if value.material_kind != "finished":
            raise forms.ValidationError("Only finished material is allowed.")
        return value

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
        if value is None:
            return value
        if value < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return value


DyeingMaterialLinkDetailFormSet = inlineformset_factory(
    DyeingMaterialLink,
    DyeingMaterialLinkDetail,
    form=DyeingMaterialLinkDetailForm,
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["material"].queryset = Material.objects.filter(
            material_kind__in=["yarn", "greige", "finished", "trim"]
        ).select_related("material_type").order_by("name")

        self.fields["unit"].queryset = MaterialUnit.objects.all().order_by("name")
        self.fields["material"].empty_label = "Select material"
        self.fields["unit"].empty_label = "Select unit"
        self.fields["unit"].required = False

    def clean_cost_per_unit(self):
        return self.cleaned_data.get("cost_per_unit") or Decimal("0")

    def clean_avg(self):
        return self.cleaned_data.get("avg") or Decimal("0")

    def clean(self):
        cleaned = super().clean()
        cost_per_unit = cleaned.get("cost_per_unit") or Decimal("0")
        avg = cleaned.get("avg") or Decimal("0")
        cleaned["cost"] = cost_per_unit * avg
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["accessory"].queryset = Accessory.objects.order_by("name")

        self.fields["unit"].queryset = MaterialUnit.objects.all().order_by("name")
        self.fields["accessory"].empty_label = "Select accessory"
        self.fields["unit"].empty_label = "Select unit"
        self.fields["unit"].required = False

    def clean_cost_per_unit(self):
        return self.cleaned_data.get("cost_per_unit") or Decimal("0")

    def clean_avg(self):
        return self.cleaned_data.get("avg") or Decimal("0")

    def clean(self):
        cleaned = super().clean()
        cost_per_unit = cleaned.get("cost_per_unit") or Decimal("0")
        avg = cleaned.get("avg") or Decimal("0")
        cleaned["cost"] = cost_per_unit * avg
        return cleaned


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
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "sort_order": forms.HiddenInput(),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["jobber"].queryset = (
            Jobber.objects.filter(owner=user, is_active=True).select_related("jobber_type").order_by("name")
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
    
BOMJobberTypeProcessFormSet = inlineformset_factory(
    BOM,
    BOMJobberTypeProcess,
    form=BOMJobberTypeProcessForm,
    extra=1,
    can_delete=True,
)

BOMJobberDetailFormSet = inlineformset_factory(
    BOM,
    BOMJobberDetail,
    form=BOMJobberDetailForm,
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
            "total_qty",
            "ratio",
            "firm",
            "damage",
            "bom",
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
            "firm": forms.Select(),
            "damage": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Enter damage",
                }
            ),
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

        if not self.instance.pk and user:
            self.initial.setdefault("program_no", Program.next_program_no(user))
            self.initial.setdefault("program_date", timezone.localdate())

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

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

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