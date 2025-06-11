from django.urls import path
from . import views


urlpatterns = [
    path('', views.chatbot_view, name='chat'),
    path('chat/', views.chatbot_response, name='chatbot_response'),
]