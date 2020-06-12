
# 这里放基类

class BaseError(Exception):
    @classmethod
    def __str__(cls) -> str:
        return cls.__name__
