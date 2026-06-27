# CarrierGuard live web demo

A small, public web demo of CarrierGuard. It exposes the **real** `core/` vetting
pipeline over HTTP so anyone can vet **any** US motor carrier by its MC number and
see the live decision, the findings, and the dated audit record.

There is **no LLM in this path**: the verdict is computed by the same versioned
policy the agent uses (`core/policy.py` + `core/scorer.py`) from live FMCSA data
(`core/fmcsa/client.py`). The full LLM agent lives in [`../app`](../app). Keeping
the public demo deterministic makes it free to run, impossible to "break" with a
bad prompt, and safe to leave open for judges.

## Endpoints
- `GET /`: the demo UI ([`live.html`](live.html)).
- `GET /api/vet?mc=<MC>`: fetch the carrier from the live FMCSA QCMobile API,
  score it, and return the decision as JSON. Responses are cached for an hour; a
  light global rate limit and graceful error handling protect the WebKey.

## Security
The FMCSA WebKey is read from the `FMCSA_WEBKEY` environment variable (injected
from Secret Manager in production) and never reaches the browser. No keys in code.

## Run locally
```bash
pip install -r webdemo/requirements.txt
FMCSA_WEBKEY=your-webkey uvicorn webdemo.main:app --port 8787
# open http://127.0.0.1:8787
```

## Deploy (Cloud Run)
The image needs `core/` in its build context, so build from the repository root
with the included [`Dockerfile`](Dockerfile):

```bash
gcloud run deploy carrierguard-demo \
  --source . \
  --region us-east1 \
  --allow-unauthenticated \
  --set-secrets FMCSA_WEBKEY=fmcsa-webkey:latest
```

(If the repository root already contains another `Dockerfile`, build the demo
image explicitly with `docker build -f webdemo/Dockerfile -t carrierguard-demo .`
and deploy that image with `gcloud run deploy --image`.)
