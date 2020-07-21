import time
import sqlite3
import platform

from collections import OrderedDict

dbPath = '/home/admin/db/tie.db'

if 'win' in platform.system().lower():
    dbPath = 'db.sqlite3'

def to_stamp(t: str) -> int:
    defaultTime = list(time.strftime('%Y%m%d%H%M'))
    for i in range(len(t)):
        defaultTime[~i] = t[~i]

    t = ''.join(defaultTime)
    return int(time.mktime(time.strptime(t, "%Y%m%d%H%M")))

class FalseLogger():
    level = 1
    lvDict = {
        'error':   3,
        'warning': 2,
        'info':    1,
        'debug':   0
    }
    def __getattr__(self, item: str):
        if item in ('error', 'warning', 'info', 'debug'):
            if self.lvDict[item] >= self.level:
                return lambda msg: print('[%s]:%s\n' % (item, msg))
            return lambda item: None
        raise AttributeError('object has no attr %s' % item)

class SqliteDb():
    tbName = 'news'

    defaultColumn = OrderedDict()
    defaultColumn['type'] = ''
    defaultColumn['tittle'] = ''
    defaultColumn['time'] = ''
    defaultColumn['abstract'] = 0
    defaultColumn['url'] = ''
    defaultColumn['purl1'] = ''
    defaultColumn['purl2'] = ''
    defaultColumn['purl3'] = ''

    def __init__(self, logger:FalseLogger=None) -> None:
        self.logger = logger if logger else FalseLogger()

    def __enter__(self) -> object:
        self.db = sqlite3.connect(dbPath, isolation_level=None) # 自动事务
        self.cursor = self.db.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.db.close()

    def execute(self, sql: str) -> tuple:
        try:
            res = self.cursor.execute(sql).fetchall()
            self.logger.info('exec sql is %s, result is %s' % (sql, res))
            return True, res

        except BaseException as e:
            self.logger.error('exec sql is %s, reason is %s' % (sql, e))
            return False, e

    def base_c(self, ins: OrderedDict, suffix=None) -> tuple:
        ins_dict = ins[0] if isinstance(ins, list) else ins
        sql = 'insert into %s' % self.tbName + ' select ' + ' , '.join(
            [('"%s" as `%s`' % (j, i) if isinstance(j, str) else
              '%s as `%s`' % (j, i)) for i, j in ins_dict.items()])

        if isinstance(ins, list):
            for dic in ins[1:]:
                sql += ' union select ' + ' , '.join([('"%s"') % i if isinstance(i, str) else
                                                      '%s' % i for i in dic.values()])

        if suffix:
            sql += ' %s' % suffix

        return self.execute(sql)

    def base_r(self, sel:(str, list)=None, eqWhe: dict=None, customWhe: str=None, suffix:str=None) -> tuple:
        if sel:
            if isinstance(sel, list):
                sel = ','.join((i for i in sel))
        else:
            sel = '*'

        sql = 'select %s from %s' % (sel, self.tbName)

        if eqWhe:
            equal_whe = [
                '`%s`=%s' % (i, j) if not isinstance(j, str) else
                '`%s`="%s"' % (i, j) for i, j in eqWhe.items()]
            sql += ' where ' + ' and '.join(equal_whe)

        if customWhe:
            unequal_whe =' and '.join(
                (i for i in (customWhe if isinstance(customWhe, list) else [customWhe])))

            sql += (' and ' + unequal_whe) if eqWhe else (' where ' + unequal_whe)

        if suffix:
            sql += ' %s' % suffix

        return self.execute(sql)

    def base_u(self, upd, eqWhe: dict=None, customWhe: str=None, suffix:str=None) -> tuple:
        sql = 'update %s' % self.tbName
        upd = ['`%s`=%s' % (i, j) if not isinstance(j, str) else
               '`%s`="%s"' % (i, j) for i, j in upd.items()]
        sql += ' set ' + ' , '.join(upd)

        if eqWhe:
            equal_whe = [
                '`%s`=%s' % (i, j) if not isinstance(j, str) else
                '`%s`="%s"' % (i, j) for i, j in eqWhe.items()]
            sql += ' where ' + ' and '.join(equal_whe)

        if customWhe:
            unequal_whe = ' and '.join(
                [i for i in (customWhe if isinstance(customWhe, list) else [customWhe])])

            sql += (' and ' + unequal_whe) if eqWhe else (' where ' + unequal_whe)

        if suffix:
            sql += ' %s' % suffix

        return self.execute(sql)

    def base_d(self, eqWhe: dict=None, customWhe: str=None, suffix:str=None) -> tuple:
        sql = 'delete from %s' % self.tbName
        if eqWhe:
            equal_whe = [
                '`%s`=%s' % (i, j) if not isinstance(j, str) else
                '`%s`="%s"' % (i, j) for i, j in eqWhe.items()]
            sql += ' where ' + ' and '.join(equal_whe)

        if customWhe:
            unequal_whe = ' and '.join(
                [i for i in (customWhe if isinstance(customWhe, list) else [customWhe])])

            sql += (' and ' + unequal_whe) if eqWhe else (' where ' + unequal_whe)

        if suffix:
            sql += ' %s' % suffix

        return self.execute(sql)

    @staticmethod
    def _format_iterable(iterable: list) -> str:
        '''处理 sql语句中 in 语法，传入单个或列表，返回带括号的替换字符串'''
        if not isinstance(iterable, list): iterable = [iterable]

        string = '(%s)' % ' , '.join([('"%s"' % i) if isinstance(i, str) else
                                      str(i) for i in iterable])

        return string

    def s(self) -> tuple:
        return self.execute('select * from news')

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    def insert(self, type: str, tittle: str, time: str, abstract: str, url: str, *purls: tuple) -> tuple:
        if 0 < len(purls) <= 3:
            d = OrderedDict(self.defaultColumn)
            d['type'] = type
            d['tittle'] = tittle
            d['time'] = to_stamp(time)
            d['abstract'] = abstract
            d['url'] = url

            for i in range(1, len(purls)):
                d['purl%s' % i] = purls[i]

            return self.base_c(d)

        raise IndexError('这个入参好像是超长了, 参数是%s' % (purls, ))

if __name__ == '__main__':
    with SqliteDb() as sql:
        # print(sql.execute("SELECT * FROM sqlite_master WHERE type='table'"))
        import pdb; pdb.set_trace()
        pass
        pass
        pass
    # insert(self, tittle, time, abstract, url, *purls)


'''
create table news(type varchar(20),tittle varchar(50),time int,abstract varchar(300),url varchar(100),purl1 varchar(200),purl2 varchar(200),purl3 varchar(200))
'''