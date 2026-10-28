from typing import Any

from .media_records import (
    IngestResult,
    KnowledgeAnswer,
    KnowledgeQuestion,
    MediaAsset,
    is_searchable,
    split_transcript,
)


class AssetNotReady(ValueError):
    pass


class AssetKnowledgeWorkflow:
    def __init__(self, gateway: Any, collection: str = "media-operations"):
        self.gateway = gateway
        self.collection = collection

    def ingest(self, asset: MediaAsset) -> IngestResult:
        if not is_searchable(asset):
            raise AssetNotReady(
                "Asset must finish processing and receive creator delivery approval"
            )
        passages = split_transcript(asset.transcript)
        embeddings = self.gateway.embed(passages)
        dimension = len(embeddings[0])
        self.gateway.post(
            "/v1/vector/collection/create",
            {
                "collection": self.collection,
                "dimension": dimension,
                "metric": "cosine",
                "metadata": {"purpose": "creator-media-operations"},
            },
            idempotency_key=f"collection:{self.collection}",
        )
        vectors = [
            {
                "id": f"{asset.asset_id}:{index}",
                "values": embedding,
                "metadata": {
                    "asset_id": asset.asset_id,
                    "title": asset.title,
                    "creator": asset.delivery.creator,
                    "processing_job_id": asset.processing.job_id,
                    "delivery_state": asset.delivery.state,
                    "text": passage,
                },
            }
            for index, (passage, embedding) in enumerate(zip(passages, embeddings))
        ]
        self.gateway.post(
            "/v1/vector/upsert",
            {"collection": self.collection, "vectors": vectors},
            idempotency_key=f"asset:{asset.asset_id}:{asset.processing.job_id}",
        )
        return IngestResult(
            asset_id=asset.asset_id, state="searchable", passages=len(passages)
        )

    def ask(self, request: KnowledgeQuestion) -> KnowledgeAnswer:
        embedding = self.gateway.embed(request.question)[0]
        filters: dict[str, str] = {}
        if request.creator:
            filters["creator"] = request.creator
        data = self.gateway.post(
            "/v1/vector/query",
            {
                "collection": self.collection,
                "embedding": embedding,
                "top_k": request.top_k,
                "filter": filters,
                "include_metadata": True,
            },
        )
        matches = data.get("matches", []) if isinstance(data, dict) else []
        contexts = [
            str(match.get("metadata", {}).get("text", ""))
            for match in matches
            if match.get("metadata", {}).get("text")
        ]
        asset_ids = list(
            dict.fromkeys(
                str(match.get("metadata", {}).get("asset_id", ""))
                for match in matches
                if match.get("metadata", {}).get("asset_id")
            )
        )
        if not contexts:
            return KnowledgeAnswer(
                answer="The indexed records do not answer this question.",
                asset_ids=[],
                context_count=0,
            )
        return KnowledgeAnswer(
            answer=self.gateway.answer(request.question, contexts),
            asset_ids=asset_ids,
            context_count=len(contexts),
        )
