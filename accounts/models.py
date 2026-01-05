from django.conf import settings
from django.db import models

class UserExtra(models.Model):
    """Extra user information (admin-side)."""

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

class Material(models.Model):
    class Type(models.TextChoices):
        YARN = "yarn", "Yarn"
        GREIGE = "greige", "Greige"
        FINISHED = "finished", "Finished Material"
        TRIM = "trim", "Trim"

    material_type = models.CharField(max_length=16, choices=Type.choices,
        default=Type.YARN,)
    name = models.CharField(max_length=150)
    remarks = models.TextField(blank=True)

    image = models.ImageField(upload_to="materials/%Y/%m/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_material_type_display()} - {self.name}"


class YarnDetail(models.Model):
    material = models.OneToOneField(Material, on_delete=models.CASCADE, related_name="yarn")

    yarn_type = models.CharField(max_length=80, blank=True)
    yarn_subtype = models.CharField(max_length=80, blank=True)
    count_denier = models.CharField(max_length=40, blank=True)
    color = models.CharField(max_length=60, blank=True)

    def __str__(self):
        return f"YarnDetail({self.material_id})"


class GreigeDetail(models.Model):
    material = models.OneToOneField(Material, on_delete=models.CASCADE, related_name="greige")

    fabric_type = models.CharField(max_length=120, blank=True)
    gsm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    construction = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return f"GreigeDetail({self.material_id})"


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

    def __str__(self):
        return f"FinishedDetail({self.material_id})"


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

    def __str__(self):
        return f"TrimDetail({self.material_id})"
