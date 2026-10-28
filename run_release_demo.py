import json

from creator_knowledge.asset_workflow import AssetKnowledgeWorkflow
from creator_knowledge.infrai_gateway import InfraiGateway
from creator_knowledge.media_records import (
    CreatorDelivery,
    KnowledgeQuestion,
    MediaAsset,
    ProcessingJob,
)


def main() -> None:
    workflow = AssetKnowledgeWorkflow(InfraiGateway())
    asset = MediaAsset(
        asset_id="episode-42",
        title="Autumn launch master",
        transcript=(
            "The final episode master completed loudness review. Creator Mina approved "
            "delivery to the streaming catalog for Friday at 09:00 UTC. Captions and "
            "the square cover image are included in the delivery package."
        ),
        processing=ProcessingJob(job_id="mix-884", state="completed"),
        delivery=CreatorDelivery(creator="Mina", state="approved"),
    )
    indexed = workflow.ingest(asset)
    answered = workflow.ask(
        KnowledgeQuestion(question="When is Mina's episode scheduled for delivery?")
    )
    print(json.dumps({"indexed": indexed.model_dump(), "answer": answered.model_dump()}, indent=2))


if __name__ == "__main__":
    main()

