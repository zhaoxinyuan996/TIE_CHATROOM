import os
import re
from sys import _getframe

from libs import Secret
from libs.log import myLog


# 关键词过滤器
class WordsFilterTool:
    def __init__(self) -> None:
        '''加载违规词库到self._againstTuple'''
        print('WordsFilterTool模块加载')
        _tmpList = []
        _existfile = ('反动词库.txt', '暴恐词库.txt')

        _filterDirPath = os.path.dirname(_getframe().f_code.co_filename)
        for i in os.listdir(_filterDirPath):
            if i in _existfile:
                with open(os.path.join(_filterDirPath, i,), encoding='utf-8-sig') as f:
                    _tmpList.extend(f.read().split('\n'))

        self._againstTuple = tuple(_tmpList)
        del _tmpList, _existfile

    def deal(self, words: (str, bytes), userInfo=None) -> tuple:
        '''
        :param words:    过滤前字符
        :param userInfo: 用户信息，比如ip，用于输出违规日志
        :return: 是：消息； 否：违规消息
        '''
        if isinstance(words, bytes):
            try: words = words.decode()
            except: return False, '“%s”decode failed' % words

        for i in self._againstTuple:
            if i in words:
                myLog.warning('user is %s words is "%s", against word "%s"' % (userInfo, words, i))
                return False, '"%s"为违规词汇！' % i
        return True, words


# SQL注入过滤器
class SqlFilterTool:
    def __init__(self) -> None:
        print('SqlFilterTool模块加载')
        self._againstTuple = ("select",
                              "insert",
                              "delete",
                              "count(",
                              "drop table",
                              "update",
                              "truncate",
                              "asc(",
                              "mid(",
                              "char(",
                              "xp_cmdshell",
                              "exec",
                              "master",
                              "net",
                              "and",
                              "or",
                              "where",

                              '<',
                              '<=',
                              '>',
                              '>=',
                              '=')

    def deal(self, *values: str) -> (str, bool):
        '''多个入参，通过返回True，不通过返回字段'''
        for i in self._againstTuple:
            for j in values:
                if i in j:
                    return j
        return True


# url/ip过滤器
class HostFilterTool:
    @staticmethod
    def deal(words: (str, bytes), userInfo=None) -> tuple:
        '''
        :param words:    过滤前字符
        :param userInfo: 用户信息，比如ip，用于输出违规日志
        :return: 是：消息； 否：违规消息
        '''
        if isinstance(words, bytes):
            try: words = words.decode()
            except: return False, '“%s”decode failed' % words

        res = re.search(Secret.rHost, words)
        if res:
                myLog.warning('user is %s words is "%s", against word "%s"' % (userInfo, words, res.group()))
                return False, '"%s"疑似为网址！' % res.group()

        res = re.search(Secret.rUrl, words)
        if res:
                myLog.warning('user is %s words is "%s", against word "%s"' % (userInfo, words, res.group()))
                return False, '"%s"疑似为IP！' % res.group()

        return True, words


sqlFilterTool = SqlFilterTool()
hostFilterTool = HostFilterTool()
wordsFilterTool = WordsFilterTool()