import os
import platform


if 'win' in platform.system().lower():
     with open(os.path.join(os.path.dirname(__file__), os.path.pardir, 'secret.txt'),
               encoding='utf-8-sig') as f:
         exec(f.read())
else:
    with open('/home/admin/secret.txt') as f:
        exec(f.read())

class Secret:
    print('Secret模块加载')
    dbPassWord = dbPassWord
    salt = salt
    rUrl = rUrl
    rHost = rHost

if __name__ == '__main__':

    for i in Secret.__dict__:
        print(i, Secret.__dict__[i])