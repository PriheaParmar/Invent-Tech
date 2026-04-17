from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone


# ============================================================
# USER
# ============================================================
MATERIAL_KIND_CHOICES = (
    ("yarn", "Yarn"),
    ("greige", "Greige"),
    ("finished", "Finished"),
    ("trim", "Trim"),
)


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

    material_kind = models.CharField(max_length=16, choices=MATERIAL_KIND_CHOICES, default="yarn")
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
    FINISH_TYPE_CHOICES = [
        ("dyed", "Dyed"),
        ("printed", "Printed"),
        ("coated", "Coated"),
        ("washed", "Washed"),
        ("other", "Other"),
    ]

    material = models.OneToOneField(Material, on_delete=models.CASCADE, related_name="finished")
    base_fabric_type = models.CharField(max_length=120, blank=True)
    finish_type = models.CharField(max_length=20, choices=FINISH_TYPE_CHOICES, blank=True)
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
# UTILITIES
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
    material_type = models.ForeignKey(MaterialType, on_delete=models.CASCADE, related_name="sub_types")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("owner", "material_type", "name")]

    def __str__(self):
        return self.name


class Firm(models.Model):
    FIRM_TYPE_CHOICES = [
        ("law_firm", "Law Firm"),
        ("company", "Company"),
        ("individual", "Individual"),
        ("startup", "Startup"),
        ("other", "Other"),
    ]

    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="firm")
    firm_name = models.CharField(max_length=180)
    firm_type = models.CharField(max_length=20, choices=FIRM_TYPE_CHOICES, default="company")
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
    APPROVAL_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    system_number = models.CharField(max_length=30, unique=True, blank=True)
    po_number = models.CharField(max_length=30, blank=True, default="")
    po_date = models.DateField()
    cancel_date = models.DateField(null=True, blank=True)
    vendor = models.ForeignKey("Vendor", on_delete=models.PROTECT, related_name="yarn_purchase_orders")
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
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default="pending")
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
        label = self.material_type.name if self.material_type else str(self.material) if self.material else "Yarn Item"
        return f"{self.po} - {label}"


class YarnPOInward(OwnedModel):
    po = models.ForeignKey("YarnPurchaseOrder", on_delete=models.CASCADE, related_name="inwards")
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
    inward = models.ForeignKey(YarnPOInward, on_delete=models.CASCADE, related_name="items")
    po_item = models.ForeignKey("YarnPurchaseOrderItem", on_delete=models.CASCADE, related_name="inward_items")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remark = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = ("inward", "po_item")

    def __str__(self):
        return f"{self.inward.inward_number} / {self.po_item_id}"


class GreigePurchaseOrder(OwnedModel):
    APPROVAL_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

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
    source_yarn_po = models.ForeignKey("YarnPurchaseOrder", on_delete=models.CASCADE, related_name="greige_pos")
    source_yarn_inward = models.ForeignKey(
        "YarnPOInward",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_greige_pos",
    )
    vendor = models.ForeignKey("Vendor", on_delete=models.PROTECT, related_name="greige_purchase_orders")
    firm = models.ForeignKey(
        "Firm",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="greige_purchase_orders",
    )
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default="pending")
    rejection_reason = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_greige_purchase_orders",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.po_date:
            self.po_date = timezone.localdate()

        if self.source_yarn_po_id:
            source_po = self.source_yarn_po

            if not self.vendor_id and getattr(source_po, "vendor_id", None):
                self.vendor = source_po.vendor

            if not self.firm_id and getattr(source_po, "firm_id", None):
                self.firm = source_po.firm

            if not self.shipping_address and getattr(source_po, "firm", None):
                self.shipping_address = source_po.firm.full_address

        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.system_number or f"Greige PO {self.pk or 'Draft'}"


class GreigePurchaseOrderItem(models.Model):
    po = models.ForeignKey("GreigePurchaseOrder", on_delete=models.CASCADE, related_name="items")
    source_yarn_po_item = models.ForeignKey(
        "YarnPurchaseOrderItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_greige_items",
    )
    material = models.ForeignKey(
        "Material",
        on_delete=models.PROTECT,
        related_name="greige_po_items",
        null=True,
        blank=True,
        limit_choices_to={"material_kind": "greige"},
    )
    fabric_name = models.CharField(max_length=150, blank=True, default="")
    yarn_name = models.CharField(max_length=150, blank=True, default="")
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
        label = self.fabric_name or (self.material.name if self.material else "Greige Item")
        return f"{self.po} - {label}"


class GreigePOInward(OwnedModel):
    po = models.ForeignKey("GreigePurchaseOrder", on_delete=models.CASCADE, related_name="inwards")
    inward_number = models.CharField(max_length=30, unique=True)
    inward_date = models.DateField(default=timezone.localdate)
    vendor = models.ForeignKey(
        "Vendor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="greige_inwards",
    )
    inward_type = models.ForeignKey(
        "InwardType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="greige_inwards",
    )
    notes = models.TextField(blank=True, default="")


class GreigePOInwardItem(models.Model):
    inward = models.ForeignKey("GreigePOInward", on_delete=models.CASCADE, related_name="items")
    po_item = models.ForeignKey("GreigePurchaseOrderItem", on_delete=models.CASCADE, related_name="inward_items")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remark = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = ("inward", "po_item")

    def __str__(self):
        return f"{self.inward.inward_number} / {self.po_item_id}"


