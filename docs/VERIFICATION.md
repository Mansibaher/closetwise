# Executed verification — October 6, 2026

Environment: Windows, Python 3.11.9, Node.js 22.14.0. Browser checks used Playwright's Chromium. API/integration checks used SQLite with foreign-key enforcement; the documented Docker deployment uses PostgreSQL.

| Check | Observed result |
|---|---|
| Backend unit, integration, image and property tests | **21 passed** |
| Playwright interview → substitution → feedback, manual entry/conflict, mobile/keyboard checks | **3 passed** |
| Generated OpenAPI client and TypeScript checking | Passed |
| Next.js optimized production build | Passed |
| Alembic migration applied to local SQLite database | Passed |
| Alembic model/migration drift check | No new upgrade operations |
| Docker Compose configuration validation | Passed |
| Python unused/undefined import checks | Passed |
| npm dependency installation audit | 0 vulnerabilities reported at install time |
| Fixed-seed evaluation | Executed; 30 method/size summaries, 10 small-wardrobe exhaustive comparisons, controlled feedback example |
| Desktop and mobile screenshots | Captured during passing browser tests and inspected |

One Starlette test-client deprecation warning was emitted for its httpx adapter; tests completed successfully. This is not an application runtime failure.

Docker Desktop did not provide a responsive engine in this environment. **Docker images and live PostgreSQL behavior were not verified here.** A GitHub Actions workflow includes a PostgreSQL migration/drift/API smoke check and browser flows against PostgreSQL for execution after publishing this repository. That workflow has been authored, not run on GitHub. `tools/smoke_postgres.py` requires a migrated disposable PostgreSQL database.

Real paid vision, S3 connectivity, HTTPS deployment, backup/restore, and real-user preference quality were not exercised. The optional vision request/schema behavior was tested with mocked HTTP responses; malformed output was rejected and API fallback was checked. Real seeded garment photographs are bundled locally under the Pexels License.

## Reading the evaluation

The synthetic run found no hard-constraint violations in returned recommendations and correct strict-direction, one-item replacements for successful adjustments. Some small wardrobes were infeasible; the exact comparison distinguishes true empty feasible sets from search misses. The bounded search returns only a subset of larger feasible sets. Five wardrobe seeds per size are a small sample, and latency varies by host/load. The labels reflect a simulated preference function, so favorable personalized ranking results are evidence of the mechanism under that simulation only.

The controlled fixed-candidate example changed the top outfit's mean formality from **4.0 to 1.25** after 60 simulated "too formal" dislikes. The experiment does not alter feasibility or claim that repeated real-user feedback would have the same effect. Exact IDs and learned weights appear in the JSON report.

## Real photo update

Replaced all 32 default illustrations with visually reviewed Pexels photographs and locally prepared full-size WebP images and thumbnails. Migrated 416 existing demo records while preserving IDs, laundry state, uploads and feedback. Photo labels and shoe category now match the pictured garments. Re-ran all 21 backend tests (3.70s), all three browser checks (8.4s), production build, generated API types, TypeScript check and fixed-seed evaluation. Desktop and mobile screenshots were refreshed.

## Saved profile update

Applied migration 0002 to the local database; Alembic reported no model drift. All 23 backend tests passed, including profile persistence, account isolation, style filtering and incompatible required items. All four browser checks passed, including signup, profile save, refresh and logout/login restoration. Production build and generated types passed. Profile screenshot captured. PostgreSQL migration remains for CI execution.

Search display update: production build passed; browser checks cover successful output, conflicting required pieces and empty account wardrobes. Search errors now appear beside results, old boards clear before a new search, and completed searches scroll into view.

Camera update: production build passed. Six browser checks passed, including JPEG capture from a synthetic browser camera, authenticated save and reload, stopped media tracks after capture, and permission denial with file-upload fallback. No real user camera was activated in testing. Physical phone cameras and browser-specific native capture pickers were not exercised.

Local recognition update: full CLIP model loaded and inference executed on CPU. All 25 backend tests passed, including pixel-dependent classification and authenticated local upload/save. A browser test against the live local provider passed: photo upload automatically added White shirt with its image, closed the details dialog, and survived refresh. Sample checks also found wrong color/pattern estimates and a cropped dress mislabeled as a shirt; this is a prototype, not a validated clothing classifier. No paid API calls were made.

HEIC update: registered pillow-heif decoder and added iPhone HEIC/HEIF to the gallery picker. All 26 backend tests passed, including HEIC conversion and metadata removal; production build passed. A live HEIC photo upload at the LAN preview was successfully decoded, recognized by the local model, and saved as White shirt. Original size and dimension safeguards remain enforced.

Gallery format update: 30 backend tests passed with AVIF, GIF, BMP and TIFF conversion in addition to HEIC. Production build passed. Browser tests against the local model passed for JPEG and AVIF input, automatic recognition/save and persistence after refresh. Browser-readable photos are resized to 1600 pixels and converted to JPEG before upload; undecodable browser formats fall back to server decoding. Physical iPhone picker behavior remains for user verification.
