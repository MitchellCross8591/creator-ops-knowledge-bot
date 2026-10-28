from typing import Any, Literal

try:
    from pydantic import BaseModel, Field
except ModuleNotFoundError:
    class BaseModel:
        """Small source-tree fallback; installed applications use Pydantic."""

        def __init__(self, **values: Any) -> None:
            fields = self.__class__.__annotations__
            unknown = values.keys() - fields.keys()
            missing = fields.keys() - values.keys()
            if unknown:
                raise TypeError(f"Unexpected fields: {', '.join(sorted(unknown))}")
            for name in missing:
                default = getattr(self.__class__, name, ...)
                if default is ...:
                    raise TypeError(f"Missing required field: {name}")
                values[name] = default
            for name, value in values.items():
                setattr(self, name, value)

        def model_dump(self) -> dict[str, Any]:
            return {
                name: value.model_dump() if isinstance(value, BaseModel) else value
                for name, value in vars(self).items()
            }

    def Field(default: Any = ..., **constraints: Any) -> Any:
        return default


class ProcessingJob(BaseModel):
    job_id: str = Field(min_length=1)
    state: Literal["queued", "processing", "completed", "failed"]


class CreatorDelivery(BaseModel):
    creator: str = Field(min_length=1)
    state: Literal["draft", "approved", "delivered"]


class MediaAsset(BaseModel):
    asset_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    transcript: str = Field(min_length=1)
    processing: ProcessingJob
    delivery: CreatorDelivery


class IngestResult(BaseModel):
    asset_id: str
    state: Literal["searchable"]
    passages: int


class KnowledgeQuestion(BaseModel):
    question: str = Field(min_length=1)
    creator: str | None = None
    top_k: int = Field(default=4, ge=1, le=10)


class KnowledgeAnswer(BaseModel):
    answer: str
    asset_ids: list[str]
    context_count: int


def is_searchable(asset: MediaAsset) -> bool:
    return asset.processing.state == "completed" and asset.delivery.state in {
        "approved",
        "delivered",
    }


def split_transcript(text: str, words_per_passage: int = 180) -> list[str]:
    words = text.split()
    return [
        " ".join(words[start : start + words_per_passage])
        for start in range(0, len(words), words_per_passage)
    ]
