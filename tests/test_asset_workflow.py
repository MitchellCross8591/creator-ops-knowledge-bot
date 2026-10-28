from typing import Any

import pytest

from creator_knowledge.asset_workflow import AssetKnowledgeWorkflow, AssetNotReady
from creator_knowledge.media_records import CreatorDelivery, MediaAsset, ProcessingJob


class RecordingGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any], str | None]] = []

    def post(
        self, path: str, payload: dict[str, Any], idempotency_key: str | None = None
    ) -> Any:
        self.calls.append((path, payload, idempotency_key))
        return {}

    def embed(self, texts: str | list[str]) -> list[list[float]]:
        items = [texts] if isinstance(texts, str) else texts
        return [[0.25, 0.75] for _ in items]

    def answer(self, question: str, context: list[str]) -> str:
        return "unused"


def test_processing_complete_still_waits_for_creator_approval() -> None:
    gateway = RecordingGateway()
    workflow = AssetKnowledgeWorkflow(gateway)
    asset = MediaAsset(
        asset_id="episode-42",
        title="Autumn launch master",
        transcript="The mastered episode is scheduled for Friday.",
        processing=ProcessingJob(job_id="mix-884", state="completed"),
        delivery=CreatorDelivery(creator="Mina", state="draft"),
    )

    with pytest.raises(AssetNotReady, match="creator delivery approval"):
        workflow.ingest(asset)

    assert gateway.calls == []


def test_approved_asset_becomes_searchable_with_stable_write_key() -> None:
    gateway = RecordingGateway()
    workflow = AssetKnowledgeWorkflow(gateway)
    asset = MediaAsset(
        asset_id="episode-42",
        title="Autumn launch master",
        transcript="The mastered episode is scheduled for Friday.",
        processing=ProcessingJob(job_id="mix-884", state="completed"),
        delivery=CreatorDelivery(creator="Mina", state="approved"),
    )

    result = workflow.ingest(asset)

    assert result.state == "searchable"
    assert gateway.calls[-1][0] == "/v1/vector/upsert"
    assert gateway.calls[-1][2] == "asset:episode-42:mix-884"

