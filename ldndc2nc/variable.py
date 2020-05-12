# -*- coding: utf-8 -*-
"""ldndc2nc.extra: extra module within the ldndc2nc package."""

import logging
from typing import List, Optional, Tuple

log = logging.getLogger(__name__)


def identical(elements: List) -> bool:
    return all([e == elements[0] for e in elements])


def valid_brackets(s: str) -> bool:
    """only up to one open/ close square bracket allowed"""
    cnt, cnt_closed = 0, 0
    for l in s:
        if l == "[":
            cnt += 1
            if cnt > 1:
                return False
        if l == "]":
            cnt -= 1
            if cnt == 0:
                cnt_closed += 1
            elif cnt < 0:
                return False
    if cnt_closed > 1:
        return False
    return True


def variables_compatible(s: str, src: List[str]) -> bool:
    prefixes = [f"{v}_" for v in ["dC", "dN", "aC", "aN"]]

    ps = [p for p in prefixes for s in src if s.startswith(p)]

    # include target variable if it also has a known prefix
    for t_p in prefixes:
        if s.startswith(t_p):
            ps.append(t_p)

    if identical(ps):
        return True

    return False


class Variable:
    def __init__(self, s: str, sources: Optional[str] = None):

        if s.count("=") == 0:
            pass
        elif s.count("=") == 1:
            s, sources = s.split("=")
        else:
            raise ValueError(f"Variable line is invalid:\n{s}")

        self._sources = [s]
        self.name, self.unit = self._decode(s)

        if sources:
            self._sources = sources.split("+") if "+" in sources else [sources]

            if not variables_compatible(s, self._sources):
                raise ValueError("Trying to add incompatible columns")

    def __repr__(self):
        return f"<var:{self.name}({self.unit})>"

    @property
    def text(self) -> str:
        return f"{self._encode(self.name, self.unit)}"

    @property
    def text_full(self) -> str:
        part1 = self.text
        part2 = "=" + "+".join(self._sources) if self.is_composite else ""
        return part1 + part2

    @property
    def sources(self) -> List[str]:
        return self._sources

    @property
    def is_composite(self) -> bool:
        return False if len(self._sources) == 1 else True

    @staticmethod
    def _decode(s: str) -> Tuple[str, Optional[str]]:
        if not valid_brackets(s):
            raise ValueError(f"Variable {s} does not follow formatting convention")
        return tuple(s.replace("]", "").split("[")) if "[" in s else (s, None)

    @staticmethod
    def _encode(name: str, unit: Optional[str] = None) -> str:
        return f"{name}[{unit}]" if unit else name
