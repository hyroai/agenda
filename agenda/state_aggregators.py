from typing import Callable
import gamla
from agenda import missing_cg_utils, composers
from computation_graph import base_types


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
