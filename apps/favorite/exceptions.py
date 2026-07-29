"""收藏夹模块业务异常。Service 层抛出，由全局 handler 转成统一 JSON。"""


class BusinessException(Exception):
    """业务异常基类。

    子类在 Service 层抛出；全局 exception handler 捕获后转为 HTTP 200 + 非零 code。
    """

    http_status: int = 200

    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg
        super().__init__(msg)


class FavoriteFolderNotFoundException(BusinessException):
    """收藏夹不存在、已软删或不属于当前 user（R3）。

    适用于：查询详情、重命名、删除、向收藏夹加入/移除情报等操作前校验失败。
    """

    def __init__(self) -> None:
        super().__init__(404001, "FAVORITE_FOLDER_NOT_EXISTS")


class FavoriteFolderNameDuplicateException(BusinessException):
    """收藏夹名称与同一用户下其他未删收藏夹重复（R1）。

    适用于：创建收藏夹或重命名时，strip 后的名称已被占用。
    """

    def __init__(self) -> None:
        super().__init__(409001, "FAVORITE_FOLDER_NAME_DUPLICATE")


class FavoriteFolderNameInvalidException(BusinessException):
    """收藏夹名称不合法（R1 前置校验）。

    适用于：名称为空、仅空白字符，或 strip 后长度超过 100（FOLDER_NAME_MAX_LEN）。
    """

    def __init__(self) -> None:
        super().__init__(400001, "FAVORITE_FOLDER_NAME_INVALID")
