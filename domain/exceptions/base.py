from __future__ import annotations


class AppError(RuntimeError):
    """Base application error for domain layer.

    Keep this class free of framework concerns so it can be used across
    domain and infrastructure code. Concrete errors should subclass this
    in the infrastructure layer when they need specific status codes.
    """

    status_code: int = 500

    def __init__(self, detail: str | None = None):
        super().__init__(detail or self.__class__.__name__)
        self.detail = detail or self.__class__.__name__
