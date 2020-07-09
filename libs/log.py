import platform

from time import strftime
from sys import _getframe
from threading import currentThread

from TIE.settings import LoggerSettings


class Logger:

    def __init__(self, level: str, w=True, p=True) -> None:
        '''w:写入文件;p:打印至控制台'''
        self._loggerDict = {
            'ERROR'  : (0, '\033[31mERROR\033[0m'),
            'WARNING': (1, '\033[33mWARNING\033[0m'),
            'INFO'   : (2, '\033[36mINFO\033[0m'),
            'DEBUG'  : (3, '\033[32mDEBUG\033[0m'),
        }
        self._levelNum = self._loggerDict[level][0]
        self._w = w
        self._p = p
        print('logger模块加载')

    def __getattr__(self, item: str):
        if item in ('error', 'warning', 'info', 'debug'):
            item = item.upper()

            if self._levelNum >= self._loggerDict[item][0]:
                return lambda info: self._output(item, info)

            return lambda info: None

    def _to_file(self, info: str) -> None:
        with open('%s%s.txt' % (LoggerSettings.logFilePath, strftime('%Y-%m-%d')), 'a') as f:
            f.write('%s\n' % info)

    def _output(self, level: str, info0: str) -> None:
        if isinstance(info0, bytes):
            info0 = info0.decode()

        info0 = '%s [%s] %s %s -> line.%s:%s' % (
            strftime('%Y-%m-%d %H:%M:%S'),      # 时间
            '%s',                               # 级别
            currentThread(),                    # 线程号
            _getframe(2).f_code.co_filename,    # 所在函数
            _getframe(2).f_lineno,              # 所在行
            info0                               # 信息
        )
        if self._w:
            info = info0 % level
            self._to_file(info)

        if self._p:
            info = info0 % self._loggerDict[level][1]
            print(info)



myLog = Logger(LoggerSettings.level, w=False if 'win' in platform.system().lower() else True)


if __name__ == '__main__':
    myLog.debug('123')
    myLog.info('123')
    myLog.warning('123')
    myLog.error('123')