class DyeingPurchaseOrder(OwnedModel):
    APPROVAL_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    system_number = models.CharField(max_length=30, unique=True, blank=True)
    po_number = models.CharField(max_length=30, blank=True, default="")
    po_date = models.DateField(default=timezone.localdate)
    internal_po_number = models.CharField(max_length=30, blank=True, default="")
    expected_delivery_date = models.DateField(null=True, blank=True)
    cancel_date = models.DateField(null=True, blank=True)
    shipping_address = models.CharField(max_length=255, blank=True, default="")
    address = models.TextField(blank=True, default="")
    remarks = models.TextField(blank=True, default="")
    terms_conditions = models.TextField(blank=True, default="")
    description = models.TextField(blank=True, default="")
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
    source_greige_inward = models.ForeignKey(
        "GreigePOInward",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_dyeing_pos",
    )
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default="pending")
    rejection_reason = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_dyeing_purchase_orders",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    total_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    after_discount_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    others = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    tcs_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        if not self.po_date:
            self.po_date = timezone.localdate()

        if self.source_greige_po_id:
            source_po = self.source_greige_po

            if not self.vendor_id and getattr(source_po, "vendor_id", None):
                self.vendor = source_po.vendor

            source_firm = getattr(source_po, "firm", None) or getattr(getattr(source_po, "source_yarn_po", None), "firm", None)
            if not self.firm_id and source_firm is not None:
                self.firm = source_firm

            if not self.shipping_address and self.firm_id:
                self.shipping_address = self.firm.full_address

        super().save(*args, **kwargs)

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
    po = models.ForeignKey("DyeingPurchaseOrder", on_delete=models.CASCADE, related_name="items")
    source_greige_po_item = models.ForeignKey(
        "GreigePurchaseOrderItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_dyeing_items",
    )
    dyeing_master_detail = models.ForeignKey(
        "DyeingMaterialLinkDetail",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dyeing_po_items",
    )
    finished_material = models.ForeignKey(
        "Material",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="dyeing_po_finished_items",
        limit_choices_to={"material_kind": "finished"},
    )
    dyeing_other_charge = models.ForeignKey(
        "DyeingOtherCharge",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dyeing_po_items",
    )

    fabric_name = models.CharField(max_length=150, blank=True, default="")
    greige_name = models.CharField(max_length=150, blank=True, default="")
    unit = models.CharField(max_length=20, blank=True, default="")

    # LEGACY FIELDS - keep for current compatibility
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remaining_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # NEW BUSINESS-SAFE FIELDS
    source_input_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expected_loss_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    expected_output_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual_output_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance_output_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    rolls = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    dyeing_type = models.CharField(max_length=50, blank=True, default="")
    dyeing_name = models.CharField(max_length=120, blank=True, default="")

    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_charge_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    job_work_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    description = models.TextField(blank=True, default="")
    remark = models.CharField(max_length=255, blank=True, default="")

    line_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_final_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    @property
    def inward_qty_total(self):
        total = self.inward_items.aggregate(total=Sum("quantity")).get("total") or Decimal("0")
        return total

    @property
    def accepted_inward_qty_total(self):
        total = self.inward_items.aggregate(total=Sum("accepted_qty")).get("total") or Decimal("0")
        return total

    @property
    def rejected_inward_qty_total(self):
        total = self.inward_items.aggregate(total=Sum("rejected_qty")).get("total") or Decimal("0")
        return total

    @property
    def hold_inward_qty_total(self):
        total = self.inward_items.aggregate(total=Sum("hold_qty")).get("total") or Decimal("0")
        return total

    @property
    def remaining_qty_total(self):
        ordered = self.quantity or Decimal("0")
        inward = self.inward_qty_total or Decimal("0")
        return ordered - inward if ordered > inward else Decimal("0")

    @property
    def planned_process_qty(self):
        if self.source_input_qty and self.source_input_qty > 0:
            return self.source_input_qty
        if self.total_qty and self.total_qty > 0:
            return self.total_qty
        return self.quantity or Decimal("0")

    @property
    def effective_expected_output_qty(self):
        if self.expected_output_qty and self.expected_output_qty > 0:
            return self.expected_output_qty
        return self.planned_process_qty

    @property
    def effective_balance_output_qty(self):
        if self.balance_output_qty and self.balance_output_qty > 0:
            return self.balance_output_qty
        return self.remaining_qty_total

    class Meta:
        ordering = ["id"]

    def __str__(self):
        label = self.fabric_name or (self.finished_material.name if self.finished_material else "Dyeing Item")
        return f"{self.po} - {label}"



