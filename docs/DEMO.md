# Three-minute interview demo

**0:00–0:25 — Product and ownership**

“ClosetWise styles what I already own. It is a modular monolith, sized for one student: Next.js, FastAPI, and PostgreSQL. These 32 real garment photographs are clearly labeled demo data. Real uploads go through the same wardrobe and constraint pipeline.” Open the isolated demo, then briefly show the gallery and clean/dirty labels.

**0:25–1:05 — Constraints and explanation**

Select job interview and cool weather: 12°C, 8 km/h wind, dry, formality 2–4, outerwear on. Generate three boards. Open “Why this works.” “The occasion suggests defaults; my selected bounds control feasibility. Ownership, laundry, slots, requirements and weather are deterministic. Color, coherence, comfort and preferences only rank valid boards.”

**1:05–1:35 — Exactly one change**

Press More casual on the first outfit. Show the highlighted replacement and its numeric formality change. “One same-slot garment changed, all other IDs stayed fixed, and the board still passes the interview bounds.” Optionally show the API response old/new IDs in the browser developer tools.

For a deterministic warmer example, reset and require Oxford shirt, Charcoal trousers, and Brown dress shoes; generate; use the board with Navy blazer and press Make this warmer. Warm beige coat supplies warmth 4 instead of 2. If a different outerwear board appears first, select the blazer board. Do not imply a layer was added.

**1:35–2:10 — Feedback mechanism**

Record Liked or Disliked with too formal. Open preferences and show the modest weight change. “The online content model shrinks toward a five-event prior. Skips record uncertainty without becoming dislikes. Wore also influences garment rotation.” Generate again, while explaining that novelty and recency can also change order.

Open `docs/reports/evaluation.md` for the controlled experiment. “Here the candidate set is fixed, so feedback's ranking effect is isolated. These labels are simulated, not a user-satisfaction study.” Show before/after garment IDs and mean formality.

**2:10–2:35 — Fail honestly**

Require Laundry Oxford and generate. Show the availability conflict. Replace that requirement with Oxford shirt plus Blue button-down to show incompatible slots. “We retain your rules. An impossible adjustment keeps the original board and explains the failure.”

**2:35–3:00 — Engineering evidence**

Show the test and evaluation reports. “The engine uses capped pools and beam search; I measured its loss against exhaustive search on small wardrobes. Tests check ownership isolation and substitution invariants. AI is used for optional recognition suggestions and feedback learning; it never authorizes a hard constraint violation. Next steps are stronger feasibility pruning, human-reviewed preference labels, and deployment abuse controls.”
