from django import forms
from .models import Jobber, JobberType
from django.core.exceptions import ValidationError
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import (
    Material, YarnDetail, GreigeDetail, FinishedDetail, TrimDetail
)

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

class MaterialForm(forms.Form):
    # STEP 1 (only this is shown initially)
    material_type = forms.ChoiceField(choices=Material.Type.choices)

    # STEP 2 common
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

    def __init__(self, *args, instance: Material | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance

        self.fields["name"].widget.attrs.update({"placeholder": "Enter name"})
        self.fields["remarks"].widget.attrs.update({"placeholder": "Remarks (optional)"})

        if instance:
            self.fields["material_type"].initial = instance.material_type
            self.fields["name"].initial = instance.name
            self.fields["remarks"].initial = instance.remarks

            if instance.material_type == Material.Type.YARN and hasattr(instance, "yarn"):
                self.fields["yarn_type"].initial = instance.yarn.yarn_type
                self.fields["yarn_subtype"].initial = instance.yarn.yarn_subtype
                self.fields["count_denier"].initial = instance.yarn.count_denier
                self.fields["yarn_color"].initial = instance.yarn.color

            if instance.material_type == Material.Type.GREIGE and hasattr(instance, "greige"):
                self.fields["fabric_type"].initial = instance.greige.fabric_type
                self.fields["gsm"].initial = instance.greige.gsm
                self.fields["width"].initial = instance.greige.width
                self.fields["construction"].initial = instance.greige.construction

            if instance.material_type == Material.Type.FINISHED and hasattr(instance, "finished"):
                self.fields["base_fabric_type"].initial = instance.finished.base_fabric_type
                self.fields["finish_type"].initial = instance.finished.finish_type
                self.fields["finished_gsm"].initial = instance.finished.gsm
                self.fields["finished_width"].initial = instance.finished.width
                self.fields["end_use"].initial = instance.finished.end_use

            if instance.material_type == Material.Type.TRIM and hasattr(instance, "trim"):
                self.fields["trim_type"].initial = instance.trim.trim_type
                self.fields["trim_size"].initial = instance.trim.size
                self.fields["trim_color"].initial = instance.trim.color
                self.fields["brand"].initial = instance.trim.brand

    def clean(self):
        cleaned = super().clean()
        t = cleaned.get("material_type")

        # image rules (edit-safe: if instance already has image, allow no new upload)
        IMAGE_REQUIRED = {
            Material.Type.YARN: False,
            Material.Type.GREIGE: False,
            Material.Type.FINISHED: True,
            Material.Type.TRIM: False,
        }
        need_img = IMAGE_REQUIRED.get(t, False)
        if need_img and not cleaned.get("image") and not (self.instance and self.instance.image):
            raise ValidationError({"image": "Image is required for this material type."})

        # required per type
        if t == Material.Type.YARN:
            if not cleaned.get("yarn_type"):
                raise ValidationError({"yarn_type": "Yarn Type is required."})

        elif t == Material.Type.GREIGE:
            if not cleaned.get("fabric_type"):
                raise ValidationError({"fabric_type": "Fabric Type is required."})

        elif t == Material.Type.FINISHED:
            if not cleaned.get("base_fabric_type"):
                raise ValidationError({"base_fabric_type": "Base Fabric Type is required."})
            if not cleaned.get("finish_type"):
                raise ValidationError({"finish_type": "Finish Type is required."})

        elif t == Material.Type.TRIM:
            if not cleaned.get("trim_type"):
                raise ValidationError({"trim_type": "Trim Type is required."})

        return cleaned

    def save(self) -> Material:
        if not self.is_valid():
            raise ValueError("Call is_valid() before save().")

        cd = self.cleaned_data
        t = cd["material_type"]

        material = self.instance or Material()
        material.material_type = t
        material.name = cd["name"]
        material.remarks = cd.get("remarks", "")

        img = cd.get("image")
        if img:
            material.image = img
        material.save()

        # delete old details (if type changed / editing)
        YarnDetail.objects.filter(material=material).delete()
        GreigeDetail.objects.filter(material=material).delete()
        FinishedDetail.objects.filter(material=material).delete()
        TrimDetail.objects.filter(material=material).delete()

        if t == Material.Type.YARN:
            YarnDetail.objects.create(
                material=material,
                yarn_type=cd["yarn_type"],
                yarn_subtype=cd.get("yarn_subtype", ""),
                count_denier=cd.get("count_denier", ""),
                color=cd.get("yarn_color", ""),
            )
        elif t == Material.Type.GREIGE:
            GreigeDetail.objects.create(
                material=material,
                fabric_type=cd["fabric_type"],
                gsm=cd.get("gsm"),
                width=cd.get("width"),
                construction=cd.get("construction", ""),
            )
        elif t == Material.Type.FINISHED:
            FinishedDetail.objects.create(
                material=material,
                base_fabric_type=cd["base_fabric_type"],
                finish_type=cd["finish_type"],
                gsm=cd.get("finished_gsm"),
                width=cd.get("finished_width"),
                end_use=cd.get("end_use", ""),
            )
        elif t == Material.Type.TRIM:
            TrimDetail.objects.create(
                material=material,
                trim_type=cd["trim_type"],
                size=cd.get("trim_size", ""),
                color=cd.get("trim_color", ""),
                brand=cd.get("brand", ""),
            )

        return material