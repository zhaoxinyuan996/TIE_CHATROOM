import json
import array
import base64
import hashlib
import os
import select
import struct

import six
import socket

from libs import myLog
from tools.thesaurus import wordsFilterTool
from TIE.settings import ChatUserConf, WordsQueueConf


accept_header = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Accept: %s\r\n"
            "\r\n"
            )

# 自定义，声明断连
class ShortMsgError(Exception): pass

class ChatUser():
    def __init__(self, request):
        if 'HTTP_X_FORWARDED_FOR' in request.META:
            self.ip = request.META['HTTP_X_FORWARDED_FOR']
        else:
            self.ip = request.META['REMOTE_ADDR']
        self.level = 0
        self.speakTimes = 0
        self._levelTable = ChatUserConf.levelTable_speak

        self.request = request
        self.sock = self._get_wsgi_sock(request)

        self.handshake()

    def __getattr__(self, item: str) -> None:
        return None

    def speak(self, words: str) -> tuple:
        self.speakTimes += 1
        if self.speakTimes in self._levelTable:
            self.level = self._levelTable.index(self.speakTimes)
            return words, self.level

        return words, None

    def handshake(self) -> None:
        k = self._compute_accept_value(self.request.META['HTTP_SEC_WEBSOCKET_KEY'])
        s = accept_header % k.decode()
        self.sock.send(s.encode())

    @staticmethod
    def _compute_accept_value(key: str) -> bytes:
        sha1 = hashlib.sha1()
        sha1.update(key.encode())
        sha1.update(b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11")  # Magic value
        return base64.b64encode(sha1.digest())

    def _get_wsgi_sock(self, request) -> socket:
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
    @staticmethod
    def _mask_or_unmask(mask: bytes, data: bytes) -> (str, bytes):
        mask = array.array("B", mask)
        unmasked = array.array("B", data)
        for i in range(len(data)):
            unmasked[i] = unmasked[i] ^ mask[i % 4]
        if hasattr(unmasked, 'tobytes'):
            return unmasked.tobytes()
        else:
            return unmasked.tostring()

    def _read_strict(self, bufsize: int) -> bytes:
        remaining = bufsize
        _bytes = b""
        while remaining:
            _buffer = self.sock.recv(remaining)
            if not _buffer:
                raise socket.error(socket.EBADF, 'Bad file descriptor')
            _bytes += _buffer
            remaining = bufsize - len(_bytes)
        return _bytes

    def check_syntax(self, msg: bytes) -> bool:
        if msg == b'\x03\xe9':
            raise ShortMsgError('%s 断连' % self.ip)

        code, msg = wordsFilterTool.deal(msg)
        if code:
            return True

        self._write_frame(msg)

    def send(self, words: bytes) -> None:
        self._write_frame(words)

    def read(self) -> bytes:
        _, _, rec = self._read_frame()
        return rec

    def _read_frame(self) -> tuple:
        header_bytes = self._read_strict(2)
        b1 = header_bytes[0] if six.PY3 else ord(header_bytes[0])
        fin = b1 >> 7 & 1
        opcode = b1 & 0xf
        b2 = header_bytes[1] if six.PY3 else ord(header_bytes[1])
        mask = b2 >> 7 & 1
        length = b2 & 0x7f

        length_data = ""
        if length == 0x7e:
            length_data = self._read_strict(2)
            length = struct.unpack("!H", length_data)[0]
        elif length == 0x7f:
            length_data = self._read_strict(8)
            length = struct.unpack("!Q", length_data)[0]
        mask_key = ""
        if mask:
            mask_key = self._read_strict(4)
        data = self._read_strict(length)
        if mask:
            data = self._mask_or_unmask(mask_key, data)
        return fin, opcode, data

    def can_read(self, timeout=0.0):
        r, w, e = [self.sock], [], []
        try:
            r, w, e = select.select(r, w, e, timeout)
        except select.error as err:
            if err.args[0] == 4:
                return False
            self.sock.close()
        return self.sock in r

    def _write_frame(self, data: bytes, fin=True, opcode=0x1) -> None:
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
            data = mask + self._mask_or_unmask(mask, data)
        if isinstance(data, six.text_type):
            data = data.encode('utf-8')
        frame += data
        try:
            self.sock.sendall(frame)
        except socket.error:
            self.sock.close()