class DyeingPOInward(OwnedModel):
    po = models.ForeignKey("DyeingPurchaseOrder", on_delete=models.CASCADE, related_name="inwards")
    inward_number = models.CharField(max_length=30, unique=True)
    inward_date = models.DateField(default=timezone.localdate)
    vendor = models.ForeignKey(
        "Vendor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dyeing_inwards",
    )
    inward_type = models.ForeignKey(
        "InwardType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dyeing_inwards",
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-inward_date", "-id"]

    def __str__(self):
        return self.inward_number



class DyeingPOInwardItem(models.Model):
    QC_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("partial", "Partial"),
        ("hold", "Hold"),
        ("rejected", "Rejected"),
    ]

    inward = models.ForeignKey(DyeingPOInward, on_delete=models.CASCADE, related_name="items")
    po_item = models.ForeignKey("DyeingPurchaseOrderItem", on_delete=models.CASCADE, related_name="inward_items")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    received_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    accepted_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    rejected_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hold_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual_rolls = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual_gsm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    actual_width = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    dye_lot_no = models.CharField(max_length=80, blank=True, default="")
    batch_no = models.CharField(max_length=80, blank=True, default="")
    shade_reference = models.CharField(max_length=120, blank=True, default="")
    qc_status = models.CharField(max_length=20, choices=QC_STATUS_CHOICES, default="pending")
    remark = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = ("inward", "po_item")

    def save(self, *args, **kwargs):
        if (self.received_qty or Decimal("0")) <= 0 and (self.quantity or Decimal("0")) > 0:
            self.received_qty = self.quantity
        total_split = (self.accepted_qty or Decimal("0")) + (self.rejected_qty or Decimal("0")) + (self.hold_qty or Decimal("0"))
        if total_split <= 0 and (self.quantity or Decimal("0")) > 0:
            self.accepted_qty = self.quantity
        super().save(*args, **kwargs)

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
    source_dyeing_po = models.ForeignKey("DyeingPurchaseOrder", on_delete=models.CASCADE, related_name="ready_pos")
    vendor = models.ForeignKey("Vendor", on_delete=models.PROTECT, related_name="ready_purchase_orders")
    firm = models.ForeignKey(
        "Firm",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ready_purchase_orders",
    )
    remarks = models.TextField(blank=True, default="")
    total_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        if not self.po_date:
            self.po_date = timezone.localdate()

        if self.source_dyeing_po_id:
            source_po = self.source_dyeing_po

            if not self.vendor_id and getattr(source_po, "vendor_id", None):
                self.vendor = source_po.vendor

            if not self.firm_id and getattr(source_po, "firm_id", None):
                self.firm = source_po.firm

            if not self.shipping_address and getattr(source_po, "shipping_address", ""):
                self.shipping_address = source_po.shipping_address
            elif not self.shipping_address and self.firm_id:
                self.shipping_address = self.firm.full_address

        super().save(*args, **kwargs)

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
    po = models.ForeignKey("ReadyPurchaseOrder", on_delete=models.CASCADE, related_name="items")
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
    po = models.ForeignKey("ReadyPurchaseOrder", on_delete=models.CASCADE, related_name="inwards")
    inward_number = models.CharField(max_length=30, unique=True)
    inward_date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-inward_date", "-id"]

    def __str__(self):
        return self.inward_number


class ReadyPOInwardItem(models.Model):
    inward = models.ForeignKey(ReadyPOInward, on_delete=models.CASCADE, related_name="items")
    po_item = models.ForeignKey("ReadyPurchaseOrderItem", on_delete=models.CASCADE, related_name="inward_items")
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


class Expense(OwnedModel):
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ["name"]
        unique_together = [("owner", "name")]

    def __str__(self):
        return self.name


class Accessory(OwnedModel):
    name = models.CharField(max_length=120)
    default_unit = models.ForeignKey(
        "MaterialUnit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accessories",
    )
    description = models.TextField(blank=True, default="")

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


class SubCategory(OwnedModel):
    main_category = models.ForeignKey(MainCategory, on_delete=models.CASCADE, related_name="sub_categories")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["main_category__name", "name"]
        unique_together = [("owner", "main_category", "name")]

    def __str__(self):
        return f"{self.main_category.name} / {self.name}"


SIZE_TYPE_CHOICES = [
    ("regular", "Regular"),
    ("plus", "Plus"),
    ("kids", "Kids"),
    ("combo", "Combo"),
]


class BOM(OwnedModel):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    bom_code = models.CharField(max_length=50)
    sku = models.CharField(max_length=100)
    product_name = models.CharField(max_length=255)
    character_name = models.CharField(max_length=120, blank=True, default="")
    license_name = models.CharField(max_length=120, blank=True, default="")
    mrp = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    color = models.CharField(max_length=80, blank=True, default="")
    drawcord = models.CharField(max_length=120, blank=True, default="")
    tie_dye_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    maintenance_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    damage_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0, blank=True)
    final_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    catalogue = models.ForeignKey("Catalogue", on_delete=models.SET_NULL, null=True, blank=True, related_name="boms")
    brand = models.ForeignKey("Brand", on_delete=models.SET_NULL, null=True, blank=True, related_name="boms")
    category = models.ForeignKey("Category", on_delete=models.SET_NULL, null=True, blank=True, related_name="boms")
    main_category = models.ForeignKey("MainCategory", on_delete=models.SET_NULL, null=True, blank=True, related_name="boms")
    sub_category = models.ForeignKey("SubCategory", on_delete=models.SET_NULL, null=True, blank=True, related_name="boms")
    pattern_type = models.ForeignKey("PatternType", on_delete=models.SET_NULL, null=True, blank=True, related_name="boms")
    gender = models.CharField(max_length=30, blank=True, default="")
    size_type = models.CharField(max_length=20, choices=SIZE_TYPE_CHOICES, blank=True, default="regular")
    notes = models.TextField(blank=True, default="")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")

    class Meta:
        ordering = ["-id"]
        unique_together = [("owner", "bom_code"), ("owner", "sku")]

    @property
    def expense_total(self):
        total = self.expense_items.aggregate(total=Sum("price")).get("total") or Decimal("0")
        return total

    @property
    def damage_amount(self):
        base_price = self.price or Decimal("0")
        expense_total = self.expense_total or Decimal("0")
        damage_percent = self.damage_percent or Decimal("0")
        return (base_price + expense_total) * damage_percent / Decimal("100")

    def recalculate_final_price(self, save=True):
        base_price = self.price or Decimal("0")
        expense_total = self.expense_total or Decimal("0")
        damage_amount = self.damage_amount or Decimal("0")
        self.final_price = base_price + expense_total + damage_amount
        if save and self.pk:
            self.save(update_fields=["final_price", "updated_at"])
        return self.final_price

    def __str__(self):
        return f"{self.bom_code} - {self.product_name}"


