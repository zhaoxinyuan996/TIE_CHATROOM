import sqlite3

from collections import OrderedDict

dbpath = 'home/admin/db/tie.db'

class FalseLogger():
    level = 1
    lv_dict = {
        'error':   3,
        'warning': 2,
        'info':    1,
        'debug':   0
    }
    def __getattr__(self, item):
        if item in ('error', 'warning', 'info', 'debug'):
            if self.lv_dict[item] >= self.level:
                return lambda msg: print('[%s]:%s\n' % (item, msg))
            return lambda item: None
        raise AttributeError('object has no attr %s' % item)

class SqliteDb():
    default_column = OrderedDict()
    default_column['tittle'] = ''
    default_column['time'] = ''
    default_column['abstract'] = 0
    default_column['url'] = ''
    default_column['purl1'] = ''
    default_column['purl2'] = ''
    default_column['purl3'] = ''

    def __init__(self, logger=None):
        self.logger = logger if logger else FalseLogger()

    def __enter__(self):
        self.db = sqlite3.connect(dbpath, isolation_level=None) # 自动事务
        self.cursor = self.db.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

    def execute(self, sql):
        try:
            res = self.cursor.execute(sql).fetchall()
            self.logger.info('exec sql is %s, result is %s' % (sql, res))
            return True, res

        except BaseException as e:
            self.logger.error('exec sql is %s, reason is %s' % (sql, e))
            return False, e

    def base_c(self, tb_name, ins, suffix=None):
        ins_dict = ins[0] if isinstance(ins, list) else ins
        sql = 'insert into %s' % tb_name + ' select ' + ' , '.join(
            [('"%s" as `%s`' % (j, i) if isinstance(j, str) else
              '%s as `%s`' % (j, i)) for i, j in ins_dict.items()])

        if isinstance(ins, list):
            for dic in ins[1:]:
                sql += ' union select ' + ' , '.join([('"%s"') % i if isinstance(i, str) else
                                                      '%s' % i for i in dic.values()])

        if suffix:
            sql += ' %s' % suffix

        return self.execute(sql)

    def base_r(self, tb_name, sel=None, eq_whe=None, custom_whe=None, suffix=None):
        if sel:
            if isinstance(sel, list):
                sel = ','.join([i for i in sel])
        else:
            sel = '*'

        sql = 'select %s from %s' % (sel, tb_name)

        if eq_whe:
            equal_whe = [
                '`%s`=%s' % (i, j) if not isinstance(j, str) else
                '`%s`="%s"' % (i, j) for i, j in eq_whe.items()]
            sql += ' where ' + ' and '.join(equal_whe)

        if custom_whe:
            unequal_whe =' and '.join(
                [i for i in (custom_whe if isinstance(custom_whe, list) else [custom_whe])])

            sql += (' and ' + unequal_whe) if eq_whe else (' where ' + unequal_whe)

        if suffix:
            sql += ' %s' % suffix

        return self.execute(sql)

    def base_u(self, tb_name, upd, eq_whe=None, custom_whe=None, suffix=None):
        sql = 'update %s' % tb_name
        upd = ['`%s`=%s' % (i, j) if not isinstance(j, str) else
               '`%s`="%s"' % (i, j) for i, j in upd.items()]
        sql += ' set ' + ' , '.join(upd)

        if eq_whe:
            equal_whe = [
                '`%s`=%s' % (i, j) if not isinstance(j, str) else
                '`%s`="%s"' % (i, j) for i, j in eq_whe.items()]
            sql += ' where ' + ' and '.join(equal_whe)

        if custom_whe:
            unequal_whe = ' and '.join(
                [i for i in (custom_whe if isinstance(custom_whe, list) else [custom_whe])])

            sql += (' and ' + unequal_whe) if eq_whe else (' where ' + unequal_whe)

        if suffix:
            sql += ' %s' % suffix

        return self.execute(sql)

    def base_d(self, tb_name, eq_whe=None, custom_whe=None, suffix=None):
        sql = 'delete from %s' % tb_name
        if eq_whe:
            equal_whe = [
                '`%s`=%s' % (i, j) if not isinstance(j, str) else
                '`%s`="%s"' % (i, j) for i, j in eq_whe.items()]
            sql += ' where ' + ' and '.join(equal_whe)

        if custom_whe:
            unequal_whe = ' and '.join(
                [i for i in (custom_whe if isinstance(custom_whe, list) else [custom_whe])])

            sql += (' and ' + unequal_whe) if eq_whe else (' where ' + unequal_whe)

        if suffix:
            sql += ' %s' % suffix

        return self.execute(sql)

    @staticmethod
    def _format_iterable(iterable):
        '''处理 sql语句中 in 语法，传入单个或列表，返回带括号的替换字符串'''
        if not isinstance(iterable, list): iterable = [iterable]

        string = '(%s)' % ' , '.join([('"%s"' % i) if isinstance(i, str) else
                                      str(i) for i in iterable])

        return string

    def s(self):
        return self.execute('select * from news')


if __name__ == '__main__':
    with SqliteDb() as sql:
        import pdb; pdb.set_trace()
        pass
        pass
        pass


'''
create table news(nid integer primary key AUTOINCREMENT,tittle varchar(50),time int,abstract varchar(300),url varchar(100),purl1 varchar(200),purl2 varchar(200),purl3 varchar(200))
'''