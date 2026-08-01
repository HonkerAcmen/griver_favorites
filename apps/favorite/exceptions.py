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


class FavoriteItemNotFoundException(BusinessException):
    """收藏项不存在、已软删或不属于当前 user。

    适用于：取消收藏、移动收藏项、查看指定收藏项详情等操作前校验失败。
    """

    def __init__(self) -> None:
        super().__init__(404041, "FAVORITE_ITEM_NOT_EXISTS")


class IntelligenceNotFoundException(BusinessException):
    """目标情报资源不存在或已被物理/逻辑删除。

    适用于：添加收藏时校验 target_id 对应的情报实体是否存在。
    """

    def __init__(self) -> None:
        super().__init__(404042, "INTELLIGENCE_NOT_EXISTS")


class FavoriteItemAlreadyExistsException(BusinessException):
    """当前用户已收藏过该目标资源（唯一性约束冲突）。

    适用于：重复添加相同 target_id 的情报，或捕获到 uq_griver_favorite_item_folder_target_active 数据库唯一索引冲突。
    """

    def __init__(self) -> None:
        super().__init__(409041, "FAVORITE_ITEM_ALREADY_EXISTS")


class FavoriteItemMoveFailedException(BusinessException):
    """收藏项移动操作失败。

    适用于：试图将收藏项移动到当前所在的同一个文件夹、目标文件夹非法或目标位置已被占用等无效变更操作。
    """

    def __init__(self) -> None:
        super().__init__(400041, "FAVORITE_ITEM_MOVE_FAILED")


class FavoriteUserNotFoundException(BusinessException):
    """
    用户无效
    """

    def __init__(self) -> None:
        super().__init__(404041, "FAVORITE_USER_NOT_EXISTS")


class FavoriteInternalDataConflict(BusinessException):
    """
    数据冲突
    """

    def __init__(self) -> None:
        super().__init__(500001, "INTERNAL_DATA_CONFLICT")
