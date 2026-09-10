from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

def role_required(*roles):
    """
    Decorator untuk membatasi akses berdasarkan role.
    Contoh: @role_required("ADMIN", "GUDANG")
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            # Superuser selalu boleh akses
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            user_role = getattr(request.user, "role", "ADMIN")

            if user_role in roles:
                return view_func(request, *args, **kwargs)

            messages.error(request, "Anda tidak memiliki akses ke halaman ini.")
            return redirect("dashboard")
        return _wrapped
    return decorator