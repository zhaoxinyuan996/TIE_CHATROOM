import array
import select
import struct

import six
import socket

from TIE.settings import ChatUserConf, WordsQueueConf

# 用户类
class ChatUser():

    __slots__ = ('ip', 'level', 'speakTimes', '_levelTable')

    def __init__(self, ip: str) -> None:
        self.ip = ip
        self.level = 0
        self.speakTimes = 0
        self._levelTable = ChatUserConf.levelTable_speak

    def __getattr__(self, item: str) -> None:
        return None

    def speak(self, words: str) -> tuple:
        self.speakTimes += 1
        if self.speakTimes in self._levelTable:
            self.level = self._levelTable.index(self.speakTimes)
            return words, self.level

        return words, None

class SocketPool():
    def __init__(self, sock):
        self.sock = sock
        self.pool = {}

    @classmethod
    def mask_or_unmask(cls, mask, data):
        """Websocket masking function.
        `mask` is a `bytes` object of length 4; `data` is a `bytes` object of any length.
        Returns a `bytes` object of the same length as `data` with the mask applied
        as specified in section 5.3 of RFC 6455.
        This pure-python implementation may be replaced by an optimized version when available.
        """
        mask = array.array("B", mask)
        unmasked = array.array("B", data)
        for i in range(len(data)):
            unmasked[i] = unmasked[i] ^ mask[i % 4]
        if hasattr(unmasked, 'tobytes'):
            # tostring was deprecated in py32.  It hasn't been removed,
            # but since we turn on deprecation warnings in our tests
            # we need to use the right one.
            return unmasked.tobytes()
        else:
            return unmasked.tostring()

    def _read_strict(self, bufsize):
        remaining = bufsize
        _bytes = b""
        while remaining:
            _buffer = self.sock.recv(remaining)
            if not _buffer:
                raise socket.error(socket.EBADF, 'Bad file descriptor')
            _bytes += _buffer
            remaining = bufsize - len(_bytes)
        return _bytes

    def read_frame(self):
        """
        recieve data as frame from server.
        """
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
            data = self.mask_or_unmask(mask_key, data)
        return fin, opcode, data

    def can_read(self, timeout=0.0):
        '''
        Return ``True`` if new data can be read from the socket.
        '''
        r, w, e = [self.sock], [], []
        try:
            r, w, e = select.select(r, w, e, timeout)
        except select.error as err:
            if err.args[0] == 4:
                return False
            self.sock.close()
        return self.sock in r
