from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UserProfile, Patient, Doctor, BlogPost, Appointment
from django.utils import timezone
from datetime import datetime, timedelta
import json
from django.http import JsonResponse
from django.db.models import Q
from django.conf import settings
import os
import google.oauth2.credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Create your views here.


def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1 != password2:
            messages.error(request, 'Passwords do not match')
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return redirect('register')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=request.POST['first_name'],
            last_name=request.POST['last_name']
        )

        profile = UserProfile.objects.create(
            user=user,
            profile_picture=request.FILES['profile_picture'],
            address_line1=request.POST['address_line1'],
            city=request.POST['city'],
            state=request.POST['state'],
            pincode=request.POST['pincode'],
            user_type=request.POST['user_type']
        )

        if profile.user_type == 'patient':
            Patient.objects.create(user_profile=profile)
        else:
            Doctor.objects.create(user_profile=profile)

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


@login_required
def my_blog(request):
    if request.user.userprofile.user_type != 'doctor':
        return redirect('index')

    doctor = Doctor.objects.get(user_profile=request.user.userprofile)
    posts = BlogPost.objects.filter(doctor=doctor)

    if request.method == 'POST':
        title = request.POST['title']
        image = request.FILES['image']
        category = request.POST['category']
        summary = request.POST['summary']
        content = request.POST['content']
        is_draft = 'is_draft' in request.POST

        BlogPost.objects.create(
            doctor=doctor,
            title=title,
            image=image,
            category=category,
            summary=summary,
            content=content,
            is_draft=is_draft
        )
        return redirect('my_blog')

    return render(request, 'task1/blog.html', {'posts': posts, 'categories': BlogPost.CATEGORIES})


@login_required
def all_posts(request):
    if request.user.userprofile.user_type != 'patient':
        return redirect('index')

    category = request.GET.get('category', '')
    posts = BlogPost.objects.filter(is_draft=False)

    if category:
        posts = posts.filter(category=category)

    return render(request, 'task1/all_posts.html', {
        'posts': posts,
        'categories': BlogPost.CATEGORIES,
        'selected_category': category
    })


@login_required
def blog_detail(request, post_id):
    post = BlogPost.objects.get(pk=post_id)

    if post.is_draft and (
        request.user.userprofile.user_type != 'doctor' or
        post.doctor.user_profile.user != request.user
    ):
        return redirect('index')

    return render(request, 'task1/blog_detail.html', {'post': post})


@login_required
def edit_blog(request, post_id):
    post = BlogPost.objects.get(pk=post_id)
    if request.user.userprofile.user_type != 'doctor' or post.doctor.user_profile.user != request.user:
        return redirect('index')

    if request.method == 'POST':
        post.title = request.POST['title']
        if 'image' in request.FILES:
            post.image = request.FILES['image']
        post.category = request.POST['category']
        post.summary = request.POST['summary']
        post.content = request.POST['content']
        post.is_draft = 'is_draft' in request.POST
        post.save()
        return redirect('blog_detail', post_id=post.id)

    return render(request, 'task1/edit_blog.html', {
        'post': post,
        'categories': BlogPost.CATEGORIES
    })


@login_required
def all_doctors(request):
    if request.user.userprofile.user_type != 'patient':
        return redirect('index')

    doctors = Doctor.objects.all()
    context = {
        'doctors': doctors,
        'today_date': timezone.now().date()
    }
    return render(request, 'task1/all_doctors.html', context)


@login_required
def book_appointment(request):
    if request.method == 'POST' and request.user.userprofile.user_type == 'patient':
        doctor_id = request.POST.get('doctor_id')
        speciality = request.POST.get('speciality')
        appointment_date = request.POST.get('appointment_date')
        appointment_time = request.POST.get('appointment_time')

        try:
            doctor = Doctor.objects.get(id=doctor_id)
            patient = Patient.objects.get(
                user_profile=request.user.userprofile)

            # Parse date and time
            date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
            time_obj = datetime.strptime(appointment_time, '%H:%M').time()

            # Calculate end time (45 minutes later)
            start_datetime = datetime.combine(date_obj, time_obj)
            end_datetime = start_datetime + timedelta(minutes=45)
            end_time = end_datetime.time()

            # Check for overlapping appointments for the doctor
            doctor_appointments = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=date_obj,
                status__in=['pending', 'confirmed']
            )

            for existing_appt in doctor_appointments:
                existing_start = datetime.combine(
                    existing_appt.appointment_date, existing_appt.appointment_time)
                existing_end = existing_start + timedelta(minutes=45)

                # Check if new appointment overlaps with existing one
                if (start_datetime < existing_end and end_datetime > existing_start):
                    messages.error(
                        request, 'This time slot is already booked. Please select a different time.')
                    return redirect('all_doctors')

            # Create appointment
            appointment = Appointment.objects.create(
                doctor=doctor,
                patient=patient,
                speciality=speciality,
                appointment_date=date_obj,
                appointment_time=time_obj,
                status='pending'
            )

            # Create Google Calendar event
            try:
                create_calendar_event(
                    doctor=doctor,
                    patient=patient,
                    appointment=appointment,
                    start_datetime=start_datetime,
                    end_datetime=end_datetime
                )
                messages.success(
                    request, 'Appointment booked successfully and added to doctor\'s calendar!')
            except Exception as e:
                messages.warning(
                    request, f'Appointment booked but calendar event creation failed: {str(e)}')

            return redirect('my_appointments')

        except Exception as e:
            messages.error(request, f'Error booking appointment: {str(e)}')
            return redirect('all_doctors')

    return redirect('all_doctors')


