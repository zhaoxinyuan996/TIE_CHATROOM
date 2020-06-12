import json
import time
import traceback

from threading import Thread
from django.http import HttpResponse
# Create your views here.

from libs import myLog
from app_chatroom.models import ChatUser, CustomCliMsgError, loop_check_disconnect, CustomSerDisconnect, chatRoomPool, \
    CustomCliNameError, CustomCliChatroomNumError


# 目前参数
#   type
#   message
#   time
#   name
#   lvS
#   lvU

# 监控线程
Thread(target=loop_check_disconnect, args=(chatRoomPool, )).start()

def _get_static(obj: ChatUser=None, msg=None) -> dict:
    '''字典参数模板'''
    d = {
        'time': time.time(),
        'type': 'usermsg' if obj else 'system',
        'name': obj.name if obj else '系统消息',
        'lvS': obj.lvS if obj else '10',
        'lvU': obj.lvU if obj else '10',

        'message': msg,
    }
    return d

def _all_user_send(m: dict, q: dict) -> None:
    '''m:消息;q:用户池'''
    if not m or not q: return

    myLog.debug(m)
    m = json.dumps(m).encode()

    for i in q:
        i.send(m)

def _join(obj: ChatUser) -> None:
    '''加入，系统消息'''
    msg = _get_static()
    msg["message"] ='%s 加入' % obj.name
    _all_user_send(msg, chatRoomPool[obj.roomNum][0])

def _speak(obj:ChatUser, msg: (str, bytes)) -> None:
    '''发言，用户消息'''
    if isinstance(msg, bytes):
        msg = msg.decode()
    try: msg = json.loads(msg)
    except: return

    msg0 = _get_static(obj)
    msg0.update(msg)

    _all_user_send(msg0, chatRoomPool[obj.roomNum][0])
    _add_to_cache(obj.roomNum, msg0)
    obj.speak_exp()


def _leave(obj: ChatUser, reason: Exception=None) -> None:
    '''离开，系统消息'''
    msg = _get_static()
    msg["message"] = '%s 离开' % obj.name
    _all_user_send(msg, chatRoomPool[obj.roomNum][0])

    msg['message'] += '%s' % reason

def _add_to_cache(roomNum: str, info: dict) -> None:
    '''添加到缓存池'''
    chatRoomPool[roomNum][1].append(info)

# VIEWS

def cli_accept(request) -> HttpResponse:
    '''客户端总处理函数'''
    if request.META.get('HTTP_SEC_WEBSOCKET_VERSION') == '13':
        try:
            cliSocket = ChatUser(request, chatRoomPool.keys())

        except CustomCliChatroomNumError as e:                  # 客户端聊天室选择非法
            myLog.warning('%s, %s' % (e, ChatUser.get_ip(request)))
            return HttpResponse(b'ROOM NUMBER ERROR', status=403)

        except CustomCliNameError as e:                         # 客户端昵称非法
            myLog.warning('%s, %s' % (e, ChatUser.get_ip(request)))
            return HttpResponse(b'USERNAME ERROR', status=403)

        except:                                                 # 其他错误
            myLog.error('未捕捉错误, %s' % traceback.format_exc())
            return HttpResponse(b'UNKNOWN ERROR', status=403)

        _join(cliSocket)
        chatRoomPool[cliSocket.roomNum][0][cliSocket] = time.time()

        try:
            while not cliSocket.can_read():
                msg = cliSocket.read()
                # 校验合法
                if cliSocket.check_syntax(msg):
                    _speak(cliSocket, msg)

        except CustomCliMsgError as e:              # 客户端主动断连
            _leave(cliSocket, e)
            del chatRoomPool[cliSocket.roomNum][0][cliSocket]
            myLog.debug(CustomCliMsgError)

        except CustomSerDisconnect as e:            # 超时未发言强制断连
            _leave(cliSocket,e)
            del chatRoomPool[cliSocket.roomNum][0][cliSocket]
            myLog.debug(CustomSerDisconnect)

        except UnicodeDecodeError:                  # 解码错误
            myLog.warning(traceback.format_exc())

        except:                                     # 其他错误
            myLog.error('未捕捉错误2, %s' % traceback.format_exc())
            _leave(cliSocket)
            del chatRoomPool[cliSocket.roomNum][0][cliSocket]

    return HttpResponse(b'FORCE EXIT', status=403)


def get_chatroom_num(request):
    '''获取当前聊天室编号'''
    return HttpResponse(json.dumps(chatRoomPool.keys()))

def get_online_num(request):
    '''获取指定聊天室同时在线人数，如果不指定则返回所有在线人数'''
    roomNum = request.GET.get('roomNum')
    if roomNum:
        if roomNum in chatRoomPool:
            return HttpResponse(len(chatRoomPool[roomNum][0]))
        return HttpResponse(b'NOT EXIST', status=403)
    num = 0
    for n in chatRoomPool:
        num += len(chatRoomPool[n][0])
    return HttpResponse(json.dumps({'num': num}))

def get_chat_cache(request):
    '''获取缓存池'''
    roomNum = request.GET.get('roomNum')
    if roomNum:
        if roomNum in chatRoomPool:
            return HttpResponse(json.dumps(list(chatRoomPool[roomNum][1])).encode())
    return HttpResponse(b"NONE", status=403)

def test(request):
    print(chatRoomPool)

    return HttpResponse(b"OK")