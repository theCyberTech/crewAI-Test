"""Knowledge collections must be isolated per crew, matching memory namespacing."""

from __future__ import annotations

from typing import Any

import pytest

from crewai.agent.core import Agent
from crewai.crew import Crew
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from crewai.knowledge.storage.base_knowledge_storage import BaseKnowledgeStorage
import crewai.knowledge.storage.factory as knowledge_factory
from crewai.knowledge.utils.knowledge_utils import (
    agent_knowledge_collection_name,
    crew_knowledge_collection_name,
    resolve_crew_name,
)
from crewai.rag.types import SearchResult


class TestCrewKnowledgeCollectionName:
    def test_default_and_none_keep_historical_crew_collection(self) -> None:
        assert crew_knowledge_collection_name(None) == "crew"
        assert crew_knowledge_collection_name("crew") == "crew"

    def test_named_crew_is_sanitized(self) -> None:
        assert crew_knowledge_collection_name("Research Crew") == "research-crew"
        assert crew_knowledge_collection_name("Alpha") == "alpha"


class TestAgentKnowledgeCollectionName:
    def test_standalone_and_default_crew_keep_role(self) -> None:
        assert agent_knowledge_collection_name("Researcher") == "Researcher"
        assert agent_knowledge_collection_name("Researcher", None) == "Researcher"
        assert agent_knowledge_collection_name("Researcher", "crew") == "Researcher"

    def test_named_crew_prefixes_sanitized_role(self) -> None:
        assert (
            agent_knowledge_collection_name("Technical Specialist", "Research Crew")
            == "research-crew__technical-specialist"
        )


class TestResolveCrewName:
    def test_none_and_empty_string(self) -> None:
        assert resolve_crew_name(None) is None
        assert resolve_crew_name("") is None

    def test_string_crew_ref(self) -> None:
        assert resolve_crew_name("Research Crew") == "Research Crew"

    def test_object_with_name(self) -> None:
        class _Crew:
            name = "alpha"

        assert resolve_crew_name(_Crew()) == "alpha"


class _InMemoryKnowledgeStorage(BaseKnowledgeStorage):
    """Minimal store keyed by collection name so isolation can be asserted."""

    collection_name: str | None = None
    documents_by_collection: dict[str, list[str]]

    def search(
        self,
        query: list[str],
        limit: int = 5,
        metadata_filter: dict[str, Any] | None = None,
        score_threshold: float = 0.6,
    ) -> list[SearchResult]:
        needle = " ".join(query).lower()
        docs = self.documents_by_collection.get(self.collection_name or "", [])
        hits = [doc for doc in docs if needle in doc.lower()][:limit]
        return [{"content": doc, "score": 1.0} for doc in hits]

    async def asearch(
        self,
        query: list[str],
        limit: int = 5,
        metadata_filter: dict[str, Any] | None = None,
        score_threshold: float = 0.6,
    ) -> list[SearchResult]:
        return self.search(query, limit, metadata_filter, score_threshold)

    def save(self, documents: list[str]) -> None:
        key = self.collection_name or ""
        self.documents_by_collection.setdefault(key, []).extend(documents)

    async def asave(self, documents: list[str]) -> None:
        self.save(documents)

    def reset(self) -> None:
        self.documents_by_collection.pop(self.collection_name or "", None)

    async def areset(self) -> None:
        self.reset()


@pytest.fixture
def isolated_knowledge_store() -> dict[str, list[str]]:
    documents_by_collection: dict[str, list[str]] = {}

    def factory(
        _embedder: object, collection_name: str | None
    ) -> _InMemoryKnowledgeStorage:
        return _InMemoryKnowledgeStorage(
            collection_name=collection_name,
            documents_by_collection=documents_by_collection,
        )

    original = knowledge_factory._factory
    knowledge_factory.set_knowledge_storage_factory(factory)
    try:
        yield documents_by_collection
    finally:
        knowledge_factory.set_knowledge_storage_factory(original)


def test_named_crews_do_not_share_knowledge_hits(
    isolated_knowledge_store: dict[str, list[str]],
) -> None:
    alpha = Crew(
        name="alpha-research",
        knowledge_sources=[
            StringKnowledgeSource(content="alpha secret token ALPHA_ONLY")
        ],
    )
    beta = Crew(
        name="beta-support",
        knowledge_sources=[
            StringKnowledgeSource(content="beta secret token BETA_ONLY")
        ],
    )

    assert alpha.knowledge is not None
    assert beta.knowledge is not None
    assert alpha.knowledge.storage is not None
    assert beta.knowledge.storage is not None
    assert alpha.knowledge.storage.collection_name != beta.knowledge.storage.collection_name
    assert alpha.knowledge.storage.collection_name == "alpha-research"
    assert beta.knowledge.storage.collection_name == "beta-support"

    alpha_hits = alpha.knowledge.query(["ALPHA_ONLY"])
    beta_hits = beta.knowledge.query(["ALPHA_ONLY"])
    assert any("ALPHA_ONLY" in hit["content"] for hit in alpha_hits)
    assert not any("ALPHA_ONLY" in hit["content"] for hit in beta_hits)


def test_default_crew_name_keeps_historical_collection(
    isolated_knowledge_store: dict[str, list[str]],
) -> None:
    crew = Crew(
        knowledge_sources=[StringKnowledgeSource(content="shared default knowledge")]
    )

    assert crew.knowledge is not None
    assert crew.knowledge.storage is not None
    assert crew.knowledge.storage.collection_name == "crew"


def test_same_role_agents_in_named_crews_use_distinct_collections(
    isolated_knowledge_store: dict[str, list[str]],
) -> None:
    alpha_agent = Agent(
        role="Researcher",
        goal="research",
        backstory="alpha",
        knowledge_sources=[StringKnowledgeSource(content="alpha agent token A_AGENT")],
    )
    beta_agent = Agent(
        role="Researcher",
        goal="research",
        backstory="beta",
        knowledge_sources=[StringKnowledgeSource(content="beta agent token B_AGENT")],
    )
    alpha_agent.crew = "Alpha Research"
    beta_agent.crew = "Beta Support"
    alpha_agent.set_knowledge()
    beta_agent.set_knowledge()

    assert alpha_agent.knowledge is not None
    assert beta_agent.knowledge is not None
    assert alpha_agent.knowledge.storage is not None
    assert beta_agent.knowledge.storage is not None
    assert (
        alpha_agent.knowledge.storage.collection_name
        == "alpha-research__researcher"
    )
    assert (
        beta_agent.knowledge.storage.collection_name == "beta-support__researcher"
    )

    alpha_hits = alpha_agent.knowledge.query(["A_AGENT"])
    beta_hits = beta_agent.knowledge.query(["A_AGENT"])
    assert any("A_AGENT" in hit["content"] for hit in alpha_hits)
    assert not any("A_AGENT" in hit["content"] for hit in beta_hits)


def test_standalone_agent_keeps_role_collection(
    isolated_knowledge_store: dict[str, list[str]],
) -> None:
    agent = Agent(
        role="Researcher",
        goal="research",
        backstory="solo",
        knowledge_sources=[StringKnowledgeSource(content="solo token")],
    )
    agent.set_knowledge()

    assert agent.knowledge is not None
    assert agent.knowledge.storage is not None
    assert agent.knowledge.storage.collection_name == "Researcher"
