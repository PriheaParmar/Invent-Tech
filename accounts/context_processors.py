from .models import Firm, UserExtra

def firm_and_role_context(request):
    if not request.user.is_authenticated:
        return {}

    current_firm = Firm.objects.filter(owner=request.user).first()
    current_user_extra = UserExtra.objects.filter(user=request.user).first()

    firm_type_choices = []
    try:
        firm_type_choices = Firm._meta.get_field("firm_type").choices
    except Exception:
        pass

    role_choices = []
    current_role = ""
    try:
        role_choices = UserExtra.Role.choices
        current_role = request.user.userextra.role
    except Exception:
        pass

    return {
        "current_firm": current_firm,
        "current_user_extra": current_user_extra,
        "FIRM_TYPE_CHOICES": firm_type_choices,
        "ROLE_CHOICES": role_choices,
        "CURRENT_ROLE": current_role,
    }

def firm_context(request):
    if request.user.is_authenticated:
        firm = Firm.objects.filter(owner=request.user).first()
    else:
        firm = None
    return {"current_firm": firm}