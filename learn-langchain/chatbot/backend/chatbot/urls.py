from django.urls import path

from . import views

urlpatterns = [
    path("helloworld", views.helloworld, name="helloworld"),
    path("conversation", views.conversation, name="conversation"),
    path("stream-conversation", views.stream_conversation, name="stream_conversation"),
    path('stream', views.stream_text, name='stream'),
    path("bedrock-conversation", views.bedrock_conversation, name="bedrock_conversation"),
]