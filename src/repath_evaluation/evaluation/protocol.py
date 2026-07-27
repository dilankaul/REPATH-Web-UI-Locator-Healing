"""Fixed query construction and eligibility protocol."""

from ..domain.models import MatchQuery, PagePair


def build_queries(pair: PagePair) -> list[MatchQuery]:
    queries: list[MatchQuery] = []
    for old_id, expected_id in pair.match_map.items():
        old_node = pair.old_page.resolve_node(old_id)
        eligible = old_node is not None and old_node.element_type != 1
        queries.append(
            MatchQuery(
                site=pair.site,
                old_element_id=old_id,
                expected_new_element_id=expected_id,
                eligible=eligible,
                old_node_found=old_node is not None,
            )
        )
    return queries
