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
    nodes: list[NodeClause], tokens: list[conllu.Token]
) -> Iterator[OrderClause]:
    """
    Produces an OrderClause for every reserved annotation
    defining order present in the given sentence.
    """

    for i in range(1, len(tokens)):
        token = tokens[i]

        if ReservedAnnotation.ORDERED.is_present_on(token):
            yield OrderClause(
                nodes[i - 1].label,
                OrderClause.Order.PRECEDENCE,
                nodes[i].label,
            )

        if ReservedAnnotation.SUBSEQUENT.is_present_on(token):
            yield OrderClause(
                nodes[i - 1].label,
                OrderClause.Order.IMMEDIATE_PRECEDENCE,
                nodes[i].label,
            )


def find_identifier(used_identifiers: set[Identifier], token: conllu.Token) -> Identifier:
    """
    Finds an identifier to use for the given token.
    """

    def generate_ids() -> Iterator[Identifier]:
        n = 1
        while True:
            yield f'T{n}'
            n += 1

    target = None
    if token_id := token['id']:
        if token_id.isnumeric():
            target = f'T{token_id}'
        elif not string_requires_quotes(token_id):
            target = token_id

    if target is None or target in used_identifiers:
        generator = generate_ids()

        target = next(generator)
        while target in used_identifiers:
            target = next(generator)
    return target


def extract_nodes_and_environment(
    tokens: list[conllu.Token],
) -> tuple[list[NodeClause], Environment]:
    """
    Creates NodeClause instances for all given tokens and produces an environment mapping
    CoNLL-U IDs to NodeClause identifiers.
    """
    nodes: list[NodeClause] = []
    environment: Environment = {}

    assigned_identifiers = set()
    for token in tokens:
        identifier = find_identifier(assigned_identifiers, token)
        assigned_identifiers.add(identifier)

        if token_id := token['id']:
            environment[token_id] = identifier

        nodes.append(NodeClause(identifier, list(extract_features(token))))

    return nodes, environment


def translate_to_grew(conll: str) -> Request:
    """Translate the given CoNLL-U sentence as a string into a Grew Request."""

    sentence = parse_conllu_sentence(conll)

    nodes, environment = extract_nodes_and_environment(sentence)
    edges = list(extract_edges(environment, sentence))
    constraints = list(extract_order_clauses(nodes, sentence))

    return Request(nodes + edges + constraints)
