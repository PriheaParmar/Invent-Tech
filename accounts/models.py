from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from django.conf import settings
from django.db import models

# ============================================================
# USER
MATERIAL_KIND_CHOICES = (
    ("yarn", "Yarn"),
    ("greige", "Greige"),
    ("finished", "Finished"),
    ("trim", "Trim"),
)
# ============================================================


class UserExtra(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    phone = models.CharField(max_length=20, blank=True, null=True)
    designation = models.CharField(max_length=80, blank=True, null=True)
    department = models.CharField(max_length=80, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username


class OwnedModel(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ============================================================
# JOBBERS
# ============================================================

class JobberType(OwnedModel):
    name = models.CharField(max_length=80)

    class Meta:
        unique_together = ("owner", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Jobber(OwnedModel):
    ROLE_CHOICES = [
        ("Supervisor", "Supervisor"),
        ("Line Incharge", "Line Incharge"),
        ("Operator", "Operator"),
        ("Helper", "Helper"),
        ("Account", "Account"),
        ("Other", "Other"),
    ]

    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default="Operator")
    jobber_type = models.ForeignKey(JobberType, on_delete=models.SET_NULL, null=True, blank=True)

    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("owner", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


# ============================================================
# MATERIAL
# ============================================================

class Material(models.Model):
    MATERIAL_KIND_CHOICES = [
        ("yarn", "Yarn"),
        ("greige", "Greige"),
        ("finished", "Finished"),
        ("trim", "Trim"),
    ]

    material_kind = models.CharField(
        max_length=16,
        choices=MATERIAL_KIND_CHOICES,
        default="yarn",
    )

    material_type = models.ForeignKey(
        "MaterialType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materials",
    )

    material_sub_type = models.ForeignKey(
        "MaterialSubType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materials",
    )

    material_shade = models.ForeignKey(
        "MaterialShade",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materials",
    )

    name = models.CharField(max_length=150)
    remarks = models.TextField(blank=True)
    image = models.ImageField(upload_to="materials/%Y/%m/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        mt = getattr(self.material_type, "name", "")
        return f"{mt} - {self.name}" if mt else self.name


class YarnDetail(models.Model):
    material = models.OneToOneField(Material, on_delete=models.CASCADE, related_name="yarn")
    yarn_type = models.CharField(max_length=80, blank=True)
    yarn_subtype = models.CharField(max_length=80, blank=True)
    count_denier = models.CharField(max_length=40, blank=True)
    color = models.CharField(max_length=60, blank=True)


class GreigeDetail(models.Model):
    material = models.OneToOneField(Material, on_delete=models.CASCADE, related_name="greige")
    fabric_type = models.CharField(max_length=120, blank=True)
    gsm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    construction = models.CharField(max_length=120, blank=True)


class FinishedDetail(models.Model):
    class FinishType(models.TextChoices):
        DYED = "dyed", "Dyed"
        PRINTED = "printed", "Printed"
        COATED = "coated", "Coated"
        WASHED = "washed", "Washed"
        OTHER = "other", "Other"

    material = models.OneToOneField(Material, on_delete=models.CASCADE, related_name="finished")

    base_fabric_type = models.CharField(max_length=120, blank=True)
    finish_type = models.CharField(max_length=20, choices=FinishType.choices, blank=True)
    gsm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    end_use = models.CharField(max_length=120, blank=True)


class TrimDetail(models.Model):
    TRIM_TYPE_CHOICES = [
        ("Button", "Button"),
        ("Zipper", "Zipper"),
        ("Label", "Label"),
        ("Elastic", "Elastic"),
        ("Thread", "Thread"),
        ("Hook", "Hook"),
        ("Other", "Other"),
    ]

    material = models.OneToOneField(Material, on_delete=models.CASCADE, related_name="trim")

    trim_type = models.CharField(max_length=80, choices=TRIM_TYPE_CHOICES, blank=True)
    size = models.CharField(max_length=60, blank=True)
    color = models.CharField(max_length=60, blank=True)
    brand = models.CharField(max_length=80, blank=True)


# ============================================================
# PARTY
# ============================================================

INDIA_STATE_CHOICES = [
    ("AN", "Andaman & Nicobar Islands"),
    ("AP", "Andhra Pradesh"),
    ("AR", "Arunachal Pradesh"),
    ("AS", "Assam"),
    ("BR", "Bihar"),
    ("CH", "Chandigarh"),
    ("CG", "Chhattisgarh"),
    ("DN", "Dadra & Nagar Haveli and Daman & Diu"),
    ("DL", "Delhi"),
    ("GA", "Goa"),
    ("GJ", "Gujarat"),
    ("HR", "Haryana"),
    ("HP", "Himachal Pradesh"),
    ("JK", "Jammu & Kashmir"),
    ("JH", "Jharkhand"),
    ("KA", "Karnataka"),
    ("KL", "Kerala"),
    ("LA", "Ladakh"),
    ("LD", "Lakshadweep"),
    ("MP", "Madhya Pradesh"),
    ("MH", "Maharashtra"),
    ("MN", "Manipur"),
    ("ML", "Meghalaya"),
    ("MZ", "Mizoram"),
    ("NL", "Nagaland"),
    ("OR", "Odisha"),
    ("PB", "Punjab"),
    ("PY", "Puducherry"),
    ("RJ", "Rajasthan"),
    ("SK", "Sikkim"),
    ("TN", "Tamil Nadu"),
    ("TS", "Telangana"),
    ("TR", "Tripura"),
    ("UP", "Uttar Pradesh"),
    ("UK", "Uttarakhand"),
    ("WB", "West Bengal"),
]


class Party(models.Model):
    party_name = models.CharField(max_length=150)
    full_name = models.CharField(max_length=200, blank=True)
    address = models.TextField(blank=True)

    pan_number = models.CharField(max_length=10, blank=True)
    gst_number = models.CharField(max_length=15, blank=True)
    tan_number = models.CharField(max_length=10, blank=True)

    state = models.CharField(max_length=2, choices=INDIA_STATE_CHOICES, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)

    bank_name = models.CharField(max_length=120, blank=True)
    account_number = models.CharField(max_length=30, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["party_name"]

    def __str__(self):
        return self.party_name

class Client(OwnedModel):
    name = models.CharField(max_length=180)
    contact_person = models.CharField(max_length=120, blank=True, default="")
    phone = models.CharField(max_length=10, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    gst_number = models.CharField(max_length=15, blank=True, default="")
    pan_number = models.CharField(max_length=10, blank=True, default="")
    city = models.CharField(max_length=80, blank=True, default="")
    state = models.CharField(max_length=2, choices=INDIA_STATE_CHOICES, blank=True, default="")
    address = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("owner", "name")]

    def __str__(self):
        return self.name
    
class Location(OwnedModel):
    name = models.CharField(max_length=120)
    address_line_1 = models.CharField(max_length=255, blank=True, default="")
    address_line_2 = models.CharField(max_length=255, blank=True, default="")
    landmark = models.CharField(max_length=150, blank=True, default="")
    city = models.CharField(max_length=80, blank=True, default="")
    state = models.CharField(max_length=80, blank=True, default="")
    pincode = models.CharField(max_length=6, blank=True, default="")

    class Meta:
        ordering = ["name"]
        unique_together = [("owner", "name")]

    def __str__(self):
        return self.name

class Brand(OwnedModel):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("owner", "name")]

    def __str__(self):
        return self.name
    
class Category(OwnedModel):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("owner", "name")]

    def __str__(self):
        return self.name

# ============================================================
# UTILITIES (SINGLE COPY ONLY ✅)
# ============================================================

class MaterialType(OwnedModel):
    material_kind = models.CharField(
        max_length=20,
        choices=MATERIAL_KIND_CHOICES,
        db_index=True,
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class MaterialShade(OwnedModel):
    material_kind = models.CharField(
        max_length=20,
        choices=MATERIAL_KIND_CHOICES,
        db_index=True,
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class MaterialSubType(OwnedModel):
    material_kind = models.CharField(
        max_length=20,
        choices=MATERIAL_KIND_CHOICES,
        db_index=True,
        null=True,
        blank=True,
    )
    material_type = models.ForeignKey(
        MaterialType,
        on_delete=models.CASCADE,
        related_name="sub_types",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("owner", "material_type", "name")]

    def __str__(self):
        return self.name


# ============================================================
# FIRM
# ============================================================

class Firm(models.Model):
    FIRM_TYPES = [
        ("proprietorship", "Proprietorship"),
        ("partnership", "Partnership"),
        ("llp", "LLP"),
        ("pvt_ltd", "Pvt Ltd"),
    ]

    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="firm")

    firm_name = models.CharField(max_length=180)
    class FirmType(models.TextChoices):
        LAW_FIRM = "law_firm", "Law Firm"
        COMPANY = "company", "Company"
        INDIVIDUAL = "individual", "Individual"
        STARTUP = "startup", "Startup"
        OTHER = "other", "Other"

    firm_type = models.CharField(max_length=20, choices=FirmType.choices, default=FirmType.COMPANY)
    address_line = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=12, blank=True)

    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    gst_number = models.CharField(max_length=20, blank=True)
    pan_number = models.CharField(max_length=20, blank=True)
    tan_number = models.CharField(max_length=20, blank=True)
    cin_number = models.CharField(max_length=30, blank=True)

    bank_name = models.CharField(max_length=120, blank=True)
    account_holder_name = models.CharField(max_length=120, blank=True)
    account_number = models.CharField(max_length=40, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)
    branch_name = models.CharField(max_length=120, blank=True)

    logo = models.ImageField(upload_to="firm_logos/", blank=True, null=True)

    def __str__(self):
        return self.firm_name

    @property
    def full_address(self):
        parts = [self.address_line, self.city, self.state, self.pincode]
        return ", ".join([p for p in parts if p])



# ============================================================
# VENDOR
# ============================================================

class Vendor(OwnedModel):
    name = models.CharField(max_length=180)
    contact_person = models.CharField(max_length=120, blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    gst_number = models.CharField(max_length=15, blank=True, default="")
    address = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("owner", "name")]

    def __str__(self):
        return self.name


# ============================================================
# YARN PURCHASE ORDER
# ============================================================

class YarnPurchaseOrder(OwnedModel):
    system_number = models.CharField(max_length=30, unique=True, blank=True)
    po_number = models.CharField(max_length=30, blank=True, default="")
    po_date = models.DateField()
    cancel_date = models.DateField(null=True, blank=True)

    vendor = models.ForeignKey(
        "Vendor",
        on_delete=models.PROTECT,
        related_name="yarn_purchase_orders",
    )
    firm = models.ForeignKey(
        "Firm",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="yarn_purchase_orders",
    )

    shipping_address = models.TextField(blank=True, default="")
    remarks = models.TextField(blank=True, default="")
    terms_conditions = models.TextField(blank=True, default="")

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    after_discount_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    others = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cgst_percent = models.DecimalField(max_digits=6, decimal_places=2, default=2.5)
    sgst_percent = models.DecimalField(max_digits=6, decimal_places=2, default=2.5)
    total_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    rejection_reason = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_yarn_purchase_orders",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    @property
    def total_inward_qty(self):
        total = (
            self.inwards.aggregate(total=Sum("items__quantity")).get("total")
            or Decimal("0")
        )
        return total

    @property
    def remaining_qty_total(self):
        ordered = self.total_weight or Decimal("0")
        inward = self.total_inward_qty or Decimal("0")
        return ordered - inward if ordered > inward else Decimal("0")

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.system_number or f"Yarn PO {self.pk or 'Draft'}"


class YarnPurchaseOrderItem(models.Model):
    po = models.ForeignKey("YarnPurchaseOrder", on_delete=models.CASCADE, related_name="items")

    material_type = models.ForeignKey(
        "MaterialType",
        on_delete=models.PROTECT,
        related_name="yarn_po_items",
        null=True,
        blank=True,
        limit_choices_to={"material_kind": "yarn"},
    )

    material = models.ForeignKey(
        "Material",
        on_delete=models.PROTECT,
        related_name="yarn_po_items",
        null=True,
        blank=True,
    )

    unit = models.CharField(max_length=20, blank=True, default="")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    dia = models.CharField(max_length=30, blank=True, default="")
    gauge = models.CharField(max_length=30, blank=True, default="")
    rolls = models.CharField(max_length=30, blank=True, default="")
    count = models.CharField(max_length=30, blank=True, default="")
    gsm = models.CharField(max_length=30, blank=True, default="")
    sl = models.CharField(max_length=30, blank=True, default="")
    hsn_code = models.CharField(max_length=30, blank=True, default="")
    remark = models.CharField(max_length=255, blank=True, default="")
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    @property
    def inward_qty_total(self):
        total = self.inward_items.aggregate(total=Sum("quantity")).get("total") or Decimal("0")
        return total

    @property
    def remaining_qty_total(self):
        ordered = self.quantity or Decimal("0")
        inward = self.inward_qty_total or Decimal("0")
        return ordered - inward if ordered > inward else Decimal("0")
    class Meta:
        ordering = ["id"]

    def __str__(self):
        label = None
        if self.material_type:
            label = self.material_type.name
        elif self.material:
            label = str(self.material)
        else:
            label = "Yarn Item"
        return f"{self.po} - {label}"
    
class YarnPOInward(OwnedModel):
    po = models.ForeignKey(
        "YarnPurchaseOrder",
        on_delete=models.CASCADE,
        related_name="inwards",
    )
    vendor = models.ForeignKey(
        "Vendor",
        on_delete=models.SET_NULL,
        related_name="yarn_inwards",
        null=True,
        blank=True,
    )
    inward_type = models.ForeignKey(
        "InwardType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="yarn_inwards",
    )
    inward_number = models.CharField(max_length=30, unique=True)
    inward_date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True, default="")


class YarnPOInwardItem(models.Model):
    inward = models.ForeignKey(
        YarnPOInward,
        on_delete=models.CASCADE,
        related_name="items",
    )
    po_item = models.ForeignKey(
        "YarnPurchaseOrderItem",
        on_delete=models.CASCADE,
        related_name="inward_items",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remark = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = ("inward", "po_item")

    def __str__(self):
        return f"{self.inward.inward_number} / {self.po_item_id}"
    
class GreigePurchaseOrder(OwnedModel):
    system_number = models.CharField(max_length=30, unique=True, blank=True)
    po_number = models.CharField(max_length=30, blank=True, default="")
    po_date = models.DateField(default=timezone.localdate)
    internal_po_number = models.CharField(max_length=30, blank=True, default="")
    available_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    shipping_address = models.CharField(max_length=255, blank=True, default="")
    delivery_period = models.CharField(max_length=100, blank=True, default="")
    expected_delivery_date = models.DateField(null=True, blank=True)
    cancel_date = models.DateField(null=True, blank=True)

    director = models.CharField(max_length=120, blank=True, default="")
    validity_period = models.CharField(max_length=100, blank=True, default="")
    address = models.TextField(blank=True, default="")
    delivery_schedule = models.CharField(max_length=150, blank=True, default="")

    source_yarn_po = models.ForeignKey(
        "YarnPurchaseOrder",
        on_delete=models.CASCADE,
        related_name="greige_pos",
    )

    source_yarn_inward = models.ForeignKey(
        "YarnPOInward",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_greige_pos",
    )

    vendor = models.ForeignKey(
        "Vendor",
        on_delete=models.PROTECT,
        related_name="greige_purchase_orders",
    )


class GreigePurchaseOrderItem(models.Model):
    po = models.ForeignKey(
        "GreigePurchaseOrder",
        on_delete=models.CASCADE,
        related_name="items",
    )

    source_yarn_po_item = models.ForeignKey(
        "YarnPurchaseOrderItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_greige_items",
    )

    fabric_name = models.CharField(max_length=150)
    yarn_name = models.CharField(max_length=150, blank=True, default="")
    unit = models.CharField(max_length=20, blank=True, default="")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remark = models.CharField(max_length=255, blank=True, default="")

    @property
    def inward_qty_total(self):
        total = self.inward_items.aggregate(total=Sum("quantity")).get("total") or Decimal("0")
        return total

    @property
    def remaining_qty_total(self):
        ordered = self.quantity or Decimal("0")
        inward = self.inward_qty_total or Decimal("0")
        return ordered - inward if ordered > inward else Decimal("0")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.po} - {self.fabric_name}"


class GreigePOInward(OwnedModel):
    po = models.ForeignKey(
        "GreigePurchaseOrder",
        on_delete=models.CASCADE,
        related_name="inwards",
    )
    inward_number = models.CharField(max_length=30, unique=True)
    inward_date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-inward_date", "-id"]

    def __str__(self):
        return self.inward_number


class GreigePOInwardItem(models.Model):
    inward = models.ForeignKey(
        "GreigePOInward",
        on_delete=models.CASCADE,
        related_name="items",
    )
    po_item = models.ForeignKey(
        "GreigePurchaseOrderItem",
        on_delete=models.CASCADE,
        related_name="inward_items",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remark = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = ("inward", "po_item")

    def __str__(self):
        return f"{self.inward.inward_number} / {self.po_item_id}"


class DyeingPurchaseOrder(OwnedModel):
    system_number = models.CharField(max_length=30, unique=True, blank=True)
    po_number = models.CharField(max_length=30, blank=True, default="")
    po_date = models.DateField(default=timezone.localdate)
    internal_po_number = models.CharField(max_length=30, blank=True, default="")
    available_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    shipping_address = models.CharField(max_length=255, blank=True, default="")
    delivery_period = models.CharField(max_length=100, blank=True, default="")
    expected_delivery_date = models.DateField(null=True, blank=True)
    cancel_date = models.DateField(null=True, blank=True)

    director = models.CharField(max_length=120, blank=True, default="")
    validity_period = models.CharField(max_length=100, blank=True, default="")
    address = models.TextField(blank=True, default="")
    delivery_schedule = models.CharField(max_length=150, blank=True, default="")

    source_greige_po = models.ForeignKey(
        "GreigePurchaseOrder",
        on_delete=models.CASCADE,
        related_name="dyeing_pos",
    )

    vendor = models.ForeignKey(
        "Vendor",
        on_delete=models.PROTECT,
        related_name="dyeing_purchase_orders",
    )

    firm = models.ForeignKey(
        "Firm",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dyeing_purchase_orders",
    )

    remarks = models.TextField(blank=True, default="")
    total_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    @property
    def total_inward_qty(self):
        total = self.inwards.aggregate(total=Sum("items__quantity")).get("total") or Decimal("0")
        return total

    @property
    def remaining_qty_total(self):
        ordered = self.total_weight or Decimal("0")
        inward = self.total_inward_qty or Decimal("0")
        return ordered - inward if ordered > inward else Decimal("0")

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.system_number or f"Dyeing PO {self.pk or 'Draft'}"


class DyeingPurchaseOrderItem(models.Model):
    po = models.ForeignKey(
        "DyeingPurchaseOrder",
        on_delete=models.CASCADE,
        related_name="items",
    )

    source_greige_po_item = models.ForeignKey(
        "GreigePurchaseOrderItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_dyeing_items",
    )

    fabric_name = models.CharField(max_length=150)
    greige_name = models.CharField(max_length=150, blank=True, default="")
    unit = models.CharField(max_length=20, blank=True, default="")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remark = models.CharField(max_length=255, blank=True, default="")

    @property
    def inward_qty_total(self):
        total = self.inward_items.aggregate(total=Sum("quantity")).get("total") or Decimal("0")
        return total

    @property
    def remaining_qty_total(self):
        ordered = self.quantity or Decimal("0")
        inward = self.inward_qty_total or Decimal("0")
        return ordered - inward if ordered > inward else Decimal("0")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.po} - {self.fabric_name}"


class DyeingPOInward(OwnedModel):
    po = models.ForeignKey(
        "DyeingPurchaseOrder",
        on_delete=models.CASCADE,
        related_name="inwards",
    )
    inward_number = models.CharField(max_length=30, unique=True)
    inward_date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-inward_date", "-id"]

    def __str__(self):
        return self.inward_number


class DyeingPOInwardItem(models.Model):
    inward = models.ForeignKey(
        DyeingPOInward,
        on_delete=models.CASCADE,
        related_name="items",
    )
    po_item = models.ForeignKey(
        "DyeingPurchaseOrderItem",
        on_delete=models.CASCADE,
        related_name="inward_items",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remark = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = ("inward", "po_item")

    def __str__(self):
        return f"{self.inward.inward_number} / {self.po_item_id}"
    
class ReadyPurchaseOrder(OwnedModel):
    system_number = models.CharField(max_length=30, unique=True, blank=True)
    po_number = models.CharField(max_length=30, blank=True, default="")
    po_date = models.DateField(default=timezone.localdate)
    internal_po_number = models.CharField(max_length=30, blank=True, default="")
    available_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    shipping_address = models.CharField(max_length=255, blank=True, default="")
    delivery_period = models.CharField(max_length=100, blank=True, default="")
    expected_delivery_date = models.DateField(null=True, blank=True)
    cancel_date = models.DateField(null=True, blank=True)

    director = models.CharField(max_length=120, blank=True, default="")
    validity_period = models.CharField(max_length=100, blank=True, default="")
    address = models.TextField(blank=True, default="")
    delivery_schedule = models.CharField(max_length=150, blank=True, default="")

    source_dyeing_po = models.ForeignKey(
        "DyeingPurchaseOrder",
        on_delete=models.CASCADE,
        related_name="ready_pos",
    )

    vendor = models.ForeignKey(
        "Vendor",
        on_delete=models.PROTECT,
        related_name="ready_purchase_orders",
    )

    firm = models.ForeignKey(
        "Firm",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ready_purchase_orders",
    )

    remarks = models.TextField(blank=True, default="")
    total_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    @property
    def total_inward_qty(self):
        total = self.inwards.aggregate(total=Sum("items__quantity")).get("total") or Decimal("0")
        return total

    @property
    def remaining_qty_total(self):
        ordered = self.total_weight or Decimal("0")
        inward = self.total_inward_qty or Decimal("0")
        return ordered - inward if ordered > inward else Decimal("0")

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.system_number or f"Ready PO {self.pk or 'Draft'}"
    
class ReadyPurchaseOrderItem(models.Model):
    po = models.ForeignKey(
        "ReadyPurchaseOrder",
        on_delete=models.CASCADE,
        related_name="items",
    )

    source_dyeing_po_item = models.ForeignKey(
        "DyeingPurchaseOrderItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_ready_items",
    )

    fabric_name = models.CharField(max_length=150)
    dyeing_name = models.CharField(max_length=150, blank=True, default="")
    unit = models.CharField(max_length=20, blank=True, default="")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remark = models.CharField(max_length=255, blank=True, default="")

    @property
    def inward_qty_total(self):
        total = self.inward_items.aggregate(total=Sum("quantity")).get("total") or Decimal("0")
        return total

    @property
    def remaining_qty_total(self):
        ordered = self.quantity or Decimal("0")
        inward = self.inward_qty_total or Decimal("0")
        return ordered - inward if ordered > inward else Decimal("0")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.po} - {self.fabric_name}"
    
class ReadyPOInward(OwnedModel):
    po = models.ForeignKey(
        "ReadyPurchaseOrder",
        on_delete=models.CASCADE,
        related_name="inwards",
    )
    inward_number = models.CharField(max_length=30, unique=True)
    inward_date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-inward_date", "-id"]

    def __str__(self):
        return self.inward_number
    
class ReadyPOInwardItem(models.Model):
    inward = models.ForeignKey(
        ReadyPOInward,
        on_delete=models.CASCADE,
        related_name="items",
    )
    po_item = models.ForeignKey(
        "ReadyPurchaseOrderItem",
        on_delete=models.CASCADE,
        related_name="inward_items",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remark = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = ("inward", "po_item")

    def __str__(self):
        return f"{self.inward.inward_number} / {self.po_item_id}"
    
    


class MaterialUnit(OwnedModel):
    name = models.CharField(max_length=20)

    class Meta:
        ordering = ["name"]
        unique_together = [("owner", "name")]

    def __str__(self):
        return self.name


class InwardType(OwnedModel):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("owner", "name")]

    def __str__(self):
        return self.name

class MainCategory(OwnedModel):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("owner", "name")]

    def __str__(self):
        return self.name


class PatternType(OwnedModel):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("owner", "name")]

    def __str__(self):
        return self.name
    
class Catalogue(OwnedModel):
    name = models.CharField(max_length=140)
    wear_type = models.CharField(max_length=80, blank=True, default="")
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("owner", "name")]

    def __str__(self):
        return self.name
    
