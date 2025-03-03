from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index_view, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('my-blog/', views.my_blog, name='my_blog'),
    path('all-posts/', views.all_posts, name='all_posts'),
    path('blog/<int:post_id>/', views.blog_detail, name='blog_detail'),
    path('blog/<int:post_id>/edit/', views.edit_blog, name='edit_blog'),
    path('all-doctors/', views.all_doctors, name='all_doctors'),
    path('book-appointment/', views.book_appointment, name='book_appointment'),
    path('my-appointments/', views.my_appointments, name='my_appointments'),
    path('doctor-appointments/', views.doctor_appointments,
         name='doctor_appointments'),
    path('cancel-appointment/<int:appointment_id>/',
         views.cancel_appointment, name='cancel_appointment'),
    path('confirm-appointment/<int:appointment_id>/',
         views.confirm_appointment, name='confirm_appointment'),
    path('reject-appointment/<int:appointment_id>/',
         views.reject_appointment, name='reject_appointment'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
