from conll2grew.translator import translate_to_grew


def conll_to_grew(conll: str) -> str:
    """
    Translate a CoNLL-U sentence given as a string into a Grew query.
    """
    return str(translate_to_grew(conll))
