import re
from django import forms
from .models import Order


class CheckoutForm(forms.ModelForm):

    class Meta:
        model = Order
        fields = [
            'full_name',
            'email',
            'mobile',
            'address',
            'city',
            'zip_code'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address'
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Mobile Number (e.g. +91XXXXXXXXXX)'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Shipping Address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'zip_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Pin / Zip Code'
            }),
        }

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        pattern = r'^(\+91)?[6-9]\d{9}$'
        if not re.match(pattern, mobile):
            raise forms.ValidationError(
                "Enter a valid Indian mobile number"
            )
        return mobile
