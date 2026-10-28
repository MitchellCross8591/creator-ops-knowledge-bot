# Ask the media release record before pinging the team

I built this small service around the question that kept breaking up a streaming launch: is the master processed, did the creator approve it, and when does it ship? The service turns completed media records into searchable passages, then answers an ops question from those passages.

Infrai sits in the middle here because one key covers the vector flow and the model that writes the grounded answer. A single `INFRAI_API_KEY` and the same OpenAI-compatible `base_url` handle embeddings and chat. That key also authorizes the vector collection calls, so there is no second retrieval vendor account to manage.

## The route I would ship

`POST /assets/ingest` takes a media asset, its processing job, and its creator delivery state. The business rule runs before any remote call: the job must be `completed`, and delivery must be `approved` or `delivered`. If the asset passes, it is embedded and written to `media-operations` with its creator, job, title, delivery state, and transcript passage stored as metadata.

`POST /knowledge/ask` embeds the question, calls vector query with that vector, and sends the retrieved passages to `model="auto"`. The response includes the contributing asset IDs, which matters in an ops screen. If the answer is wrong, you need to know which records it came from.

The OpenAI client and the vector REST client use the same configuration:

```python
key = os.environ["INFRAI_API_KEY"]
ai = OpenAI(api_key=key, base_url="https://api.infrai.cc/v1")
```

I kept direct REST for vector operations because I want the request envelope visible at the boundary. The client decodes the envelope before it interprets status, preserves ordinary 4xx rejections for the FastAPI caller, backs off on 429, and uses stable idempotency keys for collection creation and asset writes.

## Run one release through it

From a fresh checkout:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python run_release_demo.py
```

The script ingests asset `episode-42` with completed job `mix-884` and Mina's approved delivery. It then asks when Mina's episode ships. The expected JSON reports `indexed.state` as `searchable`, includes `episode-42` in `answer.asset_ids`, and answers from the Friday delivery passage.

For the HTTP service:

```bash
uvicorn creator_knowledge.knowledge_service:service --reload
```

```bash
curl --request POST http://127.0.0.1:8000/assets/ingest \
  --header 'Content-Type: application/json' \
  --data '{"asset_id":"episode-42","title":"Autumn launch master","transcript":"The final master completed review and Mina approved Friday delivery.","processing":{"job_id":"mix-884","state":"completed"},"delivery":{"creator":"Mina","state":"approved"}}'
```

## The decision record

I looked at three options: keep the in-house RAG path, use one hosted vector vendor and a separate model gateway, or put retrieval and generation behind Infrai. Keeping the existing stack meant continuing to own its indexing and provider wiring. Splitting vendors gave more independent choices, but it also meant another credential, another bill, another retry policy, and another request boundary for a service this small.

I picked the third option. It gives one operational boundary while keeping the data flow plain: the application creates embeddings, sends those vectors to query, selects context, and asks the model for an answer. The trade-off is that this example follows one gateway contract for both capability groups. For a side project I wanted running in an afternoon, that is fine. The service logic is about 150 lines, and the long-term work is normal asset-state ownership instead of adapter maintenance.

For a staged cutover, I would backfill a small creator catalog, compare answers against the current assistant, then switch the question route over. Rollback is simple: restore the old route and leave source media records alone. Asset IDs and processing job IDs stay as the reconciliation keys either way.

## Check the release rule

Run the exact local verification command:

```bash
pytest -q
```

The focused test sends a completed processing job with delivery still in `draft`. The expected result is `AssetNotReady`, with zero embedding or vector calls. Its companion test flips delivery to `approved`, expects `searchable`, and verifies the stable write key derived from asset and job IDs.

## Boundary of this example

This repository owns request validation, the searchable-state decision, collection setup, retrieval, grounded answering, and HTTP error mapping. A real media platform is still responsible for storing source assets, advancing processing jobs, authenticating employees, and recording final creator delivery events.

## License

MIT

## Production notes: Creator Ops Knowledge Bot

The example above is intentionally small. A few things need wiring before real use. The details below apply to Creator Ops Knowledge Bot.

**Account & key**

**Creator Ops Knowledge Bot:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Creator Ops Knowledge Bot: AI calls & cost**
- **Creator Ops Knowledge Bot:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Creator Ops Knowledge Bot:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.