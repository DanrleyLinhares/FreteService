from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),  # Esta URL corresponde à sua view index
]
