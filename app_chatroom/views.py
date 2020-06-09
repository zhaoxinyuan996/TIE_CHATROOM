import json
import time

from collections import deque
from django.http import HttpResponse
from django.shortcuts import render
from dwebsocket.decorators import require_websocket, accept_websocket
# Create your views here.
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
    _all_user_send(msg, sessionSet)
    sessionSet.add(request)

# 发言
def _speak(msg: str, request: object) -> None:
    if msg:
        code, words = wordsFilterTool.deal(msg, request)
        if code:
            _all_user_send(msg, sessionSet)

# 离开
def _leave(request: object) -> None:
    sessionSet.remove(request)
    msg = '%s 离开' % request
    _all_user_send(msg, sessionSet)


@accept_websocket
def cli_accept(request) -> HttpResponse:
    '''客户端总处理函数'''
    if request.is_websocket():


        _join(request)

        while True:
            msg = request.websocket.wait()

            if request.websocket.is_closed():
                _leave(request)
                return HttpResponse(b'CLIENT LEAVE')

            _speak(msg, request)

    return HttpResponse(b'FORCED EXIT')