class BOM(OwnedModel):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        UNISEX = "unisex", "Unisex"
        KIDS = "kids", "Kids"

    class SizeType(models.TextChoices):
        CHARACTER = "character", "Character"
        NUMERIC = "numeric", "Numeric"
        ALPHA = "alpha", "Alpha"
        FREE = "free", "Free Size"

    bom_code = models.CharField(max_length=30, blank=True)
    sku_code = models.CharField(max_length=100)
    product_name = models.CharField(max_length=150, blank=True, default="")
    catalogue_name = models.CharField(max_length=120, blank=True, default="")

    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name="boms",
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="boms",
        null=True,
        blank=True,
    )
    main_category = models.ForeignKey(
        MainCategory,
        on_delete=models.PROTECT,
        related_name="boms",
        null=True,
        blank=True,
    )
    pattern_type = models.ForeignKey(
        PatternType,
        on_delete=models.PROTECT,
        related_name="boms",
        null=True,
        blank=True,
    )

    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        default=Gender.UNISEX,
        blank=True,
    )
    size_type = models.CharField(
        max_length=20,
        choices=SizeType.choices,
        default=SizeType.CHARACTER,
    )
    sub_category = models.CharField(max_length=120, blank=True, default="")
    character_name = models.CharField(max_length=120, blank=True, default="")
    license_name = models.CharField(max_length=120, blank=True, default="")

    color_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    accessories_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    maintenance_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    booked_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    available_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    damage_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    is_discontinued = models.BooleanField(default=False)
    product_image = models.ImageField(upload_to="bom/%Y/%m/", blank=True, null=True)
    size_chart_image = models.ImageField(upload_to="bom/%Y/%m/", blank=True, null=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-id"]
        unique_together = [("owner", "bom_code"), ("owner", "sku_code")]

    def save(self, *args, **kwargs):
        if not self.bom_code and self.owner_id:
            next_number = (BOM.objects.filter(owner=self.owner).count() or 0) + 1
            self.bom_code = f"BOM-{next_number:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.bom_code or self.sku_code

    @property
    def material_cost_total(self):
        return self.material_items.aggregate(total=Sum("cost")).get("total") or Decimal("0")

    @property
    def jobber_cost_total(self):
        return self.jobber_items.aggregate(total=Sum("price")).get("total") or Decimal("0")

    @property
    def process_cost_total(self):
        return self.process_items.aggregate(total=Sum("price")).get("total") or Decimal("0")

    @property
    def expense_cost_total(self):
        return self.expense_items.aggregate(total=Sum("price")).get("total") or Decimal("0")

    @property
    def overhead_total(self):
        return (
            (self.color_price or Decimal("0"))
            + (self.accessories_price or Decimal("0"))
            + (self.maintenance_price or Decimal("0"))
        )

    @property
    def subtotal_cost(self):
        return (
            self.material_cost_total
            + self.jobber_cost_total
            + self.process_cost_total
            + self.expense_cost_total
            + self.overhead_total
        )

    @property
    def damage_value(self):
        subtotal = self.subtotal_cost or Decimal("0")
        percent = self.damage_percent or Decimal("0")
        return (subtotal * percent) / Decimal("100")

    @property
    def estimated_total_cost(self):
        return self.subtotal_cost + self.damage_value

    @property
    def linked_fabrics(self):
        return self.material_items.filter(item_type=BOMMaterialItem.ItemType.RAW_FABRIC)

    @property
    def linked_accessories(self):
        return self.material_items.filter(
            item_type__in=[
                BOMMaterialItem.ItemType.ACCESSORY,
                BOMMaterialItem.ItemType.TRIM,
                BOMMaterialItem.ItemType.PACKING,
            ]
        )

    @property
    def linked_fabric_names(self):
        return ", ".join(
            [item.material.name for item in self.linked_fabrics if item.material]
        )

    @property
    def linked_accessory_names(self):
        return ", ".join(
            [item.material.name for item in self.linked_accessories if item.material]
        )

    @property
    def display_sku_name(self):
        return self.sku_code or self.product_name or self.bom_code

    @property
    def display_brand_name(self):
        return self.brand.name if self.brand else ""

    @property
    def display_main_category_name(self):
        return self.main_category.name if self.main_category else ""

    @property
    def display_category_name(self):
        return self.category.name if self.category else ""

    @property
    def display_pattern_type_name(self):
        return self.pattern_type.name if self.pattern_type else ""


class BOMMaterialItem(models.Model):
    class ItemType(models.TextChoices):
        RAW_FABRIC = "raw_fabric", "Raw Fabric"
        ACCESSORY = "accessory", "Accessory"
        TRIM = "trim", "Trim"
        PACKING = "packing", "Packing"
        OTHER = "other", "Other"

    bom = models.ForeignKey(BOM, on_delete=models.CASCADE, related_name="material_items")
    item_type = models.CharField(max_length=20, choices=ItemType.choices, default=ItemType.RAW_FABRIC)
    material = models.ForeignKey(Material, on_delete=models.PROTECT, related_name="bom_material_items")
    unit = models.ForeignKey(
        MaterialUnit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bom_material_items",
    )
    cost_per_uom = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    average = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.CharField(max_length=255, blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def save(self, *args, **kwargs):
        self.cost = (self.cost_per_uom or Decimal("0")) * (self.average or Decimal("0"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bom} - {self.material}"


class BOMJobberItem(models.Model):
    bom = models.ForeignKey(BOM, on_delete=models.CASCADE, related_name="jobber_items")
    jobber = models.ForeignKey(
        Jobber,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bom_jobber_items",
    )
    jobber_type = models.ForeignKey(
        JobberType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bom_jobber_items",
    )
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def save(self, *args, **kwargs):
        if self.jobber and not self.jobber_type:
            self.jobber_type = self.jobber.jobber_type
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bom} - {self.jobber or self.jobber_type or 'Jobber'}"


class BOMProcessItem(models.Model):
    bom = models.ForeignKey(BOM, on_delete=models.CASCADE, related_name="process_items")
    jobber_type = models.ForeignKey(
        JobberType,
        on_delete=models.PROTECT,
        related_name="bom_process_items",
    )
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.bom} - {self.jobber_type}"


class BOMExpenseItem(models.Model):
    bom = models.ForeignKey(BOM, on_delete=models.CASCADE, related_name="expense_items")
    expense_name = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.bom} - {self.expense_name}"


