"""
Translation of CoNLL-U sentence into a Grew-match Request.
"""

from typing import Iterable, Iterator, Optional

import conllu

from conll2grew.conllq import ReservedAnnotation, parse_conllu_sentence
from conll2grew.syntax import (
    Arrow,
    EdgeClause,
    Identifier,
    Feature,
    FeatureEquals,
    NodeClause,
    OrderClause,
    Request,
    string_requires_quotes,
)

type Environment = dict[str, Identifier]

PLAIN_FIELDS = ('form', 'lemma', 'upos', 'xpos')


def extract_features(token: conllu.Token) -> Iterator[Feature]:
    """
    Produces a Feature instance for every defined feature on the Token.

    Plain fields are directly translated. FEATS and MISC are split into their components,
    skipping reserved annotations in MISC.
    """
    for field in PLAIN_FIELDS:
        if value := token[field]:
            yield FeatureEquals(field, value)

    if feats := token['feats']:
        for field, value in feats.items():
            yield FeatureEquals(field, value)

    if misc := token['misc']:
        for field, value in misc.items():
            if not ReservedAnnotation.is_reserved(field):
                yield FeatureEquals(field, value)


def extract_edges(environment: Environment, tokens: list[conllu.Token]) -> Iterator[EdgeClause]:
    """
    Produces an EdgeClause for every defined edge between Token s.
    """

    for token in tokens:
        deprel: Optional[str] = token['deprel']

        if (head := token['head']) and (source := environment.get(head)):
            # Head of a token defined in sentence.
            yield EdgeClause(
                source,
                Arrow(deprel),
                environment[token['id']],
            )

        elif deprel is not None:
            # Just an edge, but head is not another fixed token of sentence.
            yield EdgeClause(
                '*',
                Arrow(deprel),
                environment[token['id']],
            )


def extract_order_clauses(
    environment: Environment, tokens: list[conllu.Token]
) -> Iterator[OrderClause]:
    """
    Produces an OrderClause for every reserved annotation
    defining order present in the given sentence.
    """

    for lhs, rhs in zip(tokens, tokens[1:]):
        if ReservedAnnotation.ORDERED.is_present_on(rhs):
            yield OrderClause(
                environment[lhs['id']],
                OrderClause.Order.PRECEDENCE,
                environment[rhs['id']],
            )

        if ReservedAnnotation.SUBSEQUENT.is_present_on(rhs):
            yield OrderClause(
                environment[lhs['id']],
                OrderClause.Order.IMMEDIATE_PRECEDENCE,
                environment[rhs['id']],
            )


def make_environment(token_ids: Iterable[str]) -> Environment:
    """
    Create a mapping from Token ID columns to Grew identifiers.
    """

    def generate_ids() -> Iterator[Identifier]:
        n = 1
        while True:
            yield f'T{n}'
            n += 1

    used_identifiers = set()
    result = {}

    for token_id in token_ids:
        target = None

        if token_id.isnumeric():
            target = 'T' + token_id
        elif not string_requires_quotes(token_id):
            target = token_id

        if target is None or target in used_identifiers:
            target = next(filter(lambda t: t not in used_identifiers, generate_ids()))

        used_identifiers.update(target)
        result[token_id] = target
    return result


def translate_to_grew(conll: str) -> Request:
    """Translate the given CoNLL-U sentence as a string into a Grew Request."""

    sentence = parse_conllu_sentence(conll)

    tokens = {token['id']: list(extract_features(token)) for token in sentence}
    environment = make_environment(tokens)

    nodes = [NodeClause(environment[key], features) for key, features in tokens.items()]
    edges = list(extract_edges(environment, sentence))
    constraints = list(extract_order_clauses(environment, sentence))

    return Request(nodes + edges + constraints)
