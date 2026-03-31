from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Message

User = get_user_model()  # this ensures we always use core.User

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["subject", "body"]

class ContactForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["subject", "body"]

class CustomUserCreationForm(UserCreationForm):
    full_name = forms.CharField(
        max_length=150,
        required=True,
        label="Full Name",
        widget=forms.TextInput(attrs={"placeholder": "Enter your full name"})
    )

    id_number = forms.CharField(
        max_length=50,
        required=True,
        label="National ID / Passport",
        widget=forms.TextInput(attrs={"placeholder": "Enter your ID number"})
    )

    class Meta:
        model = User
        fields = ("full_name", "id_number", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        # Map custom fields into your custom User model
        user.username = self.cleaned_data["full_name"]
        user.email = self.cleaned_data["id_number"]  # using email field to store ID for now
        if commit:
            user.save()
        return user
class PasswordRecoveryForm(forms.Form):
    id_copy = forms.FileField(required=True, label="Upload ID Copy")
    mobile_number = forms.CharField(max_length=15, label="Mobile Number")
    email = forms.EmailField(label="Email Address")

