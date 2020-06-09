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
    if q:
        for i in q:
            i.websocket.send(m)


@accept_websocket
def cli_accept(request) -> HttpResponse:
    print(type(request))
    if request.is_websocket():

        # 加入
        msg = '%s 加入' % request
        _all_user_send(msg, sessionSet)
        sessionSet.add(request)

        while True:
            # 异步 阻塞 等待客户端发消息
            msg = request.websocket.wait()
            # 断连
            print(request.websocket.is_closed())
            if request.websocket.is_closed():
                sessionSet.remove(request)
                msg = '%s 离开' % request
                _all_user_send(msg, sessionSet)
                return HttpResponse(b'LOSS!')

            # 发言
            if msg:
                _all_user_send(msg, sessionSet)

    return HttpResponse(b'NO!')

