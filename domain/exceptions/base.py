from __future__ import annotations


class AppError(RuntimeError):
    """Base application error for domain layer.

    Keep this class free of framework concerns so it can be used across
    domain and infrastructure code.

    Domain-layer exceptions should normally rely on the default
    ``status_code = 500`` to represent unexpected/internal errors.
    Infrastructure-layer exceptions (for example, HTTP or persistence
    adapters) should subclass this type and override ``status_code``
    with an appropriate HTTP status (e.g. 404 for not found, 409 for
    conflicts) when those details are known at that layer.
    """

    status_code: int = 500

    def __init__(self, detail: str | None = None):
        super().__init__(detail or self.__class__.__name__)
        self.detail = detail or self.__class__.__name__
