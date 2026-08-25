from abc import ABC, abstractmethod

from cka.domain.user import User


class UserRepository(ABC):
    @abstractmethod
    def get_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    def save(self, user: User) -> None: ...
