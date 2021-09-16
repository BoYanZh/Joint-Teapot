from typing import Callable, Iterable, Optional, TypeVar

_T = TypeVar("_T")


def first(
    iterable: Iterable[_T], condition: Callable[[_T], bool] = lambda x: True
) -> Optional[_T]:
    return next((x for x in iterable if condition(x)), None)
