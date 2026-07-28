"""收藏夹模块业务异常。Service 层抛出，由全局 handler 转成统一 JSON。"""


class BusinessException(Exception):
    """业务异常基类。"""

    http_status: int = 200

    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg
        super().__init__(msg)


class FavoriteFolderNotFoundException(BusinessException):
    def __init__(self) -> None:
        super().__init__(404001, "FAVORITE_FOLDER_NOT_EXISTS")


class FavoriteFolderNameDuplicateException(BusinessException):
    def __init__(self) -> None:
        super().__init__(409001, "FAVORITE_FOLDER_NAME_DUPLICATE")


class FavoriteFolderNameInvalidException(BusinessException):
    def __init__(self) -> None:
        super().__init__(400001, "FAVORITE_FOLDER_NAME_INVALID")
