import json
import time

from queue import Queue


from django.http import HttpResponse
from django.shortcuts import render
from dwebsocket.decorators import require_websocket, accept_websocket
from django.core.handlers.wsgi import WSGIRequest
# Create your views here.

from app_chatroom.models import ChatUser

sessionSet = set()

def _all_user_send(m: (str, bytes), q: set) -> None:
    '''m:消息;q:用户池'''
    if not m: return
    if isinstance(m, str):
        m = m.encode()
    print('mmmmmmmmmmmm', m, type(m), sessionSet, q)
    if q:
        for i in q:
            i.websocket.send(m)


def _join(request):
    msg = '%s 加入' % request
    _all_user_send(msg, sessionSet)
    sessionSet.add(request)

def _speak(msg):
    if msg:
        _all_user_send(msg, sessionSet)

def _leave(request):
    sessionSet.remove(request)
    msg = '%s 离开' % request
    _all_user_send(msg, sessionSet)


@accept_websocket
def cli_accept(request):

    if request.is_websocket():

        # 加入
        _join(request)

        while True:
            # 异步 阻塞 等待客户端发消息
            msg = request.websocket.wait()
            # 断连
            if request.websocket.is_closed():
                _leave(request)
                return HttpResponse(b'LEAVE')
            # 发言
            _speak(msg)

    return HttpResponse(b'EXIT')