class BOMMaterialItem(models.Model):
    bom = models.ForeignKey("BOM", on_delete=models.CASCADE, related_name="material_items")
    material = models.ForeignKey(
        "Material",
        on_delete=models.PROTECT,
        related_name="bom_material_items",
        limit_choices_to={"material_kind__in": ["yarn", "greige", "finished", "trim"]},
    )
    unit = models.ForeignKey("MaterialUnit", on_delete=models.SET_NULL, null=True, blank=True, related_name="bom_material_items")
    cost_per_unit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def save(self, *args, **kwargs):
        self.cost = (self.cost_per_unit or Decimal("0")) * (self.avg or Decimal("0"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bom.bom_code} - Material - {self.material.name}"


class BOMAccessoryItem(models.Model):
    bom = models.ForeignKey("BOM", on_delete=models.CASCADE, related_name="accessory_items")
    accessory = models.ForeignKey("Accessory", on_delete=models.PROTECT, related_name="bom_items")
    unit = models.ForeignKey("MaterialUnit", on_delete=models.SET_NULL, null=True, blank=True, related_name="bom_accessory_items")
    cost_per_unit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def save(self, *args, **kwargs):
        self.cost = (self.cost_per_unit or Decimal("0")) * (self.avg or Decimal("0"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bom.bom_code} - Accessory - {self.accessory.name}"


class BOMImage(models.Model):
    bom = models.ForeignKey("BOM", on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="bom/%Y/%m/", blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.bom.bom_code} - Image {self.id}"


class BOMJobberTypeProcess(models.Model):
    bom = models.ForeignKey("BOM", on_delete=models.CASCADE, related_name="jobber_type_processes")
    jobber_type = models.ForeignKey("JobberType", on_delete=models.PROTECT, related_name="bom_jobber_type_processes")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.bom.bom_code} - {self.jobber_type.name}"


class BOMJobberDetail(models.Model):
    bom = models.ForeignKey("BOM", on_delete=models.CASCADE, related_name="jobber_details")
    jobber = models.ForeignKey("Jobber", on_delete=models.PROTECT, related_name="bom_jobber_details")
    jobber_type = models.ForeignKey("JobberType", on_delete=models.PROTECT, related_name="bom_jobber_detail_types")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.bom.bom_code} - {self.jobber.name}"


class BOMExpenseItem(models.Model):
    bom = models.ForeignKey("BOM", on_delete=models.CASCADE, related_name="expense_items")
    expense = models.ForeignKey("Expense", on_delete=models.PROTECT, related_name="bom_expense_items")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.bom.bom_code} - {self.expense.name}"


PROGRAM_STATUS_CHOICES = (
    ("open", "Open"),
    ("closed", "Closed"),
)

PROGRAM_SIZE_LINE_CHOICES = (
    ("CQ", "CQ"),
    ("FQ", "FQ"),
    ("DQ", "DQ"),
    ("FQ-DQ", "FQ-DQ"),
    ("TP", "TP"),
)


class Program(OwnedModel):
    program_no = models.CharField(max_length=30)
    program_date = models.DateField(default=timezone.localdate)
    finishing_date = models.DateField(null=True, blank=True)
    total_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ratio = models.CharField(max_length=120, blank=True, default="")
    cutting_invoice_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    stitching_invoice_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    is_verified = models.BooleanField(default=False)
    glt_days = models.PositiveIntegerField(default=0)
    glt_on_100_days = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=PROGRAM_STATUS_CHOICES, default="open")
    firm = models.ForeignKey("Firm", on_delete=models.SET_NULL, null=True, blank=True, related_name="programs")
    damage = models.DecimalField(max_digits=8, decimal_places=2, default=0, blank=True)
    bom = models.ForeignKey("BOM", on_delete=models.PROTECT, related_name="programs")

    class Meta:
        ordering = ["-id"]
        unique_together = [("owner", "program_no")]

    @classmethod
    def next_program_no(cls, owner):
        today = timezone.localdate()
        prefix = f"PRG-{today:%y%m}-"
        last_program_no = (
            cls.objects.filter(owner=owner, program_no__startswith=prefix)
            .order_by("-program_no")
            .values_list("program_no", flat=True)
            .first()
        )

        next_seq = 1
        if last_program_no:
            try:
                next_seq = int(last_program_no.rsplit("-", 1)[-1]) + 1
            except Exception:
                next_seq = cls.objects.filter(owner=owner, program_no__startswith=prefix).count() + 1

        return f"{prefix}{next_seq:04d}"

    def save(self, *args, **kwargs):
        if not self.program_no and self.owner_id:
            self.program_no = self.next_program_no(self.owner)
        if not self.program_date:
            self.program_date = timezone.localdate()
        super().save(*args, **kwargs)

    @property
    def cost_price(self):
        return self.bom.final_price or Decimal("0")

    @property
    def avg_price(self):
        return self.bom.price or Decimal("0")

    @property
    def preview_image_url(self):
        first_image = self.bom.images.order_by("sort_order", "id").first()
        if first_image and first_image.image:
            return first_image.image.url
        return ""

    @property
    def assigned_jobber_names(self):
        start = getattr(self, "start_record", None)
        if start:
            rows = start.jobber_rows.select_related("jobber").all()
            return [row.jobber.name for row in rows if row.jobber_id and row.jobber]
        rows = self.jobber_rows.select_related("jobber").all()
        return [row.jobber.name for row in rows if row.jobber_id and row.jobber]

    def __str__(self):
        return f"{self.program_no} - {self.bom.sku}"


