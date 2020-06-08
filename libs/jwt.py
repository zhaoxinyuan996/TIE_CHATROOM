import time
import base64
import hmac

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


if __name__ == '__main__':
    userName = 'zhaoxinyuan'
    token = gen_token(userName)
    print(token)

    res = certify_token(userName, token)
    print(res)