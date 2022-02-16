import gamla
from computation_graph.composers import debug

from agenda import composers

_known = gamla.compose_left(gamla.remove(gamla.equals(composers.UNKNOWN)), tuple)


def _any_true(args):
    known_values = _known(args)
    if len(known_values) < len(args):
        return any(known_values) or composers.UNKNOWN
    return any(args)


def _all_true(args):
    known_values = _known(args)
    if not known_values:
        return composers.UNKNOWN
    if not all(known_values):
        return False
    if len(known_values) < len(args):
        return composers.UNKNOWN
    return True


any_true = composers.combine_state(_any_true)
all_true = composers.combine_state(_all_true)
first_known = composers.combine_state(
    debug.name_callable(
        gamla.compose_left(
            _known,
            gamla.ternary(gamla.nonempty, gamla.head, gamla.just(composers.UNKNOWN)),
        ),
        "first_known",
    )
)
