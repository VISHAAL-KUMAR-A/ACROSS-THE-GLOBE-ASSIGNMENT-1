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
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
