from django.urls import path
from . import views


urlpatterns = [
    path('', views.chatbot_view, name='chat'),
    path("get_file_content/", views.get_file_content, name="get_file_content"),
]