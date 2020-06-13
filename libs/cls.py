
# 这里放基类

class BaseError(Exception):
    def __str__(self) -> str:
        return type(self).__name__ + (':' + (''.join(self.args)).__repr__() if self.args else '')





if __name__ == '__main__':
    e = BaseError()
    ee = BaseError('错了')

    print(e)
    print(ee)

    raise KeyError('错了')