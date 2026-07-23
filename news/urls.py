from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('analisis/', views.AnalisisView.as_view(), name='analisis'),
    path('trigger-fetch/', views.TriggerFetchView.as_view(), name='trigger_fetch'),
]