def create_calendar_event(doctor, patient, appointment, start_datetime, end_datetime):
    """Create a Google Calendar event for the doctor"""

    # Load credentials from the saved file
    creds = None
    token_path = os.path.join(settings.BASE_DIR, 'task1', 'google_token.json')

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_info(
            json.load(open(token_path)),
            ['https://www.googleapis.com/auth/calendar']
        )

    # If there are no valid credentials, we need to authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # For simplicity, we'll use a service account or pre-authenticated token
            # In a real app, you'd implement OAuth2 flow for the doctor
            raise Exception(
                "Calendar credentials not available. Please authenticate first.")

    # Build the service
    service = build('calendar', 'v3', credentials=creds)

    # Format the event
    patient_name = patient.user_profile.user.get_full_name()
    doctor_name = doctor.user_profile.user.get_full_name()

    event = {
        'summary': f'Appointment with {patient_name}',
        'location': 'Virtual Consultation',
        'description': f'Appointment for {speciality} consultation with {patient_name}. Duration: 45 minutes.',
        'start': {
            'dateTime': start_datetime.isoformat(),
            'timeZone': 'Asia/Kolkata',  # Adjust for your timezone
        },
        'end': {
            'dateTime': end_datetime.isoformat(),
            'timeZone': 'Asia/Kolkata',  # Adjust for your timezone
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 30},
            ],
        },
    }

    # Insert the event
    event = service.events().insert(calendarId='primary', body=event).execute()

    # Save the event ID to the appointment for future reference
    appointment.calendar_event_id = event.get('id')
    appointment.save()

    return event.get('id')


@login_required
def my_appointments(request):
    if request.user.userprofile.user_type != 'patient':
        return redirect('index')

    patient = Patient.objects.get(user_profile=request.user.userprofile)
    appointments = Appointment.objects.filter(patient=patient).order_by(
        'appointment_date', 'appointment_time')

    return render(request, 'task1/my_appointments.html', {'appointments': appointments})


@login_required
def cancel_appointment(request, appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id)

        # Check if the appointment belongs to the current user
        if appointment.patient.user_profile.user != request.user:
            messages.error(
                request, "You don't have permission to cancel this appointment.")
            return redirect('my_appointments')

        # Check if the appointment is pending
        if appointment.status != 'pending':
            messages.error(
                request, "Only pending appointments can be cancelled.")
            return redirect('my_appointments')

        # Delete the Google Calendar event if it exists
        if appointment.calendar_event_id:
            try:
                from .google_calendar import get_calendar_service
                service = get_calendar_service()
                service.events().delete(
                    calendarId='primary',
                    eventId=appointment.calendar_event_id
                ).execute()
            except Exception as e:
                messages.warning(
                    request, f"Could not delete calendar event: {str(e)}")

        appointment.status = 'cancelled'
        appointment.save()
        messages.success(request, "Appointment cancelled successfully.")

    except Appointment.DoesNotExist:
        messages.error(request, "Appointment not found.")

    return redirect('my_appointments')


@login_required
def doctor_appointments(request):
    if request.user.userprofile.user_type != 'doctor':
        return redirect('index')

    doctor = Doctor.objects.get(user_profile=request.user.userprofile)
    appointments = Appointment.objects.filter(doctor=doctor).order_by(
        'appointment_date', 'appointment_time')

    return render(request, 'task1/doctor_appointments.html', {'appointments': appointments})


@login_required
def confirm_appointment(request, appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id)

        # Check if the appointment belongs to the current doctor
        if appointment.doctor.user_profile.user != request.user:
            messages.error(
                request, "You don't have permission to confirm this appointment.")
            return redirect('doctor_appointments')

        # Check if the appointment is pending
        if appointment.status != 'pending':
            messages.error(
                request, "Only pending appointments can be confirmed.")
            return redirect('doctor_appointments')

        appointment.status = 'confirmed'
        appointment.save()
        messages.success(request, "Appointment confirmed successfully.")

    except Appointment.DoesNotExist:
        messages.error(request, "Appointment not found.")

    return redirect('doctor_appointments')


@login_required
def reject_appointment(request, appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id)

        # Check if the appointment belongs to the current doctor
        if appointment.doctor.user_profile.user != request.user:
            messages.error(
                request, "You don't have permission to reject this appointment.")
            return redirect('doctor_appointments')

        # Check if the appointment is pending
        if appointment.status != 'pending':
            messages.error(
                request, "Only pending appointments can be rejected.")
            return redirect('doctor_appointments')

        # Delete the Google Calendar event if it exists
        if appointment.calendar_event_id:
            try:
                from .google_calendar import get_calendar_service
                service = get_calendar_service()
                service.events().delete(
                    calendarId='primary',
                    eventId=appointment.calendar_event_id
                ).execute()
            except Exception as e:
                messages.warning(
                    request, f"Could not delete calendar event: {str(e)}")

        appointment.status = 'cancelled'
        appointment.save()
        messages.success(request, "Appointment rejected successfully.")

    except Appointment.DoesNotExist:
        messages.error(request, "Appointment not found.")

    return redirect('doctor_appointments')
