"""
Definitions to use CoNLL-U as a query language.

Defines more permissive parsing plus reserved MISC fields with a special meaning.
"""

import re
from enum import StrEnum
from typing import Any, Callable, Optional

import conllu
from conllu.exceptions import ParseException


def field_parser[A](f: Callable[[str], A]) -> Callable[[list[str], int], A]:
    """
    Transforms functions processing a string i.e. `(str) -> A` into a function
    compatible with the field parser signature of conllu: `(list[str], int) -> A`.
    """
    return lambda line, i: f(line[i])


@field_parser
def parse_unchanged(value: str) -> str:
    """
    Identity field parser used to parse the head column.
    We allow use of identifiers for the head and not just numerical ids.
    """
    return value


@field_parser
def parse_nullable(value: str) -> Optional[str]:
    """
    Field parser recognizing "_" as None.
    """
    if value == '_':
        return None
    return value


@field_parser
def parse_dict(value: str) -> dict[str, str]:
    """
    Field parser for Key=Value pairs separated by "|".
    Recognizes "_" as the empty dictionary.
    """
    if value == '_':
        return {}

    result = {}
    for segment in value.split('|'):
        if '=' in segment:
            key, val = segment.split('=', maxsplit=1)
            result[key] = val if val != '_' else None
        else:
            result[segment] = ''
    return result


# This more permissive than CoNLL-U, allowing each field apart from ID to be unspecified.
FIELD_PARSERS: dict[str, Callable[[list[str], int], Any]] = {
    'id': parse_unchanged,
    'form': parse_nullable,
    'lemma': parse_nullable,
    'upos': parse_nullable,
    'xpos': parse_nullable,
    'feats': parse_dict,
    'head': parse_nullable,
    'deprel': parse_nullable,
    'deps': parse_nullable,
    'misc': parse_dict,
}


def is_multiword_token(token: conllu.Token) -> bool:
    """Multiword tokens have a token ID like 1-3"""
    return re.fullmatch(r'\d+-\d+', token['id']) is not None


def is_empty_node(token: conllu.Token) -> bool:
    """Empty nodes have a token ID like 4.1"""
    return re.fullmatch(r'\d+.\d+', token['id']) is not None


def parse_conllu_sentence(s: str) -> list[conllu.Token]:
    """Parses a given string into a list of Token"""
    try:
        parsed = conllu.parse(s, fields=FIELD_PARSERS)
    except ParseException as ex:
        raise ValueError(f'Invalid CoNLL-U: {ex}') from ex

    if len(parsed) == 0:
        raise ValueError('No CoNLL-U sentence found!')

    sentence = parsed[0]
    return [
        token for token in sentence if not is_multiword_token(token) and not is_empty_node(token)
    ]


class ReservedAnnotation(StrEnum):
    """
    All reserved annotations to be ignored when translating.
    """

    # Special meanings for translation
    ORDERED = 'ordered'
    SUBSEQUENT = 'subsequent'

    @classmethod
    def is_reserved(cls, annotation: str) -> bool:
        """Is the given MISC column key a reserved annotation?"""
        return annotation in cls

    def is_present_on(self, token: conllu.Token) -> bool:
        """
        Does the given CoNLL-U token has this annotation?
        Annotation has to be encoded as Ann=Yes on the misc column.
        """
        all_annotations = token['misc']
        if hasattr(all_annotations, '__getitem__') and self.value in all_annotations:
            return all_annotations[self.value] == 'Yes'
        return False
