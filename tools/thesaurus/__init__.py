import os
from sys import _getframe

from libs.logger import logger


class FilterTool:
    def __init__(self):
        '''加载违规词库到self._againstTuple'''
        _tmpList = []
        _existfile = ('反动词库.txt', '暴恐词库.txt')

        _filterDirPath = os.path.join(_getframe().f_code.co_filename, os.path.pardir)
        for i in os.listdir(_filterDirPath):
            if i in _existfile:
                with open(os.path.join(_filterDirPath, i,), encoding='utf-8-sig') as f:
                    _tmpList.extend(f.read().split('\n'))

        self._againstTuple = tuple(_tmpList)
        del _tmpList, _existfile

    def deal(self, words:str, userInfo=None) -> tuple:
        '''
        :param words:    过滤前字符
        :param userInfo: 用户信息，比如ip，用于输出违规日志
        :return: 是：消息； 否：违规消息
        '''
        for i in self._againstTuple:
            if i in words:
                logger.warning('user is %s words is "%s", against word "%s"' % (userInfo, words, i))
                return False, '"%s"为违规词汇！' % i
        return True, words


filterTool = FilterTool()
