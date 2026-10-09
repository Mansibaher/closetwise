# Design decisions

## Acceptance contract

The default demo returns three feasible cool-weather interview outfits, supports a same-slot casual replacement under formality bounds 2–4, and records feedback against a persisted outfit. All garment, upload, image, outfit, reset, and feedback operations enforce owner scope. Impossible adjustments return an error and leave the original record intact. Core operation requires no API keys.

## Architecture and data

A modular monolith keeps deployment to a frontend, one API process, and PostgreSQL. The API owns authentication, image handling, wardrobe CRUD, recommendation persistence, and feedback. The engine receives plain garment dictionaries and a validated context, so it is independently testable and benchmarkable. JSON attributes avoid 15 repetitive joins while indexed owner, slot, and laundry columns support scoped access; those duplicated fields are set together on every write. A future schema could promote frequently queried attributes into columns.

Entities: users; garments; recognition suggestions (original proposal and first confirmed attributes); outfits (context, score breakdown, image/attribute snapshots, parent reference); outfit items (one per slot); feedback events (event, reason, feature snapshot); preference state (weights and informative-event count). Timestamps use UTC. Foreign keys prevent dangling relational references, with `SET NULL` on deleted garment references and cascading outfit-item/feedback deletion during demo reset. Historical metadata survives ordinary garment deletion; private images do not.

Passwords use pwdlib's Argon2 implementation, and PyJWT signs 8-hour HS256 sessions. Cookies are HTTP-only and SameSite=Lax; production adds Secure and rejects the development secret. Auth follows established FastAPI primitives; no custom cryptography. The same-origin Next.js proxy avoids browser token storage. Mutation requests with an unexpected Origin are rejected. Missing Origin is allowed for CLI clients. Public deployments require an edge rate limit and abuse controls.

## Attribute scales and weather

Warmth: **0 airy**, **1 light**, **2 medium**, **3 warm**, **4 insulated**. Formality: **0 relaxed**, **1 casual**, **2 smart casual**, **3 business**, **4 formal**. These are subjective user-confirmed ordinal labels. Every selected garment, including accessories, must be within the chosen formality interval.

Effective temperature is `temperature − min(wind_kmh / 10, 5)`. Body warmth sums top+bottom or one-piece, plus outerwear, excluding shoes/accessories. Allowed intervals are:

| Effective °C | Body warmth interval |
|---|---|
| below 5 | 7–16 |
| 5 to below 15 | 4–12 |
| 15 to below 23 | 2–8 |
| 23 or above | 0–4 |

Rain requires rain-suitable shoes and any selected outerwear. Wind of at least 25 km/h requires wind-suitable outerwear. Seasons are descriptive metadata, not an additional constraint: temperature and protection flags are authoritative. The dry flag does not restrict dry-weather use. This intentionally simple heuristic is reproducible and explainable but not a comfort guarantee; a one-piece's single ordinal value does not perfectly compare with two garments, which can make cold-weather one-piece boards infeasible.

Occasion supplies UI defaults only. Changing it does not authorize bypassing the actual min/max formality. Required items, explicit exclusions, ownership, clean laundry status, archive state, slot compatibility, requested optional slots, duplicates, and weather checks are hard constraints. Required optional-slot garments are included even if their toggle is off. Optional slots otherwise participate only when requested; layer addition/removal is outside adjustment scope.

## Search and ranking

Two templates: top+bottom+shoes and one-piece+shoes, with requested outerwear/accessory slots. Preflight rejects unavailable required IDs, duplicate-slot requirements, and mixed one-piece/separates requirements. Pools first prune ownership/availability/dress bounds and rain/wind protection. Required slots are fixed; other slots cap at **24** candidates. Per-slot ordering uses preference fit, then descending formality and stable ID. Beam search expands slots sequentially and retains **160** partial boards using soft scores. Complete boards run all hard checks before ranking or persistence.

With N garments, S≤5 slots, cap C=24 and beam B=160, pool filtering is O(N); pool sorting O(N log N); expansion is O(SBC), with sorting O(SBC log(BC)). Scoring adds a small O(S²) pairwise-color term. Working storage is O(BCS); result storage is O(BS). Two templates multiply by a constant. Exhaustive search is available only to the evaluation harness and tests, with O(product of slot-pool sizes) complexity.

Partial scores are not admissible bounds. The engine can discard a partial board needed for eventual weather feasibility or optimality, and the pool cap can exclude a useful garment. No-feasible errors mean no solution was found under this budget, not a proof of impossibility. Required items bypass the pool cap. The evaluation compares bounded/exact feasible counts and best-score regret on small wardrobes. An exact fallback or stronger interval pruning is a future improvement.

