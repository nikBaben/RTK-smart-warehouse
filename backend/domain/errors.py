"""Application errors; HTTP and database details belong to adapters."""


class ApplicationError(Exception):
    pass


class NotFound(ApplicationError):
    pass


class Conflict(ApplicationError):
    pass


class InvalidOperation(ApplicationError):
    pass


class RelatedEntityError(ApplicationError):
    pass


class StorageError(ApplicationError):
    pass
