from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserCreationForm,
    PasswordChangeForm
)
from django.contrib.auth import get_user_model

from core.models import CustomUser

User = get_user_model()

class LoginForm(AuthenticationForm):

    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Masukkan Username"
        })
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Masukkan Password"
        })
    )


class RegisterForm(UserCreationForm):

    first_name = forms.CharField(
        label="Nama Lengkap",
        widget=forms.TextInput(attrs={
            "class": "form-control"
        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-control"
        })
    )

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control"
        })
    )

    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control"
        })
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control"
        })
    )

    class Meta:
        model = User
        fields = (
            "first_name",
            "email",
            "username",
            "password1",
            "password2",
        )


class ChangePasswordForm(PasswordChangeForm):

    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control"
        })
    )

    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control"
        })
    )

    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control"
        })
    )

    from .models import CustomUser


class ProfileForm(forms.ModelForm):

    class Meta:
        model = CustomUser

        fields = [
            "foto_profil",
            "first_name",
            "email",
            "no_hp",
            "alamat",
            "jabatan",
            "tanggal_lahir",
        ]

        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "no_hp": forms.TextInput(attrs={"class": "form-control"}),
            "alamat": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "jabatan": forms.TextInput(attrs={"class": "form-control"}),
            "tanggal_lahir": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date"
                }
            ),
        }