class ProgramJobberDetail(models.Model):
    program = models.ForeignKey("Program", on_delete=models.CASCADE, related_name="jobber_rows")
    jobber = models.ForeignKey("Jobber", on_delete=models.PROTECT, related_name="program_jobber_rows")
    jobber_type = models.ForeignKey("JobberType", on_delete=models.PROTECT, related_name="program_jobber_type_rows")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)
    issued_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    inward_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.program.program_no} - {self.jobber.name}"


class ProgramSizeDetail(models.Model):
    program = models.ForeignKey("Program", on_delete=models.CASCADE, related_name="size_rows")
    line_name = models.CharField(max_length=20, choices=PROGRAM_SIZE_LINE_CHOICES)
    xs_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    s_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    m_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    l_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    xl_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    xxl_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        unique_together = [("program", "line_name")]

    def __str__(self):
        return f"{self.program.program_no} - {self.line_name}"

class ProgramStart(OwnedModel):
    program = models.OneToOneField(
        "Program",
        on_delete=models.CASCADE,
        related_name="start_record",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    is_started = models.BooleanField(default=False)
    remarks = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"Start - {self.program.program_no}"


class ProgramStartFabric(models.Model):
    start_record = models.ForeignKey(
        "ProgramStart",
        on_delete=models.CASCADE,
        related_name="fabric_rows",
    )
    material = models.ForeignKey(
        "Material",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="program_start_fabrics",
    )
    unit = models.ForeignKey(
        "MaterialUnit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="program_start_fabrics",
    )

    used = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    length = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    width = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    count = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    pp_count = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    lot_no = models.CharField(max_length=150, blank=True, default="")
    lot_count = models.PositiveIntegerField(default=0)
    available_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    used_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        material_name = self.material.name if self.material_id else "Fabric"
        return f"{self.start_record.program.program_no} - {material_name}"


class ProgramStartSize(models.Model):
    start_record = models.ForeignKey(
        "ProgramStart",
        on_delete=models.CASCADE,
        related_name="size_rows",
    )
    size_name = models.CharField(max_length=20)
    qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.start_record.program.program_no} - {self.size_name}"


class ProgramStartJobber(models.Model):
    start_record = models.ForeignKey(
        "ProgramStart",
        on_delete=models.CASCADE,
        related_name="jobber_rows",
    )
    jobber = models.ForeignKey(
        "Jobber",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="program_start_jobbers",
    )
    jobber_type = models.ForeignKey(
        "JobberType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="program_start_jobber_types",
    )

    jobber_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    allocation_date = models.DateField(null=True, blank=True)

    invoice_no = models.CharField(max_length=100, blank=True, default="")
    invoice_rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    invoice_date = models.DateField(null=True, blank=True)

    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        jobber_name = self.jobber.name if self.jobber_id else "Jobber"
        return f"{self.start_record.program.program_no} - {jobber_name}"


PROGRAM_JOBBER_CHALLAN_STATUS_CHOICES = (
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("partial", "Partial Inward"),
    ("closed", "Closed"),
)


class ProgramJobberChallan(OwnedModel):
    challan_no = models.CharField(max_length=30, unique=True)
    challan_date = models.DateField(default=timezone.localdate)
    program = models.ForeignKey("Program", on_delete=models.CASCADE, related_name="jobber_challans")
    start_record = models.ForeignKey("ProgramStart", on_delete=models.CASCADE, related_name="jobber_challans")
    start_jobber = models.ForeignKey("ProgramStartJobber", on_delete=models.CASCADE, related_name="challans")
    jobber = models.ForeignKey("Jobber", on_delete=models.SET_NULL, null=True, blank=True, related_name="program_jobber_challans")
    jobber_type = models.ForeignKey("JobberType", on_delete=models.SET_NULL, null=True, blank=True, related_name="program_jobber_challan_types")
    firm = models.ForeignKey("Firm", on_delete=models.SET_NULL, null=True, blank=True, related_name="program_jobber_challans")
    production_sku = models.CharField(max_length=120, blank=True, default="")
    product_name = models.CharField(max_length=180, blank=True, default="")
    total_issued_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    inward_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    driver_name = models.CharField(max_length=120, blank=True, default="")
    lr_no = models.CharField(max_length=80, blank=True, default="")
    transport_name = models.CharField(max_length=150, blank=True, default="")
    vehicle_no = models.CharField(max_length=50, blank=True, default="")
    gate_pass_no = models.CharField(max_length=80, blank=True, default="")
    expected_return_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=PROGRAM_JOBBER_CHALLAN_STATUS_CHOICES, default="pending")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_program_jobber_challans")
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-id"]

    @classmethod
    def next_challan_no(cls):
        last = cls.objects.order_by("-id").first()
        next_id = (last.id + 1) if last else 1
        return f"CHL-{next_id:04d}"

    @property
    def created_by_name(self):
        full_name = ""
        try:
            full_name = self.owner.get_full_name().strip()
        except Exception:
            full_name = ""
        return full_name or getattr(self.owner, "username", "") or "-"

    def refresh_totals(self, save=True):
        total_issue = self.size_rows.aggregate(total=Sum("issued_qty")).get("total") or Decimal("0")
        total_inward = self.size_rows.aggregate(total=Sum("inward_qty")).get("total") or Decimal("0")
        self.total_issued_qty = total_issue
        self.inward_qty = total_inward
        if total_inward <= 0:
            if self.status not in {"approved", "rejected"}:
                self.status = "pending"
        elif total_inward < total_issue:
            self.status = "partial"
        elif total_inward >= total_issue and total_issue > 0:
            self.status = "closed"
        if save and self.pk:
            self.save(update_fields=["total_issued_qty", "inward_qty", "status", "updated_at"])

    def save(self, *args, **kwargs):
        if not self.challan_no:
            self.challan_no = self.next_challan_no()
        if not self.start_record_id and self.start_jobber_id:
            self.start_record = self.start_jobber.start_record
        if not self.program_id:
            if self.start_record_id:
                self.program = self.start_record.program
            elif self.start_jobber_id:
                self.program = self.start_jobber.start_record.program
        if not self.jobber_id and self.start_jobber_id and self.start_jobber.jobber_id:
            self.jobber = self.start_jobber.jobber
        if not self.jobber_type_id and self.start_jobber_id and self.start_jobber.jobber_type_id:
            self.jobber_type = self.start_jobber.jobber_type
        if not self.firm_id and self.program_id and self.program.firm_id:
            self.firm = self.program.firm
        if not self.production_sku and self.program_id and self.program.bom_id:
            self.production_sku = self.program.bom.sku or ""
        if not self.product_name and self.program_id and self.program.bom_id:
            self.product_name = self.program.bom.product_name or ""
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.challan_no} - {self.program.program_no}"