class Program(OwnedModel):
    program_no = models.CharField(max_length=30)
    program_date = models.DateField(default=timezone.localdate)

    bom = models.ForeignKey(
        "BOM",
        on_delete=models.PROTECT,
        related_name="programs",
    )

    firm = models.ForeignKey(
        "Firm",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="programs",
    )

    total_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ratio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    damage = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        ordering = ["-program_date", "-id"]
        unique_together = [("owner", "program_no")]

    def __str__(self):
        return self.program_no

    @property
    def sku_name(self):
        return self.bom.display_sku_name if self.bom_id else ""

    @property
    def linked_fabric_names(self):
        return self.bom.linked_fabric_names if self.bom_id else ""

    @property
    def linked_accessory_names(self):
        return self.bom.linked_accessory_names if self.bom_id else ""

    @property
    def brand_name(self):
        return self.bom.display_brand_name if self.bom_id else ""

    @property
    def gender(self):
        return self.bom.get_gender_display() if self.bom_id else ""

    @property
    def main_category_name(self):
        return self.bom.display_main_category_name if self.bom_id else ""

    @property
    def category_name(self):
        return self.bom.display_category_name if self.bom_id else ""

    @property
    def sub_category_name(self):
        return self.bom.sub_category if self.bom_id else ""

    @property
    def pattern_type_name(self):
        return self.bom.display_pattern_type_name if self.bom_id else ""

    @property
    def license_name(self):
        return self.bom.license_name if self.bom_id else ""

    @property
    def character_name(self):
        return self.bom.character_name if self.bom_id else ""

    @property
    def mrp(self):
        return self.bom.selling_price if self.bom_id else Decimal("0")

    @property
    def color_drawcord_tie_dye_price(self):
        return self.bom.color_price if self.bom_id else Decimal("0")

    @property
    def accessories_price(self):
        return self.bom.accessories_price if self.bom_id else Decimal("0")

    @property
    def product_image(self):
        return self.bom.product_image if self.bom_id else None