Feature vector: mean formality/4, mean warmth/4, color compatibility, fraction of solid-pattern pieces. Color compatibility is the fraction of unordered color pairs that match or contain a neutral (black, white, navy, gray, beige, brown). Secondary color and user tags are stored but are not currently ranked. Coherence is `1 − formality range/4`. Comfort is closeness to the midpoint of the feasible body-warmth interval. Novelty is 0 for a garment-ID set found in the last 100 generated outfits, otherwise 1. Rotation is 1 minus the fraction worn in the past seven days.

Total score = `.22 color + .22 coherence + .18 comfort + .35 preference_dot_features + .10 novelty + .10 rotation`. The signed personal component can be negative; the total is a ranking value, not a probability. The results retain separate components. Up to three boards are chosen greedily by score minus `.25 * maximum Jaccard similarity` to already selected boards; no identical ID sets repeat. Diversity may sacrifice some raw score.

## Exactly one substitution

For each unfixed selected item, scan all same-slot wardrobe alternatives. The requested warmth/formality value must strictly improve, the new complete board must pass all hard checks, and the other IDs must remain identical. Choose the best soft score minus penalties for color (.08), pattern (.06), and unrelated ordinal change (.04 per step). Complexity is O(SNS²) using the complete constraint and feature checks; it is small for a personal wardrobe. The response returns old/new IDs, a child outfit, the direction, and an explanation using actual values. No layer can be added or removed. A failed substitution creates no outfit and reports `NO_VALID_SINGLE_ITEM_ADJUSTMENT`.

## Feedback and personalization

Liked = +1, disliked = −1, wore = +.6. Skipped is recorded but contributes no label and no informative-event count. For centered feature vector `x = features − .5`, evidence is `label*x`. Explicit reasons override the relevant coordinate: too formal/casual → −/+ .75 formality; too cold/warm → +/− .75 warmth; don't like colors → + .75 harmony preference.

Update `w_new = clip((w_old*(count+5) + evidence)/(count+6), −1, 1)`. This is a regularized running average with a five-event zero prior. It is transparent, bounded, and stable with sparse feedback, but not a calibrated model of taste. Feedback stores generation-time features. Wore separately updates recency through its event timestamp. Constraints never use these weights.

The controlled evaluation fixes the feasible candidate set and removes novelty/recency variation, then repeatedly supplies simulated "too formal" dislikes and shows before/after top IDs and mean formality. It demonstrates the mechanism without attributing ordinary regenerate differences to learning alone. The UI shows weights and feedback history; the generated report holds the reproducible controlled example.

## Recognition and storage

The mock provider ignores pixel content and returns a deterministic placeholder, visibly labeled. The optional vision provider reads normalized WebP bytes and proposes an Attributes schema. Pydantic validates the complete response again. Errors leave a persisted private upload available for manual confirmation. Proposal/confirmation pairs support later human-reviewed attribute evaluation; this project makes no recognition-accuracy claim.

Image normalization accepts decoded JPEG/PNG/WebP, up to 8 MiB, 64–6000 px per dimension and at most 24 MP. Orientation is applied before resizing to 1600 px; metadata is cleared; the image is re-encoded as WebP with a 400 px thumbnail. Storage uses random keys and a strict key pattern. Local and private S3 implementations expose bytes only through an owner-checked route.

## Limitations

Search approximation, subjective ordinal scales, simple color rules, uncalibrated vision output, correlated/sparse feedback, and synthetic evaluation limit claims. The application has no account recovery or social sharing. Public demo accounts accumulate unless an operator expires them; abandoned upload suggestions likewise need retention cleanup. Preference updates use read-modify-write and are suited to one small deployment; concurrent feedback requests for the same account should be serialized or updated with row locking at higher traffic. All image work and optional vision calls happen synchronously. A background queue is deliberately omitted for student scope.

## Account style profile

Users have a validated JSON profile with display name, outfit style and default occasion. `PUT /profile` updates only the authenticated account. `GET /auth/me` and sign-in responses restore it. Garments have an editable men/women/unisex audience label (legacy user clothes default to unisex). The recommendation API filters the account wardrobe by style before hard-constraint validation and generation; incompatible required pieces raise a conflict. Adjustments reject fixed garments incompatible with a changed profile and request regeneration. Profile changes preserve wardrobe and learned feedback. No demographic or gender classification is performed from photographs. Migration 0002 adds the users.profile column on SQLite and PostgreSQL.
