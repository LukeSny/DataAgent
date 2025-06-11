from django.urls import path
from . import views


urlpatterns = [
    path('', views.chatbot_view, name='chat'),
    path("get_file_content/", views.get_file_content, name="get_file_content"),
    path('clear_chat/', views.clear_chat_view, name='clear_chat'),
    path('reload_db/', views.reload_db, name='reload_db')
]