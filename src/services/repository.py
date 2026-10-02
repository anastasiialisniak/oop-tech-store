from typing import Generic, TypeVar


T = TypeVar("T")


class Repository(Generic[T]):
    def __init__(self):
        self.__items: list[T] = []

    def add(self, item: T) -> None:
        self.__items.append(item)

    def get_all(self) -> list[T]:
        return self.__items.copy()

    def count(self) -> int:
        return len(self.__items)

    def clear(self) -> None:
        self.__items.clear()