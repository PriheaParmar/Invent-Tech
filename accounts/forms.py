from django import forms
from .models import Jobber, JobberType

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