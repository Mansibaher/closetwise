# Executed synthetic evaluation

Synthetic wardrobes and simulated preferences; no human satisfaction claim. Engine latency excludes recognition, I/O and persistence. Five wardrobe seeds per size. Ranking quality is min-max normalized oracle utility within each search pool, not a calibrated accuracy.

Seed: 20261006; Python 3.11.9; NumPy 2.4.3.

| Size | Method | Feasible | Violations | Diversity | Simulated quality | Median ms | Adjustment correct |
|---:|---|---:|---:|---:|---:|---:|---:|
| 12 | heuristic | 0.200 | 0.000 | 0.107 | 1.000 | 0.1 | 1.000 |
| 12 | no_color | 0.200 | 0.000 | 0.107 | 1.000 | 0.1 | 1.000 |
| 12 | no_personalization | 0.200 | 0.000 | 0.107 | 1.000 | 0.1 | 1.000 |
| 12 | no_recency | 0.200 | 0.000 | 0.107 | 1.000 | 0.1 | 1.000 |
| 12 | personalized | 0.200 | 0.000 | 0.107 | 1.000 | 0.1 | 1.000 |
| 12 | random_valid | 0.200 | 0.000 | 0.080 | 0.000 | 0.1 | 1.000 |
| 24 | heuristic | 1.000 | 0.000 | 0.841 | 0.452 | 9.2 | 1.000 |
| 24 | no_color | 1.000 | 0.000 | 0.776 | 0.753 | 11.7 | 1.000 |
| 24 | no_personalization | 1.000 | 0.000 | 0.841 | 0.452 | 12.3 | 1.000 |
| 24 | no_recency | 1.000 | 0.000 | 0.836 | 0.753 | 11.9 | 1.000 |
| 24 | personalized | 1.000 | 0.000 | 0.776 | 0.753 | 9.2 | 1.000 |
| 24 | random_valid | 1.000 | 0.000 | 0.794 | 0.581 | 9.2 | 1.000 |
| 48 | heuristic | 1.000 | 0.000 | 0.955 | 0.598 | 36.3 | 1.000 |
| 48 | no_color | 1.000 | 0.000 | 0.910 | 0.685 | 38.1 | 1.000 |
| 48 | no_personalization | 1.000 | 0.000 | 0.955 | 0.598 | 38.6 | 1.000 |
| 48 | no_recency | 1.000 | 0.000 | 0.888 | 0.717 | 37.9 | 1.000 |
| 48 | personalized | 1.000 | 0.000 | 0.910 | 0.685 | 35.3 | 1.000 |
| 48 | random_valid | 1.000 | 0.000 | 0.847 | 0.466 | 35.3 | 1.000 |
| 120 | heuristic | 1.000 | 0.000 | 0.990 | 0.371 | 385.8 | 1.000 |
| 120 | no_color | 1.000 | 0.000 | 0.981 | 0.799 | 390.8 | 1.000 |
| 120 | no_personalization | 1.000 | 0.000 | 0.990 | 0.371 | 393.7 | 1.000 |
| 120 | no_recency | 1.000 | 0.000 | 0.981 | 0.799 | 390.9 | 1.000 |
| 120 | personalized | 1.000 | 0.000 | 0.981 | 0.799 | 423.8 | 1.000 |
| 120 | random_valid | 1.000 | 0.000 | 0.970 | 0.376 | 414.4 | 1.000 |
| 300 | heuristic | 1.000 | 0.000 | 0.971 | 0.298 | 595.4 | 1.000 |
| 300 | no_color | 1.000 | 0.000 | 1.000 | 0.922 | 628.6 | 1.000 |
| 300 | no_personalization | 1.000 | 0.000 | 0.971 | 0.298 | 623.7 | 1.000 |
| 300 | no_recency | 1.000 | 0.000 | 1.000 | 0.922 | 625.7 | 1.000 |
| 300 | personalized | 1.000 | 0.000 | 1.000 | 0.922 | 623.0 | 1.000 |
| 300 | random_valid | 1.000 | 0.000 | 0.892 | 0.427 | 628.4 | 1.000 |

## Bounded versus exhaustive

| Size | Seed | Exact count | Bounded count | Recall | Best-score regret | Missed every solution |
|---:|---:|---:|---:|---:|---:|---|
| 12 | 0 | 0 | 0 | None | None | False |
| 12 | 1 | 4 | 4 | 1.0 | 0.0 | False |
| 12 | 2 | 0 | 0 | None | None | False |
| 12 | 3 | 0 | 0 | None | None | False |
| 12 | 4 | 0 | 0 | None | None | False |
| 24 | 0 | 69 | 63 | 0.9130434782608695 | 0.0 | False |
| 24 | 1 | 126 | 126 | 1.0 | 0.0 | False |
| 24 | 2 | 124 | 124 | 1.0 | 0.0 | False |
| 24 | 3 | 56 | 56 | 1.0 | 0.0 | False |
| 24 | 4 | 168 | 141 | 0.8392857142857143 | 0.0 | False |

## Controlled feedback

{
  "before_ids": [
    "g0036",
    "g0013",
    "g0002",
    "g0003"
  ],
  "after_ids": [
    "g0000",
    "g0031",
    "g0019",
    "g0033"
  ],
  "before_formality": 4.0,
  "after_formality": 1.25,
  "preferences": [
    -0.6923076923076923,
    -0.11538461538461539,
    -0.46153846153846156,
    -0.23076923076923078
  ],
  "same_feasible_candidate_ids": true,
  "training_events": 60
}

Candidate budgets can miss valid outfits, especially under weather constraints. Low synthetic quality or a personalization regression is evidence of a limitation, not a user study. Ablations use the same bounded generator and change the final ranking term; they do not isolate generator bias.