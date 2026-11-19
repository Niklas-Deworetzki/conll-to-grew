"""
Definition of a minimal abstract syntax for Grew-match queries.
"""

import string
from abc import ABC
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal as LiteralType, Optional, Sequence

Identifier = str
AnyNode = LiteralType['*']


@dataclass
class Literal:
    """
    "björn"
    adj
    """

    value: str

    def __str__(self) -> str:
        return f'"{self.value}"' if string_requires_quotes(self.value) else self.value


class Feature(ABC):
    pass


@dataclass
class FeatureEquals(Feature):
    """
    [upos = ADJ]
    """

    feature: Identifier
    value: str

    def __str__(self) -> str:
        return f'{self.feature}={Literal(self.value)}'


# Arrow


@dataclass
class Arrow:
    """
    ->
    -[advmod]>
    """

    type: Optional[str] = None

    def __str__(self) -> str:
        if type := self.type:
            return f'-[{Literal(type)}]->'
        return '->'


# Clauses


class Clause(ABC):
    pass


@dataclass
class NodeClause(Clause):
    """
    X [upos=ADV, Typo=Yes]
    """

    label: Identifier
    features: Sequence[Feature]

    def __str__(self) -> str:
        feature_structure = ', '.join(map(str, self.features))
        return f'{self.label} [{feature_structure}]'


@dataclass
class EdgeClause(Clause):
    """
    X -> Y
    """

    src: Identifier | AnyNode
    arrow: Arrow
    dst: Identifier | AnyNode

    def __str__(self) -> str:
        return f'{self.src} {self.arrow} {self.dst}'


@dataclass
class OrderClause(Clause):
    """
    X << Y
    """

    class Order(StrEnum):
        PRECEDENCE = '<<'
        IMMEDIATE_PRECEDENCE = '<'

    lhs: Identifier
    order: Order
    rhs: Identifier

    def __str__(self) -> str:
        return f'{self.lhs} {self.order.value} {self.rhs}'


# Request


@dataclass
class Request:
    pattern: Sequence[Clause]

    def __str__(self) -> str:
        body = ''.join(f'\t{clause};\n' for clause in self.pattern)
        return 'pattern {\n' + body + '}'


RESERVED_KEYWORDS = {
    're',
    'include',
    'import',
    'from',
    'pattern',
    'without',
    'with',
    'commands',
    'global',
    'add_edge',
    'del_edge',
    'shift_in',
    'shift_out',
    'shift',
    'del_node',
    'add_node',
    'del_feat',
    'append_feats',
    'prepend_feats',
    'unorder',
    'insert',
    'package',
    'rule',
    'strat',
    'Pick',
    'Alt',
    'Seq',
    'Iter',
    'If',
    'Try',
    'Empty',
    'Onf',
}


def string_requires_quotes(s: str) -> bool:
    """
    Does the given string need quotes when used as a literal in Grew?
    """

    if not s:
        return True

    if s in RESERVED_KEYWORDS:
        return True

    if all(char in string.ascii_letters for char in s):
        return False

    if all(char in string.digits for char in s):
        return False

    return True
