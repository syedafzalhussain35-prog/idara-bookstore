# store/forms.py
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
            'zip_code',
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
                'placeholder': 'Mobile Number (e.g. 9876543210)'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Full Shipping Address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'zip_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'PIN Code'
            }),
        }

    # ✅ Indian Mobile Validation
    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile', '').strip()
        pattern = r'^(\+91)?[6-9]\d{9}$'

        if not re.match(pattern, mobile):
            raise forms.ValidationError(
                "Enter a valid Indian mobile number"
            )
        return mobile

    # ✅ PIN Code Validation
    def clean_zip_code(self):
        zip_code = self.cleaned_data.get('zip_code', '').strip()

        if not re.match(r'^\d{6}$', zip_code):
            raise forms.ValidationError(
                "Enter a valid 6-digit PIN code"
            )
        return zip_code
