import os
import gzip

from io import BytesIO
from datetime import datetime
from django.http.response import HttpResponse

from libs.static import contentTypeDic
from TIE.settings import StaticConf

# 这里放基类和公共方法


# 错误基类
class BaseError(Exception):
    def __init__(self, userObj, *args):
        super().__init__(*args)
        userObj.on_error(self.__class__.__name__)

    def __str__(self) -> str:
        return type(self).__name__ + (':' + (''.join(self.args)).__repr__() if self.args else '')


# 静态文件加载到内存
class StaticFile:
    def __init__(self):
        self.rootPath = StaticConf.hostPath
        self.replaceLen = os.path.abspath(os.path.join(self.rootPath, os.pardir)).__len__()
        self.fileDict = {}
        self.deal_file(self.rootPath)
        print('StaticFile模块加载')

    @staticmethod
    def last_file_time(mtime: float) -> str:
        t = datetime.fromtimestamp(mtime)
        t = t.strftime('%a, %d %b %Y %H:%M:%S GMT')
        return t

    def deal_file(self, file: str) -> None:
        for i in os.walk(file):
            if i[-1]:
                for j in i[-1]:
                    p = os.path.join(i[0], j)
                    self.write_cache(p, os.path.getmtime(p))

    def write_cache(self, absfile: str, modifytime: float) -> None:
        relativePath = os.path.abspath(absfile)[self.replaceLen:].replace('\\', '/')

        if relativePath.endswith('html'):
            relativePath = relativePath.replace('/static/', '')

        with open(absfile, 'rb') as f:
            res = f.read()
        f_gzip = BytesIO()
        gzip.open(f_gzip, 'wb').write(res)
        f_gzip = f_gzip.getvalue()
        self.fileDict[relativePath] = (res, f_gzip, self.last_file_time(modifytime))


# 添加http报文字段
def add_response_field(response: HttpResponse, **kwargs: dict) -> None:

    for k, v in kwargs.items():
        if k in StaticConf.allowKey:
            response._headers[k] = (k, v.__str__())


# 静态文件添加gzip压缩
def gzip_response(func):
    def f(*args):
        contentEncoding = args[0].META.get('HTTP_ACCEPT_ENCODING', '')
        fileUrl = args[0].META.get('PATH_INFO')

        if fileUrl not in g.fileDict:
            return HttpResponse('STATICFILE NOT EXIST', status=404)

        contentType = contentTypeDic.get(fileUrl.split('.')[-1], '*/*')

        if 'gzip' in contentEncoding:
            response = HttpResponse(g.fileDict[fileUrl][1], content_type=contentType)
            response._headers['Content-Encoding'] = ('Content-Encoding', 'gzip')

        else:
            response = HttpResponse(g.fileDict[fileUrl][0])

        add_response_field(response, **{'last-modified': g.fileDict[fileUrl][2]})

        return response

    return f

g = StaticFile()


