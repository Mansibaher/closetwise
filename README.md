# ClosetWise — AI Outfit Planner

**Style what I already own.** A full-stack application for a private wardrobe, constrained outfit recommendations, explainable single-item substitutions, and feedback-based personalization. Works with no paid API keys.

![Interview outfit and highlighted casual substitution](docs/screenshots/planner.png)

## Start with Docker Compose

Requirements: Docker Desktop/Engine with Compose, about 3 GB free disk space. The only published service is the Next.js app; PostgreSQL and FastAPI stay on the internal Compose network.

```sh
cp .env.example .env
docker compose up --build
```

Open **http://localhost:3000**, then **Explore the demo wardrobe**. Each visitor gets a private 32-piece photo demo. The startup command applies Alembic migrations and creates the named CLI demo account (`demo@closetwise.local` / `closetwise-demo`). Visitor demos are separate from that account. Normal accounts start empty.

Reset your own demo with the **Reset demo data** button. Reset the named account with:

```sh
docker compose exec backend python -m app.seed --reset
```

Stop with `docker compose down`. Named volumes retain the database and images. Do not delete volumes unless you intend to erase that data.

## Native development

Python 3.11–3.12 and Node.js 22.14+ are suitable. SQLite is an explicit local/testing fallback; Compose uses PostgreSQL. Run the following from the repository root (activation commands are shown separately).

```sh
python -m venv .venv
```

Activate with `.venv\Scripts\Activate.ps1` in PowerShell, or `source .venv/bin/activate` on macOS/Linux.

