from crewai.memory.utils import sanitize_scope_name
from crewai.rag.types import SearchResult


_DEFAULT_CREW_COLLECTION = "crew"


def crew_knowledge_collection_name(crew_name: str | None) -> str:
    """Return the storage collection name for a crew's shared knowledge.

    Unnamed crews keep the historical ``crew`` collection so existing stores
    continue to resolve. Named crews are isolated from each other the same way
    memory already namespaces by ``/crew/{name}``.
    """
    return sanitize_scope_name(crew_name or _DEFAULT_CREW_COLLECTION)


def resolve_crew_name(crew: object | None) -> str | None:
    """Return a crew's display name from a Crew instance or serialized string."""
    if crew is None:
        return None
    if isinstance(crew, str):
        return crew or None
    name = getattr(crew, "name", None)
    if isinstance(name, str) and name:
        return name
    return None


def agent_knowledge_collection_name(role: str, crew_name: str | None = None) -> str:
    """Return the storage collection name for an agent's knowledge.

    Standalone agents and agents on the default-named crew keep the historical
    role-based collection. Agents on a named crew are prefixed so the same
    role cannot leak embeddings across crews.
    """
    sanitized_crew = sanitize_scope_name(crew_name) if crew_name else None
    if sanitized_crew and sanitized_crew != _DEFAULT_CREW_COLLECTION:
        return f"{sanitized_crew}__{sanitize_scope_name(role)}"
    return role


def extract_knowledge_context(knowledge_snippets: list[SearchResult]) -> str:
    """Extract knowledge from the task prompt."""
    valid_snippets = [
        result["content"]
        for result in knowledge_snippets
        if result and result.get("content")
    ]
    snippet = "\n".join(valid_snippets)
    return f"Additional Information: {snippet}" if valid_snippets else ""
