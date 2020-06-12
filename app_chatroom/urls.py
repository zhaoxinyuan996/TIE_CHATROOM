from django.conf.urls import url

from .views import *

urlpatterns = [
    url('chat', cli_accept),
    url('test', test),
    url('room_num', get_chatroom_num),
    url('online_num', get_online_num),
    url('chat_cache', get_chat_cache),
]