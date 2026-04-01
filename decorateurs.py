from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def check_role(role):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.role != role:
                messages.error(request, "Vous n'avez pas les droits nécessaires pour accéder à cette page")
                return redirect('frontend:accueil')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
