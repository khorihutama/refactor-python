from collections.abc import Iterable
from dataclasses import dataclass


@dataclass
class User:
    name: str
    quota: int
    executed: int = 0


class UserRegistry:
    def __init__(self, users: Iterable[User]) -> None:
        self._users = {user.name: user for user in users}

    def __contains__(self, name: object) -> bool:
        return name in self._users

    def get(self, name: str) -> User:
        return self._users[name]

    def can_execute(self, name: str) -> bool:
        user = self._users[name]
        return user.executed < user.quota

    def record_execution(self, name: str) -> None:
        self._users[name].executed += 1
