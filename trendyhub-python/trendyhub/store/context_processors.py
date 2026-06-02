def user_context(request):
    if request.user.is_authenticated:
        role = getattr(getattr(request.user, "profile", None), "role", "CUSTOMER")
        return {
            "logged_in_user": request.user,
            "logged_in_role": role,
        }

    return {
        "logged_in_user": None,
        "logged_in_role": None,
    }
