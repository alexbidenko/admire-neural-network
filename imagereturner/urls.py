from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path("", views.return_image),
    path("tags", views.return_tags),
]