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
    # ✅ Needed because your forms.py uses Material.MATERIAL_KIND_CHOICES
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

    # Step 2 (master-driven)
    material_type = models.ForeignKey(
        "MaterialType",
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.party_name


# ============================================================
# LOCATION
# ============================================================

class Location(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="locations")
    name = models.CharField(max_length=120)
    city = models.CharField(max_length=80, blank=True, default="")
    state = models.CharField(max_length=80, blank=True, default="")
    address = models.TextField(blank=True, default="")
    pincode = models.CharField(max_length=10, blank=True, default="")
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
    firm_type = models.CharField(max_length=30, choices=FIRM_TYPES)

    address_line = models.CharField(max_length=255)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80)
    pincode = models.CharField(max_length=10)

    phone = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    website = models.URLField(blank=True, default="")

    gst_number = models.CharField(max_length=15, blank=True, default="")
    pan_number = models.CharField(max_length=10, blank=True, default="")
    tan_number = models.CharField(max_length=10, blank=True, default="")
    cin_number = models.CharField(max_length=21, blank=True, default="")

    bank_name = models.CharField(max_length=120, blank=True, default="")
    account_holder_name = models.CharField(max_length=120, blank=True, default="")
    account_number = models.CharField(max_length=30, blank=True, default="")
    ifsc_code = models.CharField(max_length=11, blank=True, default="")
    branch_name = models.CharField(max_length=120, blank=True, default="")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.firm_name