```sh
cd backend
python -m pip install -r requirements-lock.txt
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:3000**. Next.js forwards `/api/*` to FastAPI, including private image requests and session cookies. Native Python does not auto-load `.env`: export any custom settings into your shell. Defaults work for local SQLite and mock recognition. To use a local PostgreSQL instance, export `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/closetwise` before migration and startup. URL-encode special characters in native database passwords.

## Checks and evaluation

From `backend/`, with the Python environment activated:

```sh
python -m pytest -q
python export_openapi.py
python -m app.evaluate --output ../docs/reports
```

From `frontend/`:

```sh
npm run api:generate
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
```

Browser tests need FastAPI running at port 8000; Playwright starts the frontend itself. `openapi.json` and its generated TypeScript definitions are committed, so initial builds require no running API. Regenerate both when schemas change. Direct dependencies are pinned in `requirements.txt`; the full tested Python environment is pinned in `requirements-lock.txt`. The frontend uses `package-lock.json` and `npm ci`.

See [verification status](docs/VERIFICATION.md) for checks actually executed in the build environment and [executed synthetic evaluation](docs/reports/evaluation.md) for generated results. Recommendation latency excludes image recognition, database writes, and network I/O. Synthetic ranking results do **not** establish user satisfaction or general fashion quality.

## Demo

1. Explore the demo wardrobe.
2. Keep **job interview**, **Cool weather**, formality **2–4**, and outerwear enabled.
3. Select **Find my outfits**. Inspect three boards made from the wardrobe’s stored images.
4. Select **More casual** on the first board. One same-slot item changes; it is highlighted with an attribute-based explanation. All remaining garment IDs stay fixed.
5. Record **Liked**, **Wore**, or **Disliked** with a reason. Open **Your preferences** to inspect weights and history.
6. Generate again. Preferences change soft ranking; clean status, ownership, weather, required pieces, and dress bounds still gate every board.
7. In **Required & excluded pieces**, require **Laundry Oxford** to expose an actionable availability conflict. Require **Oxford shirt** and **Blue button-down** to expose an incompatible-slot conflict. No constraints relax automatically.

See the [three-minute interview script](docs/DEMO.md), including a deterministic warmer substitution and controlled feedback experiment.

## Repository

```text
backend/
  app/auth.py             Argon2 password hashing, signed expiring session cookies
  app/db.py               SQLAlchemy entities and sessions
  app/schemas.py          Pydantic validation and OpenAPI response contracts
  app/storage.py          Safe image processing; local/S3 storage abstraction
  app/recognition.py      Deterministic mock and optional vision provider
  app/engine.py           Constraints, bounded generation, scoring, substitutions
  app/main.py             Ownership-checked API and persistence orchestration
  app/seed.py             Local demo photography and resettable demo
  app/evaluate.py         Fixed-seed synthetic evaluation and ablations
  assets/                 32 locally bundled original garment PNGs
  migrations/             Alembic schema migration
  tests/                  Unit, API integration, image and property-based checks
frontend/
  app/                    Responsive Next.js planner, wardrobe, review, insights
  lib/                    Generated OpenAPI types and typed fetch client
  tests/                  Playwright demo and constraint-error flow
docs/                     Design, provenance, deployment, demo, reports, screenshots
compose.yaml              App + API + PostgreSQL, persistent volumes, health checks
```

FastAPI is one service with pure recommendation functions and explicit persistence boundaries. Outfit records include immutable generation-time attribute snapshots and relational item references. Adjustments re-fetch current garments and create a child outfit, preserving the original. Feedback references stable outfit records. Deleting a garment retains historical attribute snapshots but removes its image and nulls live references.

## AI/ML and deterministic engineering

The learned component is a transparent content-based preference vector updated from centered outfit features and signed feedback, with shrinkage toward a zero prior. NumPy handles feature vectors. Scikit-learn is intentionally unnecessary for this four-feature online model. Optional vision proposes editable structured attributes; the default mock does no recognition. Hard validity checks, beam search, image handling, ownership checks, substitution invariants, and explanation templates are deterministic engineering. An LLM never decides validity.

## Optional integrations

Set server-side `RECOGNITION_PROVIDER=vision`, `VISION_API_KEY`, and optionally `VISION_MODEL` and `VISION_URL`. The provider uses an OpenAI-compatible chat completion endpoint with image input and JSON-schema output. Responses are validated again with Pydantic; unknown fields and incompatible category/slot combinations fail validation. Request failures, malformed responses, missing credentials, and timeouts return `RECOGNITION_UNAVAILABLE` as a warning while retaining the upload for manual entry. No key reaches the browser. Real vision execution requires your own credentials and was not used for this build.

Set `STORAGE_BACKEND=s3`, `S3_BUCKET`, `S3_ENDPOINT_URL` when needed, and standard AWS credentials/region for a private S3-compatible bucket. Backend proxy reads enforce ownership; objects never need to be public. Local storage remains the default. S3 connectivity was not exercised in this build.

Variables are explained in [.env.example](.env.example). For a practical HTTPS VM configuration and production prerequisites, see [deployment](docs/DEPLOYMENT.md).

## Limits and tradeoffs

Warmth is ordinal, not thermal physics. Rain/wind protection and formality are user-confirmed heuristics, not safety advice or objective dress-code interpretation. Color harmony uses a simple neutral-color rule; style judgments are subjective. Recognition can be wrong, and mock values are placeholders. Sparse feedback moves weights modestly; repeated correlated signals can overfit. Skips are recorded without learning a dislike. Bounded search can miss valid or better outfits; error messages explicitly state the candidate-budget limitation. There is no virtual try-on, live weather, background removal, account recovery, or large-scale job infrastructure. The demo is a portfolio application; public deployment needs rate limiting, demo retention cleanup, backups, and ongoing dependency/security maintenance.

## License and image provenance

Project code is MIT-licensed. The 32 default demo photographs are bundled locally under the Pexels License, separate from the code license. Legacy procedural illustrations are CC0. No network image requests are needed at runtime. See [provenance](docs/IMAGE_PROVENANCE.md).

## Saved account profiles

After creating an account, complete Your profile with your name, men’s / male outfits, women’s / female outfits, or all styles, and a usual occasion. Settings are stored in the account database and restored at sign-in. The planner shows the current style with a Change shortcut. New accounts begin with an empty private wardrobe; add clothing and set each item’s clothing style (men, women, or unisex). Recommendations and replacements include the selected style plus unisex items, while All styles includes everything. Demo style labels are manually curated clothing examples, not inferred gender identities. Apply `alembic upgrade head` to upgrade existing databases through migration 0002.

## Camera photos

My wardrobe → + Add garment → Take photo opens a live camera preview after browser permission. Capture photo sends a JPEG through the same authenticated upload, normalization, review and confirmation workflow as a file upload. The camera stops after capture, cancellation or editor closure; delayed permission responses after cancellation stop their tracks immediately. Use device camera (phones) also offers a native camera picker on supporting mobile browsers. Live camera access requires HTTPS or localhost. Permission denial and missing-camera errors keep ordinary uploads available. With local recognition enabled, recognized photos are added automatically and their details remain editable. In mock mode, review the details and confirm Save; mock mode does not recognize clothing.

On local HTTP phone previews, Take photo automatically invokes the native capture file input instead of opening an unavailable live preview. Capture uses the rear-camera hint; the phone browser controls the exact picker options.

## Free local photo recognition

The preview uses CLIP on this computer, with no cloud API requests, subscription or inference charges. Install the optional local dependencies from backend/requirements-local.txt, then run backend/tools/setup_local_model.py inside backend once. Approximately 608 MB of pinned model files are downloaded; later inference does not need internet. Set RECOGNITION_PROVIDER=local before starting the backend. The ZIP excludes model binaries; the setup script reproduces them. Existing electricity, hardware and internet costs still apply.

Recognized photos are added automatically to the private wardrobe. Clothing type, color and pattern are visual estimates and remain editable. Warmth and formality are approximate category defaults, rather than verified fabric properties. Waterproofing is not assumed. Photograph one item on a plain background. Busy scenes and close-ups can be mislabeled. The model source is https://huggingface.co/Xenova/clip-vit-base-patch32 at revision d15189d7028b43f1d3e65039190477f6af591c2a, based on https://github.com/openai/CLIP.

For Docker, download the model files into backend/models/clip before building and set RECOGNITION_PROVIDER=local in .env. Cloud vision remains optional and disabled in this preview.

Gallery uploads also accept iPhone HEIC/HEIF photos and normalize them to private WebP images before local recognition.

Gallery upload preprocessing resizes browser-readable images to 1600 pixels and JPEG. The server also supports AVIF, GIF (first frame), BMP and TIFF, and retains decoded-image dimension and size checks.
