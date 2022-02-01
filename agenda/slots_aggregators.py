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


def combinator_for_state_participated_and_utter(aggregator: Callable):
    @composers.composer([composers.state, composers.utter, composers.participated])
    def combinator_for_state_participated_and_utter(*graphs):
        return base_types.merge_graphs(
            composers.combine_utter_graphs(*graphs),
            composers.mark_state(
                missing_cg_utils.compose_left_many_to_one(
                    gamla.pipe(graphs, gamla.map(composers.state_sink), tuple),
                    aggregator,
                )
            ),
        )

    return combinator_for_state_participated_and_utter


any_true = combinator_for_state_participated_and_utter(_any_true)
all_true = combinator_for_state_participated_and_utter(_all_true)
