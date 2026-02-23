from .models import Firm, UserExtra

def firm_and_role_context(request):
    if not request.user.is_authenticated:
        return {}

    current_firm = Firm.objects.filter(owner=request.user).first()

    # choices pulled from model fields (config-based)
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
        "FIRM_TYPE_CHOICES": firm_type_choices,
        "ROLE_CHOICES": role_choices,
        "CURRENT_ROLE": current_role,
    }
