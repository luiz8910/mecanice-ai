from __future__ import annotations


class DomainError(Exception):
	"""Base class for domain-layer errors."""


class NotFoundError(DomainError):
	"""Raised when an entity cannot be found."""


class ValidationError(DomainError):
	"""Raised when domain validation fails."""


class ConflictError(DomainError):
	"""Raised when an operation would cause a conflict (eg. duplicate)."""


class UnauthorizedError(DomainError):
	"""Raised when the actor is not authorized to perform an action."""


# Specific domain exceptions (convenience subclasses)
class MechanicNotFound(NotFoundError):
	pass


class WorkshopNotFound(NotFoundError):
	pass


class SupplierNotFound(NotFoundError):
	pass


class VendorNotFound(NotFoundError):
	pass


class VendorAssignmentNotFound(NotFoundError):
	pass


class QuotationNotFound(NotFoundError):
	pass


class QuoteError(DomainError):
	"""Generic quote-related error."""


class SolicitationError(DomainError):
	"""Generic solicitation-related error."""

