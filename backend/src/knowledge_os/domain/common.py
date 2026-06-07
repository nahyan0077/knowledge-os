from dataclasses import dataclass


@dataclass(frozen=True)
class DomainError(Exception):
    message: str
    code: str

    def __str__(self) -> str:
        return self.message


class ConflictError(DomainError):
    pass


class AuthenticationError(DomainError):
    pass


class AuthorizationError(DomainError):
    pass


class NotFoundError(DomainError):
    pass


class ValidationError(DomainError):
    pass
