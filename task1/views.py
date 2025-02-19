from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UserProfile, Patient, Doctor

# Create your views here.


def register_view(request):
    if request.method == 'POST':
        # Get form data
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        # Validate passwords match
        if password1 != password2:
            messages.error(request, 'Passwords do not match')
            return redirect('register')

        # Check if username exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return redirect('register')

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=request.POST['first_name'],
            last_name=request.POST['last_name']
        )

        # Create user profile
        profile = UserProfile.objects.create(
            user=user,
            profile_picture=request.FILES['profile_picture'],
            address_line1=request.POST['address_line1'],
            city=request.POST['city'],
            state=request.POST['state'],
            pincode=request.POST['pincode'],
            user_type=request.POST['user_type']
        )

        # Create Patient or Doctor instance
        if profile.user_type == 'patient':
            Patient.objects.create(user_profile=profile)
        else:
            Doctor.objects.create(user_profile=profile)

        # Log the user in
        login(request, user)
        return redirect('index')

    return render(request, 'task1/register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            messages.error(request, 'Invalid username or password')
            return redirect('login')

    return render(request, 'task1/login.html')


@login_required
def index_view(request):
    return render(request, 'task1/index.html')
