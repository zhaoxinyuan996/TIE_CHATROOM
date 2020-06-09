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