class ProgramJobberChallanSize(models.Model):
    challan = models.ForeignKey("ProgramJobberChallan", on_delete=models.CASCADE, related_name="size_rows")
    size_name = models.CharField(max_length=20)
    issued_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    inward_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.challan_id:
            self.challan.refresh_totals(save=True)

    def delete(self, *args, **kwargs):
        challan = self.challan
        super().delete(*args, **kwargs)
        if challan:
            challan.refresh_totals(save=True)

    def __str__(self):
        return f"{self.challan.challan_no} - {self.size_name}"


class DispatchChallan(OwnedModel):
    challan_no = models.CharField(max_length=30)
    challan_date = models.DateField(default=timezone.localdate)
    program = models.ForeignKey("Program", on_delete=models.CASCADE, related_name="dispatch_challans")
    client = models.ForeignKey("Client", on_delete=models.PROTECT, related_name="dispatch_challans")
    firm = models.ForeignKey("Firm", on_delete=models.SET_NULL, null=True, blank=True, related_name="dispatch_challans")
    driver_name = models.CharField(max_length=120, blank=True, default="")
    lr_no = models.CharField(max_length=80, blank=True, default="")
    transport_name = models.CharField(max_length=150, blank=True, default="")
    vehicle_no = models.CharField(max_length=50, blank=True, default="")
    remarks = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-id"]
        unique_together = [("owner", "challan_no")]

    @classmethod
    def next_challan_no(cls, owner):
        today = timezone.localdate()
        prefix = f"CHL-{today:%y%m}-"
        last_no = (
            cls.objects.filter(owner=owner, challan_no__startswith=prefix)
            .order_by("-challan_no")
            .values_list("challan_no", flat=True)
            .first()
        )

        next_seq = 1
        if last_no:
            try:
                next_seq = int(last_no.rsplit("-", 1)[-1]) + 1
            except Exception:
                next_seq = cls.objects.filter(owner=owner, challan_no__startswith=prefix).count() + 1

        return f"{prefix}{next_seq:04d}"

    def save(self, *args, **kwargs):
        if not self.challan_no and self.owner_id:
            self.challan_no = self.next_challan_no(self.owner)
        if not self.challan_date:
            self.challan_date = timezone.localdate()
        if self.program_id and not self.firm_id:
            self.firm = self.program.firm
        super().save(*args, **kwargs)

    def __str__(self):
        return self.challan_no


class DyeingMaterialLink(OwnedModel):
    vendor = models.ForeignKey("Vendor", on_delete=models.CASCADE, related_name="dyeing_material_links")
    material_type = models.ForeignKey(
        "MaterialType",
        on_delete=models.PROTECT,
        related_name="dyeing_material_links",
        limit_choices_to={"material_kind": "greige"},
    )
    material = models.ForeignKey(
        "Material",
        on_delete=models.PROTECT,
        related_name="dyeing_material_links",
        limit_choices_to={"material_kind": "greige"},
    )
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["vendor__name", "material_type__name", "material__name"]
        unique_together = [("owner", "vendor", "material")]

    def __str__(self):
        vendor_name = self.vendor.name if self.vendor_id else "Vendor"
        material_name = self.material.name if self.material_id else "Material"
        return f"{vendor_name} - {material_name}"


class DyeingMaterialLinkDetail(models.Model):
    DYEING_TYPE_CHOICES = [
        ("plain", "Plain"),
        ("print", "Print"),
        ("pigment", "Pigment"),
        ("reactive", "Reactive"),
        ("wash", "Wash"),
        ("finish", "Finish"),
        ("other", "Other"),
    ]

    link = models.ForeignKey(DyeingMaterialLink, on_delete=models.CASCADE, related_name="details")
    finished_material = models.ForeignKey(
        "Material",
        on_delete=models.PROTECT,
        related_name="dyeing_link_details",
        limit_choices_to={"material_kind": "finished"},
        null=True,
        blank=True,
    )
    dyeing_type = models.CharField(max_length=30, choices=DYEING_TYPE_CHOICES)
    dyeing_name = models.CharField(max_length=120)
    percentage_no_of_colors = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    weight_loss = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        base = self.dyeing_name or "Dyeing Detail"
        if self.finished_material_id:
            return f"{self.link} - {base} - {self.finished_material.name}"
        return f"{self.link} - {base}"

# ============================================================
# PHASE 2 FOUNDATION: LOT / ROLL / QR / QC / COSTING
# ============================================================

LOT_STAGE_CHOICES = [
    ("yarn", "Yarn"),
    ("greige", "Greige"),
    ("dyeing", "Dyeing"),
    ("ready", "Ready"),
]

QC_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("partial", "Partial"),
    ("hold", "Hold"),
    ("rejected", "Rejected"),
]

