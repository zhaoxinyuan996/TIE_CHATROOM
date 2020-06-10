import base64
import hashlib
import json
import time
import random
import socket

from collections import deque
from django.http import HttpResponse
from django.shortcuts import render
# Create your views here.
from dwebsocket.decorators import require_websocket, accept_websocket
from libs import logger
from TIE.settings import WordsQueueConf
from app_chatroom.models import ChatUser
from tools.thesaurus import wordsFilterTool

# TODO:多个聊天室后期实现，大概会做一个初次信息判定，初次判定时 用户资料（昵称和ip）会被整合至request请求
sessionSet = set()
wordsQueue = deque(maxlen=WordsQueueConf.maxLenth)

def _all_user_send(m: (str, bytes), q: set) -> None:
    '''m:消息;q:用户池'''
    if not m or not q: return

    if isinstance(m, str):
        m = m.encode()

    for i in q:
        i.websocket.send(m)

# 加入
def _join(request: object) -> None:
    msg = '%s 加入' % request
    logger.debug(msg)
    _all_user_send(msg, sessionSet)
    sessionSet.add(request)

# 发言
def _speak(msg: str, request: object) -> None:
    logger.debug(msg)
    if msg:
        code, words = wordsFilterTool.deal(msg, request)
        if code: _all_user_send(msg, sessionSet)

# 离开
def _leave(request: object) -> None:
    sessionSet.remove(request)
    msg = '%s 离开' % request
    logger.debug(msg)
    _all_user_send(msg, sessionSet)


def _get_wsgi_sock(request):
    if 'gunicorn.socket' in request.META:
        sock = request.META['gunicorn.socket']
    else:
        wsgi_input = request.META['wsgi.input']
        if hasattr(wsgi_input, '_sock'):
            sock = wsgi_input._sock
        elif hasattr(wsgi_input, 'rfile'):  # gevent
            if hasattr(wsgi_input.rfile, '_sock'):
                sock = wsgi_input.rfile._sock
            else:
                sock = wsgi_input.rfile.raw._sock
        elif hasattr(wsgi_input, 'raw'):
            sock = wsgi_input.raw._sock
        elif hasattr(wsgi_input, 'stream') and hasattr(wsgi_input.stream, 'raw'):
            sock = wsgi_input.stream.raw._sock
        else:
            raise ValueError('Socket not found in wsgi.input')
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    return sock

l = []
random.choice('abcdefghijklmnopqrstuvwxyz!@#$%^&*()')

accept_header = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Accept: %s\r\n"
            )


def compute_accept_value(key):
    """Computes the value for the Sec-WebSocket-Accept header,
    given the value for Sec-WebSocket-Key.
    """
    sha1 = hashlib.sha1()
    sha1.update(key.encode())
    sha1.update(b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11")  # Magic value
    return base64.b64encode(sha1.digest())

@accept_websocket
def cli_accept(request) -> HttpResponse:
    '''客户端总处理函数'''
    h = request.META['HTTP_SEC_WEBSOCKET_KEY']
    cliSocket = _get_wsgi_sock(request)
    l.append(cliSocket)
    k = compute_accept_value(h)
    s = accept_header % k.decode().encode()
    if isinstance(s, str): s = s.encode()
    cliSocket.send(s)
    while True:
        print('send')
        cliSocket.send(b'111')
        break



    # if request.is_websocket():
    #
    #
    #     _join(request)
    #
    #     while True:
    #         msg = request.websocket.wait()
    #
    #         if request.websocket.is_closed():
    #             _leave(request)
    #             return HttpResponse(b'CLIENT LEAVE')
    #
    #         _speak(msg, request)
    #
    # return HttpResponse(b'FORCED EXIT')


