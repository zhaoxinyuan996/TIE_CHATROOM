import platform

from time import strftime
from sys import _getframe
from threading import currentThread, Thread

from TIE.settings import LoggerSettings


class Logger:

    def __init__(self, level: str, w=True, p=True) -> None:
        '''w:写入文件;p:打印至控制台'''
        print('logger模块加载')
        self._loggerDict = {
            'ERROR'  : (0, '\033[31mERROR\033[0m'),
            'WARNING': (1, '\033[33mWARNING\033[0m'),
            'INFO'   : (2, '\033[36mINFO\033[0m'),
            'DEBUG'  : (3, '\033[32mDEBUG\033[0m'),
        }
        self._levelNum = self._loggerDict[level][0]
        self._w = w
        self._p = p

    def _to_file(self, info: str) -> None:
        with open('%s%s.txt' % (LoggerSettings.logFilePath, strftime('%Y-%m-%d')), 'a') as f:
            f.write('%s\n' % info)

    def _output(self, level: str, info0: str) -> None:
        if isinstance(info0, bytes):
            info0 = info0.decode()
        if self._w:
            info = '%s [%s] %s %s -> line.%s:%s' % (
                strftime('%Y-%m-%d %H:%M:%S'),   # 时间
                self._loggerDict[level],         # 级别
                currentThread(),                 # 线程号
                _getframe(2).f_code.co_filename, # 所在函数
                _getframe(2).f_lineno,           # 所在行
                info0)
            self._to_file(info)


        if self._p:
            info = '%s [%s] %s %s -> line.%s:%s' % (
                strftime('%Y-%m-%d %H:%M:%S'),   # 时间
                level,                           # 级别
                currentThread(),                 # 线程号
                _getframe(2).f_code.co_filename, # 所在函数
                _getframe(2).f_lineno,           # 所在行
                info0)
            print(info)


    def error(self, info: (str, bytes)) -> None:
        if self._levelNum >= 0:
            self._output('ERROR', info)
    def warning(self, info: (str, bytes)) -> None:
        if self._levelNum >= 1:
            self._output('WARNING', info)
    def info(self, info: (str, bytes)) -> None:
        if self._levelNum >= 2:
            self._output('INFO', info)
    def debug(self, info: (str, bytes)) -> None:
        if self._levelNum >= 3:
            self._output('DEBUG', info)


myLog = Logger(LoggerSettings.level, w=False if 'win' in platform.system().lower() else True)


if __name__ == '__main__':
    logger = Logger(LoggerSettings.level)
    logger.info('123')