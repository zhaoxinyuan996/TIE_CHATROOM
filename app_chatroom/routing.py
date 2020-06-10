from django.urls import path
from . import consumers


websocket_urlpatterns = [
    path('ws/chat', consumers.Chatting), #consumers.Chatting 是该路由的消费者
]