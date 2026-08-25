from sqlalchemy import select
from sqlalchemy.orm import Session

from cka.domain.user import User
from cka.domain.user_repository import UserRepository
from cka.infrastructure.database.models import UserModel


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_username(self, username: str) -> User | None:
        model = self._session.scalar(select(UserModel).where(UserModel.username == username))
        return self._to_domain(model) if model else None

    def save(self, user: User) -> None:
        model = UserModel(
            id=user.id,
            username=user.username,
            password_hash=user.password_hash,
            role=user.role,
            active=user.active,
        )
        self._session.merge(model)

    @staticmethod
    def _to_domain(model: UserModel) -> User:
        return User(
            id=model.id,
            username=model.username,
            password_hash=model.password_hash,
            role=model.role,
            active=model.active,
        )
