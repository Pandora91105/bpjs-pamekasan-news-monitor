from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('review/', views.ReviewView.as_view(), name='review'),
    path('review/<int:pk>/approve/', views.ApproveNewsView.as_view(), name='approve_news'),
    path('review/<int:pk>/reject/', views.RejectNewsView.as_view(), name='reject_news'),
    path('analisis/', views.AnalisisView.as_view(), name='analisis'),
]