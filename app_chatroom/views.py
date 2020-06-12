import json
import time
import traceback

from threading import Thread

# Create your views here.
from django.http import HttpResponse

from libs import myLog
from app_chatroom.models import ChatUser, CustomCliMsgError, loop_check_disconnect, CustomSerDisconnect, chatRoomPool, \
    CustomCliNameError, CustomCliChatroomNumError, ChatRoomPool

# TODO:多个聊天室，需要有一个分发函数


Thread(target=loop_check_disconnect, args=(chatRoomPool, )).start()

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
    msg = {"message": '%s 加入' % obj.ip, "type": "system", "time": time.time()}
    _all_user_send(msg, chatRoomPool[obj.roomNum][0])

    myLog.debug(msg)

# 发言
def _speak(obj:ChatUser, msg: (str, bytes)) -> None:
    if msg:
        myLog.debug(msg)

        if isinstance(msg, bytes):
            msg = msg.decode()
        try: msg = json.loads(msg)
        except: return
        msg['type'] = 'usermsg'
        msg['name'] = obj.name
        msg['time'] = time.time()

        _all_user_send(json.dumps(msg), chatRoomPool[obj.roomNum][0])
        _add_to_cache(obj.roomNum, msg)


# 离开
def _leave(obj: ChatUser, reason: Exception=None) -> None:
    msg = {"message": '%s 离开' % (obj.ip), "type": "system", "time": time.time()}
    _all_user_send(msg, chatRoomPool[obj.roomNum][0])

    msg['message'] += '%s' % reason
    myLog.debug(msg)

# 添加缓冲池
def _add_to_cache(roomNum: str, info: dict) -> None:
    chatRoomPool[roomNum][1].append(info)

# VIEWS

def cli_accept(request) -> HttpResponse:
    '''客户端总处理函数'''
    if request.META.get('HTTP_SEC_WEBSOCKET_VERSION') == '13':
        try:
            cliSocket = ChatUser(request)

        except CustomCliChatroomNumError as e:
            myLog.info(e)
            return HttpResponse(b'NO')

        except CustomCliNameError as e:
            myLog.info(e)
            return HttpResponse(b'NO')

        except:
            myLog.error('未捕捉错误, %s' % traceback.format_exc())
            return HttpResponse(b'NO')

        _join(cliSocket)
        chatRoomPool[cliSocket.roomNum][0][cliSocket] = time.time()

        try:
            while not cliSocket.can_read():
                msg = cliSocket.read()
                # 校验合法
                if cliSocket.check_syntax(msg):
                    _speak(cliSocket, msg)

        except CustomCliMsgError as e:          # 客户端主动断连
            _leave(cliSocket, e)
            del chatRoomPool[cliSocket.roomNum][0][cliSocket]

        except CustomSerDisconnect as e:        # 超时未发言强制断连
            _leave(cliSocket,e)
            del chatRoomPool[cliSocket.roomNum][0][cliSocket]
            myLog.debug(CustomSerDisconnect)

        except UnicodeDecodeError:
            myLog.warning(traceback.format_exc())

        except:                                 # 其他错误
            myLog.error('未捕捉错误2, %s' % traceback.format_exc())
            _leave(cliSocket)
            del chatRoomPool[cliSocket.roomNum][0][cliSocket]

    return HttpResponse(b'FORCE EXIT')

# 获取当前聊天室数
def get_chatroom_num(request):
    return HttpResponse(len(chatRoomPool))

# 获取指定聊天室同时在线人数，如果不指定则返回所有在线人数
def get_online_num(request):
    roomNum = request.GET.get('roomNum')
    if roomNum:
        if roomNum in chatRoomPool:
            return HttpResponse(len(chatRoomPool[roomNum][0]))
        return HttpResponse(b'NOT EXIST')
    num = 0
    for n in chatRoomPool:
        num += len(chatRoomPool[n][0])
    return HttpResponse(num)

# 获取缓存池
def get_chat_cache(request):
    roomNum = request.GET.get('roomNum')
    if roomNum:
        if roomNum in chatRoomPool:
            return HttpResponse(json.dumps(chatRoomPool[roomNum][1]).encode())

def test(request):
    print(chatRoomPool)

    return HttpResponse(b"OK")