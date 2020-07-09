import os
import six
import time
import json
import array
import base64
import select
import struct
import socket
import hashlib

from collections import deque
from functools import partial

from libs import myLog
from libs.cls import BaseError
from tools.thesaurus import wordsFilterTool, hostFilterTool
from TIE.settings import ChatUserConf, ChatUserPoolConf, ChatRoomPoolConf, WordsQueueConf

wordsQueue = partial(deque, maxlen=WordsQueueConf.maxLenth)

accept_header = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Accept: %s\r\n"
            "\r\n"
            )

# 子线程定时踢出
def loop_check_disconnect(chatRoomPool:dict):
    while True:
        try:
            t = time.time()
            for key in chatRoomPool:
                for j in chatRoomPool[key][0]:
                    if t - j.lastAvtive > ChatUserPoolConf.timeout:
                        j.close()

            time.sleep(ChatUserPoolConf.loolTime)
        except Exception as e:
            myLog.error(e)

# 客户端字段非法
class CustomHackMsgError(BaseError): pass

# 客户端用户名非法
class CustomCliNameError(BaseError): pass

# 聊天室人数已满
class CustomUserOverLimit(BaseError): pass

# 客户端名字重名
class CustomCliNameSameError(BaseError): pass

# 客户端聊天室非法
class CustomCliChatroomNameError(BaseError): pass

# 客户端声明断连
class CustomCliMsgError(BaseError): pass

# 超时未发言服务器主动断连
class CustomSerDisconnect(BaseError): pass

# 聊天室用户类
class ChatUser:
    def __init__(self, request, cPool) -> None:

        self.lvS = 0
        self.lvU = 0
        self._sTimes = 0
        self._uTimes = 0
        self.lastAvtive = 0
        self._r = cPool.keys()
        self.request = request
        self.chatPool = cPool
        self.ip = self.get_ip(self.request)
        self._levelTableS = ChatUserConf.levelTableS
        self._levelTableU = ChatUserConf.levelTableU
        self.sock = self._get_wsgi_sock(request)

        # check
        self.roomNum = self._check_chatroom_num()
        self.name = self._check_name(request.GET.get('name'))

        self._handshake()

        del self._r

    def __getattr__(self, item: str) -> None:
        myLog.error('attr "%s" not exist' % item)
        return None

    @staticmethod
    def get_ip(request) -> str:
        if 'HTTP_X_FORWARDED_FOR' in request.META:
            ip = request.META['HTTP_X_FORWARDED_FOR']
        else:
            ip = request.META['REMOTE_ADDR']
        return ip

    def _check_chatroom_num(self) -> str:
        if self.request.GET.get('roomName') in self._r:
            return self.request.GET.get('roomName')
        raise CustomCliChatroomNameError

    def _check_name(self, name: str) -> str:
        if not name:
            raise CustomCliNameError

        if len(self.chatPool[self.roomNum][0]) >= ChatRoomPoolConf.userNumLimit:
            raise CustomUserOverLimit

        # 空间和时间哪个重要
        name = name.replace(' ', '')
        if name in (i.name for i in self.chatPool[self.roomNum][0]):
            raise CustomCliNameSameError

        code, msg = wordsFilterTool.deal(name, userInfo=self.ip)

        if code: return name
        raise CustomCliNameError

    def speak_exp(self) -> None:
        self._sTimes += 1
        if self._sTimes in self._levelTableS:
            self.lvS = self._levelTableS.index(self._sTimes)

    def thumbs_up_exp(self) -> None:
        self._uTimes += 1
        if self._uTimes in self._levelTableU:
            self.lvU = self._levelTableU.index(self._uTimes)

    def _handshake(self) -> None:
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
                raise CustomSerDisconnect('%s 超时' % self.ip)
            _bytes += _buffer
            remaining = bufsize - len(_bytes)
        return _bytes

    def check_syntax(self, msg: bytes) -> bool:
        if msg == b'\x03\xe9':                                             # 断连信号
            raise CustomCliMsgError('%s 断连' % self.ip)

        if b'Masked frame from server' in msg:                             # 忘了，解码出错
            return False

        if time.time() - self.lastAvtive < ChatUserConf.legalSpeakTime:    # 发言间隔太短
            return False

         # TODO 这里需要再加140字校验

        code, msg = hostFilterTool.deal(msg, userInfo=self.ip)
        if not code:                                                       # 包含url相关
            self._write_frame(json.dumps({"message": msg, "type": "system"}).encode())
            return False

        code, msg = wordsFilterTool.deal(msg, userInfo=self.ip)
        if not code:                                                       # 包含违规词
            self._write_frame(json.dumps({"message": msg, "type": "system"}).encode())
            return False

        self.speak_exp()
        self.lastAvtive = time.time()
        return True



    def send(self, words: bytes) -> None:
        self._write_frame(words)

    def read(self) -> bytes:
        _, _, rec = self._read_frame()
        return rec

    def close(self) -> None:
        try:
            self.sock.shutdown(2)
            self.sock.close()
        except: pass

    def _read_frame(self) -> tuple:
        header_bytes = self._read_strict(2)
        b1 = header_bytes[0] if six.PY3 else ord(header_bytes[0])
        fin = b1 >> 7 & 1
        opcode = b1 & 0xf
        b2 = header_bytes[1] if six.PY3 else ord(header_bytes[1])
        mask = b2 >> 7 & 1
        length = b2 & 0x7f

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

    def can_read(self, timeout=0.0) -> bool:
        r, w, e = (self.sock,), (), ()
        try:
            r, w, e = select.select(r, w, e, timeout)
        except select.error as err:
            if err.args[0] == 4:
                return False
            self.close()
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
            self.close()

# 聊天室   {'编号':[[套接字1,套接字2], [聊天缓存池]]}
class ChatRoomPool(dict):
    def __init__(self, cName: tuple) -> None:
        for i in cName:
            self.add(i)
        super().__init__()

    def keys(self) -> list:
        return list(super().keys())

    def add(self, key: str) -> None:
        self[key] = [[], wordsQueue()]

    def clear(self, *keys: tuple) -> None:
        if not keys:
            keys = self.keys()

        for key in keys:
            self._release(*self[key])

    def _release(self, keys) -> None:
        myLog.info('释放聊天室，key is %s' % keys)
        for key in keys:
            self[key][1].clear()
        for key in keys:
            for i in self[key][0]:
                try: i.close()
                except: print('这里释放有问题')

chatRoomPool = ChatRoomPool(ChatRoomPoolConf.roomNames)


if __name__ == '__main__':

    s = '''全面、及时的新闻报道，Google 新闻为您汇集来自世界各地的新闻来源。
    国际新闻- BBC News 中文 - m › zhongwen › simp › world
    国际新闻. 头条新闻. Keyframe #2. 视频. 视频. '''

    def check(msg):
        code, msg = hostFilterTool.deal(msg)
        if not code:  #
            return False

        code, msg = wordsFilterTool.deal(msg)
        if not code:  #
            return False

        return True

    t = time.time()
    for i in range(10000):
        res = check(s)
    print(time.time() - t)