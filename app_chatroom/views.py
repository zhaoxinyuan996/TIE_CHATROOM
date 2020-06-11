import json
import time
import traceback

from threading import Thread
from collections import deque

# Create your views here.
from django.http import HttpResponse

from libs import myLog
from TIE.settings import WordsQueueConf
from app_chatroom.models import ChatUser, CustomCliMsgError, loop_check_disconnect, CustomSerDisconnect

# TODO:多个聊天室后期实现，大概会做一个初次信息判定，初次判定时 用户资料（昵称和ip）会被整合至request请求
# 用户池
sessionSet = dict()
wordsQueue = deque(maxlen=WordsQueueConf.maxLenth)

Thread(target=loop_check_disconnect, args=(sessionSet, )).start()

def _all_user_send(m: (str, bytes), q: dict) -> None:
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
    if msg:
        myLog.debug(msg)

        if isinstance(msg, bytes):
            msg = msg.decode()
        try: msg = json.loads(msg)
        except: return
        msg['type'] = 'usermsg'

        _all_user_send(json.dumps(msg), sessionSet)

# 离开
def _leave(obj: ChatUser) -> None:
    msg = '%s 离开' % obj.ip
    myLog.debug(msg)

    msg = {"message": msg, "type": "system"}
    _all_user_send(msg, sessionSet)


# VIEWS

def cli_accept(request) -> HttpResponse:
    '''客户端总处理函数'''
    if request.META.get('HTTP_SEC_WEBSOCKET_VERSION') and request.META['HTTP_SEC_WEBSOCKET_VERSION'] == '13':
        cliSocket = ChatUser(request)
        # 加入
        _join(cliSocket)
        sessionSet[cliSocket] = time.time()

        try:
            while not cliSocket.can_read():
                msg = cliSocket.read()
                # 校验合法
                if cliSocket.check_syntax(msg):
                    _speak(msg)

        except CustomCliMsgError:       # 客户端主动断连
            _leave(cliSocket)
            del sessionSet[cliSocket]
            myLog.debug(CustomCliMsgError)

        except CustomSerDisconnect:     # 超时未发言强制断连
            _leave(cliSocket)
            del sessionSet[cliSocket]
            myLog.debug(CustomSerDisconnect)

        except UnicodeDecodeError:
            myLog.warning(traceback.format_exc())

        except:                         # 其他错误
            myLog.error(traceback.format_exc())
            _leave(cliSocket)
            del sessionSet[cliSocket]


    return HttpResponse('FORCE EXIT')

def test(request):
    print(sessionSet)

    return HttpResponse("OK")