import jwt
import time
import base64
import hmac

from jwt import ExpiredSignatureError

from TIE.settings import JWT
from libs.secret import Secret
from libs.logger import logger


def gen_token(key: str, expire=3600) -> str:
    '''生成token'''
    tsStr = str(time.time() + expire)
    tsByte = tsStr.encode("utf-8")

    sha1Tshexstr = hmac.new(key.encode("utf-8"), tsByte, 'sha1').hexdigest()
    token = tsStr + ':' + sha1Tshexstr
    b64Token = base64.urlsafe_b64encode(token.encode("utf-8"))

    return b64Token.decode("utf-8")

def certify_token(key: str, token: str) -> bool:
    '''验证token'''
    try:
        tokenStr = base64.urlsafe_b64decode(token).decode('utf-8')

        tsStr, knownSha1Tsstr = tokenStr.split(':')
        if float(tsStr) < time.time():
            return False

        sha1 = hmac.new(key.encode("utf-8"),tsStr.encode('utf-8'),'sha1')
        calcSha1Tsstr = sha1.hexdigest()
        if calcSha1Tsstr != knownSha1Tsstr:
            return False

        return True
    except Exception as e:
        logger.warning('tocken check error, key is %s, token is %s; e is %s' % (key, token, e))
        return False

def gen_jwt(payload: dict) -> str:
    '''生成jwt'''
    t = time.time()
    payload.update({'iat': t})
    payload.update({'exp': t + JWT.exp})
    headers = {
        'alg': "HS256",
        'typ': 'JWT'
    }

    jwt_token = jwt.encode(payload,                 # payload
                           Secret.salt,             # 盐
                           algorithm=JWT.method,    # 加密算法
                           headers=headers          # header
                           ).decode()

    return jwt_token

def parse_jwt(jwt_token: str) -> tuple:
    '''解析jwt'''
    try:
        data = jwt.decode(jwt_token,                # jwt
                          Secret.salt,              # 盐
                          algorithms=[JWT.method])  # 加密算法
        return (0, data)

    except ExpiredSignatureError as e:
         return (1, str(e))

    except Exception as e:
        return (2, str(e))



if __name__ == '__main__':

    res = gen_jwt({'1':'11'})
    print(res)

    res = parse_jwt(res)
    print(res)