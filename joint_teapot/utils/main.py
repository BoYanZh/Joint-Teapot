import math
import re
from typing import Callable, Iterable, Optional, TypeVar

from canvasapi.user import User

_T = TypeVar("_T")


def first(
    iterable: Iterable[_T], condition: Callable[[_T], bool] = lambda x: True
) -> Optional[_T]:
    return next((x for x in iterable if condition(x)), None)


def percentile(
    N: Iterable[float], percent: float, key: Callable[[float], float] = lambda x: x
) -> Optional[float]:
    if not N:
        return None
    N = sorted(N)
    k = (len(N) - 1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return key(N[int(k)])
    d0 = key(N[int(f)]) * (c - k)
    d1 = key(N[int(c)]) * (k - f)
    return d0 + d1


def default_repo_name_convertor(user: User) -> str:
    login_id, name = user.login_id, user.name
    eng = re.sub("[\u4e00-\u9fa5]", "", name)
    eng = eng.replace(",", "")
    eng = eng.title().replace(" ", "").replace(u'\xa0', '')
    return f"{eng}{login_id}"
