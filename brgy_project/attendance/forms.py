# attendance/forms.py
from django import forms
from .models import Profile

class ProfileForm(forms.ModelForm):
    birthdate = forms.DateField(
        widget=forms.DateInput(format='%m/%d/%Y', attrs={'placeholder': 'MM/DD/YYYY'}),
        input_formats=['%m/%d/%Y', '%m-%d-%Y'],
    )

    class Meta:
        model = Profile
        fields = ['email', 'name']