class ProgramJobberItem(models.Model):
    program = models.ForeignKey(
        "Program",
        on_delete=models.CASCADE,
        related_name="jobber_items",
    )
    jobber = models.ForeignKey(
        "Jobber",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="program_jobber_items",
    )
    jobber_type = models.ForeignKey(
        "JobberType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="program_jobber_items",
    )
    jobber_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    issue_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    inward_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def save(self, *args, **kwargs):
        if self.jobber and not self.jobber_type:
            self.jobber_type = self.jobber.jobber_type
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.program} - {self.jobber or self.jobber_type or 'Jobber'}"


class ProgramSizeDetail(models.Model):
    SIZE_CHOICES = [
        ("XS", "XS"),
        ("S", "S"),
        ("M", "M"),
        ("L", "L"),
        ("XL", "XL"),
        ("XXL", "XXL"),
        ("3XL", "3XL"),
        ("4XL", "4XL"),
        ("5XL", "5XL"),
    ]

    program = models.ForeignKey(
        "Program",
        on_delete=models.CASCADE,
        related_name="size_details",
    )
    size = models.CharField(max_length=10, choices=SIZE_CHOICES)

    cq = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fq = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    dq = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fq_dq = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tp = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]
        unique_together = [("program", "size")]

    def __str__(self):
        return f"{self.program} - {self.size}"
    
    
    
class Expense(OwnedModel):
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ["name"]
        unique_together = [("owner", "name")]

    def __str__(self):
        return self.name
    
class DyeingOtherCharge(OwnedModel):
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ["name"]
        unique_together = [("owner", "name")]

    def __str__(self):
        return self.name
    
class TermsCondition(OwnedModel):
    title = models.CharField(max_length=150)
    content = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]
        unique_together = [("owner", "title")]

    def __str__(self):
        return self.title