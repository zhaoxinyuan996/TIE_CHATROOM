import json
import traceback

from collections import deque

# Create your views here.
from libs import myLog
from TIE.settings import WordsQueueConf
from app_chatroom.models import ChatUser, ShortMsgError

# TODO:多个聊天室后期实现，大概会做一个初次信息判定，初次判定时 用户资料（昵称和ip）会被整合至request请求
sessionSet = set()
wordsQueue = deque(maxlen=WordsQueueConf.maxLenth)

def _all_user_send(m: (str, bytes), q: set) -> None:
    '''m:消息;q:用户池'''
    if not m or not q: return

    if isinstance(m, dict):
        m = json.dumps(m)

    if isinstance(m, str):
        m = m.encode()

    for i in q:
        i.send(m)

# 加入
def _join(obj: ChatUser) -> None:
    msg = '%s 加入' % obj.ip
    myLog.debug(msg)
    msg = {"message": msg, "type": "system"}

    _all_user_send(msg, sessionSet)

# 发言
def _speak(msg: (str, bytes)) -> None:
    myLog.debug(msg)

    if isinstance(msg, bytes):
        msg = msg.decode()
    msg = json.loads(msg)
    msg['type'] = 'usermsg'

    _all_user_send(json.dumps(msg), sessionSet)

# 离开
def _leave(obj: ChatUser) -> None:
    msg = '%s 离开' % obj.ip
    myLog.debug(msg)

    msg = {"message": msg, "type": "system"}
    _all_user_send(msg, sessionSet)

def cli_accept(request) -> None:
    '''客户端总处理函数'''
    cliSocket = ChatUser(request)
    # 加入
    _join(cliSocket)
    sessionSet.add(cliSocket)

    try:
        while not cliSocket.can_read():
            msg = cliSocket.read()
            # 校验合法
            if cliSocket.check_syntax(msg):
                _speak(msg)

    except ShortMsgError:
        # 离开
        _leave(cliSocket)
        sessionSet.remove(cliSocket)

    except:
        myLog.error(traceback.format_exc())
        _leave(cliSocket)
        sessionSet.remove(cliSocket)