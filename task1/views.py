from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UserProfile, Patient, Doctor, BlogPost

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
