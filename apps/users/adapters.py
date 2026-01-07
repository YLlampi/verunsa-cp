# apps/users/adapters.py
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.forms import ValidationError
from django.urls import reverse
from django.shortcuts import resolve_url


class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = sociallogin.user.email

        if not email or not email.endswith('@unsa.edu.pe'):
            messages.error(
                request,
                "Acceso denegado: Solo se permite el ingreso con correo institucional (@unsa.edu.pe)."
            )

            # redirigimos al login
            raise ImmediateHttpResponse(redirect('/accounts/google/login/'))

    def is_open_for_signup(self, request, sociallogin):
        return True
        # Test
        # email = sociallogin.user.email
        # allowed_domains = ('@unsa.edu.pe',)
        # if not email or not email.endswith(allowed_domains):
        #     return False
        # return True
        # End Test

        # email = sociallogin.user.email
        # if not email.endswith('@unsa.edu.pe'):
        #     return False
        # return True

    def authentication_error(self, request, provider_id, error=None, exception=None, extra_context=None):
        pass


class MyAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        user = request.user

        if not user.escuela or not user.codigo_alumno or not user.celular:
            return resolve_url('frontend:onboarding')

        return resolve_url('frontend:dashboard')
