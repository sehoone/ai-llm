from django.urls import path

from . import views

urlpatterns = [
    path("helloworld", views.helloworld, name="helloworld"),
    path("conversation", views.conversation, name="conversation"),
]