from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User, Profile, DoctorProfile, PatientProfile, AmbulanceStaffProfile

class PatientRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-medical-green focus:border-medical-green transition duration-300',
            'placeholder': 'Enter your password'
        }),
        label="Password",
        help_text="Password must be at least 8 characters long"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-medical-green focus:border-medical-green transition duration-300',
            'placeholder': 'Confirm your password'
        }),
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-medical-green focus:border-medical-green transition duration-300',
                'placeholder': 'Choose a username'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-medical-green focus:border-medical-green transition duration-300',
                'placeholder': 'Enter your first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-medical-green focus:border-medical-green transition duration-300',
                'placeholder': 'Enter your last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-medical-green focus:border-medical-green transition duration-300',
                'placeholder': 'Enter your email address'
            }),
        }
        labels = {
            'username': 'Username',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email Address',
        }

    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError('Passwords don\'t match.')
        return cd['password2']

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already exists. Please choose a different one.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already registered. Please use a different email address.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = User.Role.PATIENT
        if commit:
            user.save()
        return user

class StaffRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-medical-blue focus:border-medical-blue transition duration-300',
            'placeholder': 'Enter your password'
        }),
        label="Password",
        help_text="Password must be at least 8 characters long"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-medical-blue focus:border-medical-blue transition duration-300',
            'placeholder': 'Confirm your password'
        }),
        label="Confirm Password"
    )
    role = forms.ChoiceField(
        choices=[(User.Role.DOCTOR, "Doctor"), (User.Role.AMBULANCE_STAFF, "Ambulance Staff")],
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-medical-blue focus:border-medical-blue transition duration-300'
        }),
        label="Staff Role"
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'role')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-medical-blue focus:border-medical-blue transition duration-300',
                'placeholder': 'Choose a username'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-medical-blue focus:border-medical-blue transition duration-300',
                'placeholder': 'Enter your first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-medical-blue focus:border-medical-blue transition duration-300',
                'placeholder': 'Enter your last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-medical-blue focus:border-medical-blue transition duration-300',
                'placeholder': 'Enter your email address'
            }),
        }
        labels = {
            'username': 'Username',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email Address',
        }

    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError('Passwords don\'t match.')
        return cd['password2']

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already exists. Please choose a different one.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already registered. Please use a different email address.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = self.cleaned_data["role"]
        user.is_active = False # Staff must verify email first
        user.is_verified = False # Staff must be approved by admin
        if commit:
            user.save()
        return user

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('address', 'phone_number', 'profile_picture')

class DoctorProfileForm(forms.ModelForm):
    class Meta:
        model = DoctorProfile
        fields = ('license_number', 'primary_specialty', 'primary_hospital')

class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        fields = ('date_of_birth', 'gender')

class AmbulanceStaffProfileForm(forms.ModelForm):
    class Meta:
        model = AmbulanceStaffProfile
        fields = ('employee_id', 'driver_license')


class CustomLoginForm(AuthenticationForm):
    """Enhanced login form with professional styling and placeholders"""

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 pl-11 pr-11 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200 bg-white placeholder-gray-400',
            'placeholder': 'Enter your username or email address',
            'autocomplete': 'username',
            'autofocus': True
        }),
        label="Username or Email"
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 pl-11 pr-11 border-2 border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200 bg-white placeholder-gray-400',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password'
        }),
        label="Password"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove help text
        for field in self.fields.values():
            field.help_text = None

        # Add custom error messages
        self.fields['username'].error_messages = {
            'required': 'Please enter your username or email address.',
        }
        self.fields['password'].error_messages = {
            'required': 'Please enter your password.',
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Allow login with email or username
            if '@' in username:
                # Try to find user by email
                try:
                    user = User.objects.get(email=username)
                    return user.username
                except User.DoesNotExist:
                    pass
        return username