MOVEMENT_TYPE_CHOICES = [
    ("receipt", "Receipt"),
    ("issue", "Issue"),
    ("return", "Return"),
    ("transfer", "Transfer"),
    ("adjustment", "Adjustment"),
    ("dispatch", "Dispatch"),
]


class InventoryLot(OwnedModel):
    lot_code = models.CharField(max_length=40, unique=True)
    stage = models.CharField(max_length=20, choices=LOT_STAGE_CHOICES, default="ready")
    material = models.ForeignKey("Material", on_delete=models.PROTECT, related_name="inventory_lots")
    unit = models.CharField(max_length=20, blank=True, default="")

    yarn_inward_item = models.ForeignKey(
        "YarnPOInwardItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inventory_lots",
    )
    greige_inward_item = models.ForeignKey(
        "GreigePOInwardItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inventory_lots",
    )
    dyeing_inward_item = models.ForeignKey(
        "DyeingPOInwardItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inventory_lots",
    )
    ready_inward_item = models.ForeignKey(
        "ReadyPOInwardItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inventory_lots",
    )

    dye_lot_no = models.CharField(max_length=80, blank=True, default="")
    batch_no = models.CharField(max_length=80, blank=True, default="")
    shade_reference = models.CharField(max_length=120, blank=True, default="")
    location_name = models.CharField(max_length=120, blank=True, default="")

    received_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    accepted_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    rejected_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hold_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    used_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    available_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    qc_status = models.CharField(max_length=20, choices=QC_STATUS_CHOICES, default="pending")
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-id"]

    def save(self, *args, **kwargs):
        accepted = self.accepted_qty or Decimal("0")
        used = self.used_qty or Decimal("0")
        available = accepted - used
        self.available_qty = available if available > 0 else Decimal("0")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.lot_code


class InventoryRoll(models.Model):
    lot = models.ForeignKey("InventoryLot", on_delete=models.CASCADE, related_name="rolls")
    roll_no = models.CharField(max_length=50)
    length_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    gsm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    weight_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    accepted_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=QC_STATUS_CHOICES, default="pending")

    class Meta:
        ordering = ["id"]
        unique_together = [("lot", "roll_no")]

    def __str__(self):
        return f"{self.lot.lot_code} / {self.roll_no}"


class QRCodeRecord(OwnedModel):
    qr_code = models.CharField(max_length=60, unique=True)
    lot = models.ForeignKey(
        "InventoryLot",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="qr_codes",
    )
    roll = models.ForeignKey(
        "InventoryRoll",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="qr_codes",
    )
    qr_type = models.CharField(
        max_length=20,
        choices=[("lot", "Lot"), ("roll", "Roll")],
        default="lot",
    )
    status = models.CharField(max_length=20, default="active")
    payload_url = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.qr_code


class QualityCheck(OwnedModel):
    qc_number = models.CharField(max_length=40, unique=True)
    stage = models.CharField(max_length=20, choices=LOT_STAGE_CHOICES, default="ready")

    lot = models.ForeignKey(
        "InventoryLot",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="quality_checks",
    )
    roll = models.ForeignKey(
        "InventoryRoll",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="quality_checks",
    )
    dyeing_inward_item = models.ForeignKey(
        "DyeingPOInwardItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quality_checks",
    )
    ready_inward_item = models.ForeignKey(
        "ReadyPOInwardItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quality_checks",
    )

    inspection_date = models.DateField(default=timezone.localdate)
    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
    )
    result = models.CharField(max_length=20, choices=QC_STATUS_CHOICES, default="pending")

    inspected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspected_quality_checks",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_quality_checks",
    )

    remarks = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-inspection_date", "-id"]

    def __str__(self):
        return self.qc_number


class QualityCheckParameter(models.Model):
    quality_check = models.ForeignKey(
        "QualityCheck",
        on_delete=models.CASCADE,
        related_name="parameters",
    )
    parameter_name = models.CharField(max_length=120)
    expected_value = models.CharField(max_length=120, blank=True, default="")
    actual_value = models.CharField(max_length=120, blank=True, default="")
    tolerance = models.CharField(max_length=60, blank=True, default="")
    is_pass = models.BooleanField(default=True)
    remarks = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quality_check.qc_number} / {self.parameter_name}"


class QualityCheckDefect(models.Model):
    quality_check = models.ForeignKey(
        "QualityCheck",
        on_delete=models.CASCADE,
        related_name="defects",
    )
    defect_name = models.CharField(max_length=120)
    severity = models.CharField(
        max_length=20,
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")],
        default="low",
    )
    affected_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remarks = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quality_check.qc_number} / {self.defect_name}"


class InventoryMovement(OwnedModel):
    movement_no = models.CharField(max_length=40, unique=True)
    lot = models.ForeignKey("InventoryLot", on_delete=models.CASCADE, related_name="movements")
    roll = models.ForeignKey(
        "InventoryRoll",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="movements",
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES, default="receipt")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    movement_date = models.DateField(default=timezone.localdate)
    ref_model = models.CharField(max_length=80, blank=True, default="")
    ref_number = models.CharField(max_length=80, blank=True, default="")
    remarks = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-movement_date", "-id"]

    def __str__(self):
        return self.movement_no


