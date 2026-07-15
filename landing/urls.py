from django.urls import path
from . import views

app_name = "landing"

urlpatterns = [
    path("", views.home, name="home"),
    path("contact/", views.submit_contact, name="contact"),
    path("demo/voice/", views.demo_voice, name="demo_voice"),
    path("demo/chat/", views.demo_chat, name="demo_chat"),
]
