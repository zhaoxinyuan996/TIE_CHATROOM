import base64
import hashlib
import json
import os
import struct
import time
import random
import socket
import array

from collections import deque

import six
from django.http import HttpResponse
from django.shortcuts import render
# Create your views here.
from dwebsocket.decorators import require_websocket, accept_websocket
from libs import logger
from TIE.settings import WordsQueueConf
from app_chatroom.models import ChatUser, SocketPool
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
            "\r\n"
            )


def compute_accept_value(key):
    sha1 = hashlib.sha1()
    sha1.update(key.encode())
    sha1.update(b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11")  # Magic value
    return base64.b64encode(sha1.digest())

def mask_or_unmask(mask, data):
    mask = array.array("B", mask)
    unmasked = array.array("B", data)
    for i in range(len(data)):
        unmasked[i] = unmasked[i] ^ mask[i % 4]
    if hasattr(unmasked, 'tobytes'):
        return unmasked.tobytes()
    else:
        return unmasked.tostring()
def _write_frame(sock, data, fin=True, opcode=0x1):
    mask_outgoing = False
    if fin:
        finbit = 0x80
    else:
        finbit = 0
    frame = struct.pack("B", finbit | opcode)
    l = len(data)
    if mask_outgoing:
        mask_bit = 0x80
    else:
        mask_bit = 0
    if l < 126:
        frame += struct.pack("B", l | mask_bit)
    elif l <= 0xFFFF:
        frame += struct.pack("!BH", 126 | mask_bit, l)
    else:
        frame += struct.pack("!BQ", 127 | mask_bit, l)
    if mask_outgoing:
        mask = os.urandom(4)
        data = mask + mask_or_unmask(mask, data)
    if isinstance(data, six.text_type):
        data = data.encode('utf-8')
    frame += data
    try:
        sock.sendall(frame)
        print('frame', frame)
    except socket.error:
        sock.close()

def _read_strict(sock, bufsize):
    remaining = bufsize
    _bytes = b""
    while remaining:
        _buffer = sock.recv(remaining)
        if not _buffer:
            raise socket.error(socket.EBADF, 'Bad file descriptor')
        _bytes += _buffer
        remaining = bufsize - len(_bytes)
    return _bytes

def read_frame(sock):
    """
    recieve data as frame from server.
    """
    header_bytes = _read_strict(sock, 2)
    b1 = header_bytes[0] if six.PY3 else ord(header_bytes[0])
    fin = b1 >> 7 & 1
    opcode = b1 & 0xf
    b2 = header_bytes[1] if six.PY3 else ord(header_bytes[1])
    mask = b2 >> 7 & 1
    length = b2 & 0x7f

    length_data = ""
    if length == 0x7e:
        length_data = _read_strict(sock, 2)
        length = struct.unpack("!H", length_data)[0]
    elif length == 0x7f:
        length_data = _read_strict(sock, 8)
        length = struct.unpack("!Q", length_data)[0]
    mask_key = ""
    if mask:
        mask_key = _read_strict(sock, 4)
    data = _read_strict(sock, length)
    if mask:
        data = mask_or_unmask(mask_key, data)
    return fin, opcode, data

# @accept_websocket
def cli_accept(request) -> HttpResponse:
    '''客户端总处理函数'''
    h = request.META['HTTP_SEC_WEBSOCKET_KEY']
    cliSocket = _get_wsgi_sock(request)
    l.append(cliSocket)
    k = compute_accept_value(h)
    s = accept_header % k.decode()


    if isinstance(s, str): s = s.encode()
    print(s)
    cliSocket.send(s)

    for i in range(5):
        pass
        print('send')
        _write_frame(cliSocket, b'{"message": "123", "type": "usermsg", "name": "123"}')
    mySock = SocketPool(cliSocket)
    while not mySock.can_read():
        _, _, res = read_frame(cliSocket)
        res = json.loads(res.decode())
        res['type'] = 'usermsg'
        res = json.dumps(res).encode()
        for i in l:
            print('遍历', i)
            _write_frame(i, res)