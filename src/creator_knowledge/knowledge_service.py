from fastapi import FastAPI, HTTPException

from .asset_workflow import AssetKnowledgeWorkflow, AssetNotReady
from .infrai_gateway import InfraiError, InfraiGateway
from .media_records import IngestResult, KnowledgeAnswer, KnowledgeQuestion, MediaAsset


service = FastAPI(title="Creator Operations Knowledge Bot")


def workflow() -> AssetKnowledgeWorkflow:
    return AssetKnowledgeWorkflow(InfraiGateway())


@service.post("/assets/ingest", response_model=IngestResult)
def ingest_asset(asset: MediaAsset) -> IngestResult:
    try:
        return workflow().ingest(asset)
    except AssetNotReady as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except InfraiError as error:
        status = error.status_code if 400 <= error.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=str(error)) from error


@service.post("/knowledge/ask", response_model=KnowledgeAnswer)
def ask_knowledge(request: KnowledgeQuestion) -> KnowledgeAnswer:
    try:
        return workflow().ask(request)
    except InfraiError as error:
        status = error.status_code if 400 <= error.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=str(error)) from error