class CostingSnapshot(OwnedModel):
    bom = models.ForeignKey(
        "BOM",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="costing_snapshots",
    )
    program = models.ForeignKey(
        "Program",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="costing_snapshots",
    )

    material_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    accessory_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    process_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expense_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    overhead_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    wastage_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    target_margin_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    target_selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mrp = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-id"]

    def save(self, *args, **kwargs):
        self.total_cost = sum(
            [
                self.material_cost or Decimal("0"),
                self.accessory_cost or Decimal("0"),
                self.process_cost or Decimal("0"),
                self.expense_cost or Decimal("0"),
                self.overhead_cost or Decimal("0"),
                self.wastage_cost or Decimal("0"),
            ],
            Decimal("0"),
        )
        if not self.target_selling_price:
            margin = self.target_margin_percent or Decimal("0")
            self.target_selling_price = self.total_cost + (self.total_cost * margin / Decimal("100"))
        super().save(*args, **kwargs)

    def __str__(self):
        if self.program_id:
            return f"Costing - {self.program.program_no}"
        if self.bom_id:
            return f"Costing - {self.bom.bom_code}"
        return f"Costing {self.pk or 'Draft'}"




class ProgramInvoice(OwnedModel):
    invoice_no = models.CharField(max_length=30)
    invoice_date = models.DateField(default=timezone.localdate)
    firm = models.ForeignKey("Firm", on_delete=models.PROTECT, related_name="program_invoices")
    client = models.ForeignKey("Client", on_delete=models.PROTECT, related_name="program_invoices")
    program = models.ForeignKey("Program", on_delete=models.PROTECT, related_name="invoices")
    vehicle_no = models.CharField(max_length=50, blank=True, default="")
    remarks = models.TextField(blank=True, default="")
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    after_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    igst_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["-invoice_date", "-id"]
        unique_together = [("owner", "invoice_no")]

    @classmethod
    def next_invoice_no(cls, owner):
        today = timezone.localdate()
        prefix = f"INV-{today:%y%m}-"
        last_no = (
            cls.objects.filter(owner=owner, invoice_no__startswith=prefix)
            .order_by("-invoice_no")
            .values_list("invoice_no", flat=True)
            .first()
        )
        next_seq = 1
        if last_no:
            try:
                next_seq = int(last_no.rsplit("-", 1)[-1]) + 1
            except Exception:
                next_seq = cls.objects.filter(owner=owner, invoice_no__startswith=prefix).count() + 1
        return f"{prefix}{next_seq:04d}"

    def recompute_totals(self, save=False):
        sub_total = self.items.aggregate(total=Sum("amount")).get("total") or Decimal("0")
        discount_percent = self.discount_percent or Decimal("0")
        self.sub_total = sub_total
        self.discount_amount = (sub_total * discount_percent / Decimal("100")).quantize(Decimal("0.01"))
        self.after_discount_amount = (sub_total - self.discount_amount).quantize(Decimal("0.01"))
        base_amount = self.after_discount_amount + (self.other_charges or Decimal("0"))
        gst_percent = self.gst_percent or Decimal("0")
        igst_percent = self.igst_percent or Decimal("0")
        self.gst_amount = (base_amount * gst_percent / Decimal("100")).quantize(Decimal("0.01"))
        self.igst_amount = (base_amount * igst_percent / Decimal("100")).quantize(Decimal("0.01"))
        self.final_amount = (base_amount + self.gst_amount + self.igst_amount).quantize(Decimal("0.01"))
        if save and self.pk:
            self.save(update_fields=[
                "sub_total", "discount_amount", "after_discount_amount", "gst_amount", "igst_amount", "final_amount", "updated_at"
            ])

    def save(self, *args, **kwargs):
        if not self.invoice_no and self.owner_id:
            self.invoice_no = self.next_invoice_no(self.owner)
        if not self.invoice_date:
            self.invoice_date = timezone.localdate()
        if self.program_id and not self.firm_id and getattr(self.program, "firm_id", None):
            self.firm = self.program.firm
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_no


class ProgramInvoiceItem(models.Model):
    invoice = models.ForeignKey("ProgramInvoice", on_delete=models.CASCADE, related_name="items")
    dispatch_challan = models.ForeignKey("DispatchChallan", on_delete=models.SET_NULL, null=True, blank=True, related_name="invoice_items")
    program_label = models.CharField(max_length=80, blank=True, default="")
    sku = models.CharField(max_length=120, blank=True, default="")
    challan_no = models.CharField(max_length=30, blank=True, default="")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hsn_code = models.CharField(max_length=30, blank=True, default="")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def save(self, *args, **kwargs):
        self.amount = (Decimal(self.quantity or 0) * Decimal(self.price or 0)).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice.invoice_no} - {self.challan_no or self.pk}"


class MaintenanceRecord(OwnedModel):
    month_key = models.CharField(max_length=7)
    inward_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expense_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    entry_date = models.DateField(default=timezone.localdate)
    remarks = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-month_key", "-id"]
        unique_together = [("owner", "month_key")]

    @property
    def month_display(self):
        try:
            year, month = self.month_key.split("-")
            month_num = int(month)
            names = ["January","February","March","April","May","June","July","August","September","October","November","December"]
            return f"{names[month_num-1]} {year}"
        except Exception:
            return self.month_key

    def save(self, *args, **kwargs):
        self.cost_total = (Decimal(self.inward_total or 0) + Decimal(self.expense_total or 0)).quantize(Decimal("0.01"))
        if not self.entry_date:
            self.entry_date = timezone.localdate()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.month_display


def next_quality_check_number():
    last = QualityCheck.objects.order_by("-id").first()
    return f"QC-{((last.id + 1) if last else 1):05d}"


def next_inventory_movement_number():
    last = InventoryMovement.objects.order_by("-id").first()
    return f"MOV-{((last.id + 1) if last else 1):05d}"


def next_qr_code_number():
    last = QRCodeRecord.objects.order_by("-id").first()
    return f"QR-{((last.id + 1) if last else 1):05d}"