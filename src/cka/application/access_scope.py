from cka.domain.retrieval import AccessScope
from cka.domain.source_repository import SourceRepository
from cka.domain.user import ACCESS_LEVELS_BY_ROLE


def build_access_scope_for_user(
    user_id: str, role: str, source_repository: SourceRepository
) -> AccessScope:
    """The real document-ACL enforcement point (ADR-009): a source is only in
    scope if it's approved/ingestible AND its access_level is one the role is
    allowed to see (the Access Matrix in domain/user.py). Authorization
    happens here, before any retrieval query runs — never as a post-filter.
    """
    allowed_levels = ACCESS_LEVELS_BY_ROLE.get(role, frozenset())
    allowed = frozenset(
        source.id
        for source in source_repository.list_sources()
        if source.status == "approved"
        and source.allowed_for_ingestion
        and source.access_level in allowed_levels
    )
    return AccessScope(user_id=user_id, role=role, allowed_source_ids=allowed)
