"""Reproducible synthetic evaluation; no recognition or external services."""

import argparse, json, time, platform
from pathlib import Path
import numpy as np
from .engine import (
    candidates,
    diverse,
    features,
    conflicts,
    adjust,
    score,
    update_preferences,
)
from .schemas import Context
from .seed import DATA


def synthetic(size, seed):
    rng = np.random.default_rng(seed)
    ws = []
    # Interleave slots so small wardrobes are useful, rather than all tops.
    order = [0, 8, 14, 19, 24, 29] + [
        i for i in range(30) if i not in (0, 8, 14, 19, 24, 29)
    ]
    for i in range(size):
        name, category, slot, color, warmth, formality = DATA[order[i % 30]]
        ws.append(
            dict(
                id=f"g{i:04}",
                owner_id="synthetic",
                name=name,
                category=category,
                slot=slot,
                primary_color=color,
                pattern="solid" if rng.random() < 0.7 else "striped",
                warmth=int(rng.integers(0, 5)),
                formality=int(rng.integers(0, 5)),
                laundry="clean" if rng.random() < 0.9 else "dirty",
                weather=["dry", "rain", "wind"],
                archived=False,
            )
        )
    return ws


def utility(items, target):
    return float(features(items) @ target)


def quality(board, pool, target):
    values = [utility(p[0], target) for p in pool]
    lo, hi = min(values), max(values)
    return (utility(board, target) - lo) / (hi - lo) if hi > lo else 1.0


def diversity(boards):
    ids = [{g["id"] for g in b} for b in boards]
    return (
        float(
            np.mean(
                [
                    1 - len(a & b) / len(a | b)
                    for i, a in enumerate(ids)
                    for b in ids[i + 1 :]
                ]
            )
        )
        if len(ids) > 1
        else 0.0
    )


def evaluate(output):
    rng = np.random.default_rng(20261006)
    target = np.array([-1.8, 0.5, 0.9, 0.4])
    rows = []
    comparisons = []
    for size in [12, 24, 48, 120, 300]:
        trials = []
        for seed in range(5):
            ws = synthetic(size, seed)
            c = Context(
                temperature=[4, 12, 20, 28, 12][seed],
                min_formality=1,
                outerwear=seed != 3,
            )
            recent = {g["id"]: 1 for g in ws[:5]}
            v = [0.0] * 4
            n = 0
            # Training labels are simulated, explicitly not human judgments.
            training, _ = candidates(ws, c, "synthetic", recent=recent)
            if training:
                utilities = [utility(p[0], target) for p in training]
                median = float(np.median(utilities))
                for index in rng.integers(0, len(training), size=80):
                    board = training[int(index)][0]
                    event = "liked" if utility(board, target) >= median else "disliked"
                    v, n = update_preferences(
                        v,
                        n,
                        board,
                        event,
                        "too formal" if event == "disliked" else None,
                    )
            for mode, vector, ablation in [
                ("random_valid", [0.0] * 4, None),
                ("heuristic", [0.0] * 4, None),
                ("personalized", v, None),
                ("no_personalization", v, "no_personalization"),
                ("no_color", v, "no_color"),
                ("no_recency", v, "no_recency"),
            ]:
                if mode == "no_personalization":
                    vector = [0.0] * 4
                start = time.perf_counter()
                pool, error = candidates(ws, c, "synthetic", vector, recent)
                if pool and mode.startswith("no_"):
                    pool = sorted(
                        [
                            (b, score(b, c, vector, recent, ablation=ablation))
                            for b, _ in pool
                        ],
                        key=lambda p: p[1]["total"],
                        reverse=True,
                    )
                elapsed = (time.perf_counter() - start) * 1000
                boards = []
                if pool:
                    selected = (
                        [
                            pool[int(i)]
                            for i in rng.choice(
                                len(pool), min(3, len(pool)), replace=False
                            )
                        ]
                        if mode == "random_valid"
                        else diverse(pool)
                    )
                    boards = [p[0] for p in selected]
                adjustments = correct = improved = 0
                for board in boards:
                    for direction in ["warmer", "cooler", "casual", "formal"]:
                        result = adjust(board, ws, c, "synthetic", direction, vector)
                        if result:
                            updated, old, new, _ = result
                            adjustments += 1
                            correct += int(
                                len(
                                    {g["id"] for g in board}
                                    ^ {g["id"] for g in updated}
                                )
                                == 2
                                and not conflicts(updated, c, "synthetic")
                            )
                            attr = (
                                "warmth"
                                if direction in ("warmer", "cooler")
                                else "formality"
                            )
                            sign = 1 if direction in ("warmer", "formal") else -1
                            improved += int(sign * (new[attr] - old[attr]) > 0)
                trials.append(
                    dict(
                        mode=mode,
                        feasible=int(bool(boards)),
                        violations=sum(
                            bool(conflicts(b, c, "synthetic")) for b in boards
                        ),
                        recommendations=len(boards),
                        diversity=diversity(boards),
                        ranking_quality=quality(boards[0], pool, target)
                        if boards
                        else None,
                        latency_ms=elapsed,
                        adjustments=adjustments,
                        correct=correct,
                        improved=improved,
                    )
                )
            if size <= 24:
                bounded, _ = candidates(ws, c, "synthetic")
                exact, _ = candidates(ws, c, "synthetic", exhaustive=True)
                comparisons.append(
                    {
                        "size": size,
                        "seed": seed,
                        "exhaustive_feasible": len(exact),
                        "bounded_feasible": len(bounded),
                        "missed_all_feasible": bool(exact and not bounded),
                        "best_score_regret": round(
                            exact[0][1]["total"] - bounded[0][1]["total"], 5
                        )
                        if exact and bounded
                        else None,
                        "feasible_recall": len(bounded) / len(exact) if exact else None,
                    }
                )
        for mode in sorted({t["mode"] for t in trials}):
            ts = [t for t in trials if t["mode"] == mode]
            total = sum(t["recommendations"] for t in ts)
            adjustments = sum(t["adjustments"] for t in ts)
            rows.append(
                {
                    "wardrobe_size": size,
                    "mode": mode,
                    "feasible_rate": float(np.mean([t["feasible"] for t in ts])),
                    "violation_rate": sum(t["violations"] for t in ts) / total
                    if total
                    else None,
                    "diversity": float(np.mean([t["diversity"] for t in ts])),
                    "ranking_quality": float(
                        np.mean(
                            [
                                t["ranking_quality"]
                                for t in ts
                                if t["ranking_quality"] is not None
                            ]
                        )
                    )
                    if total
                    else None,
                    "latency_median_ms": float(
                        np.median([t["latency_ms"] for t in ts])
                    ),
                    "latency_p95_ms": float(
                        np.percentile([t["latency_ms"] for t in ts], 95)
                    ),
                    "successful_adjustments": adjustments,
                    "adjustment_correctness": sum(t["correct"] for t in ts)
                    / adjustments
                    if adjustments
                    else None,
                    "direction_improvement": sum(t["improved"] for t in ts)
                    / adjustments
                    if adjustments
                    else None,
                }
            )
    # Controlled feedback example: fixed candidate set, no novelty/recency confounds.
    ws = synthetic(48, 10)
    c = Context(min_formality=1)
    pool, _ = candidates(ws, c, "synthetic", exhaustive=True)
    v = [0.0] * 4
    n = 0
    for _ in range(60):
        v, n = update_preferences(v, n, pool[0][0], "disliked", "too formal")
    reranked = sorted(pool, key=lambda p: score(p[0], c, v)["total"], reverse=True)
    controlled = {
        "before_ids": [g["id"] for g in pool[0][0]],
        "after_ids": [g["id"] for g in reranked[0][0]],
        "before_formality": float(features(pool[0][0])[0] * 4),
        "after_formality": float(features(reranked[0][0])[0] * 4),
        "preferences": v,
        "same_feasible_candidate_ids": True,
        "training_events": n,
    }
    report = {
        "seed": 20261006,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "data": "Synthetic wardrobes and simulated preferences; no human satisfaction claim. Engine latency excludes recognition, I/O and persistence. Five wardrobe seeds per size. Ranking quality is min-max normalized oracle utility within each search pool, not a calibrated accuracy.",
        "rows": rows,
        "exhaustive_comparison": comparisons,
        "controlled_feedback": controlled,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "evaluation.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    lines = [
        "# Executed synthetic evaluation",
        "",
        report["data"],
        "",
        f"Seed: {report['seed']}; Python {report['python']}; NumPy {report['numpy']}.",
        "",
        "| Size | Method | Feasible | Violations | Diversity | Simulated quality | Median ms | Adjustment correct |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        fmt = lambda v: "n/a" if v is None else f"{v:.3f}"
        lines.append(
            f"| {r['wardrobe_size']} | {r['mode']} | {fmt(r['feasible_rate'])} | {fmt(r['violation_rate'])} | {fmt(r['diversity'])} | {fmt(r['ranking_quality'])} | {r['latency_median_ms']:.1f} | {fmt(r['adjustment_correctness'])} |"
        )
    lines += [
        "",
        "## Bounded versus exhaustive",
        "",
        "| Size | Seed | Exact count | Bounded count | Recall | Best-score regret | Missed every solution |",
        "|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in comparisons:
        lines.append(
            f"| {r['size']} | {r['seed']} | {r['exhaustive_feasible']} | {r['bounded_feasible']} | {r['feasible_recall']} | {r['best_score_regret']} | {r['missed_all_feasible']} |"
        )
    lines += [
        "",
        "## Controlled feedback",
        "",
        json.dumps(controlled, indent=2),
        "",
        "Candidate budgets can miss valid outfits, especially under weather constraints. Low synthetic quality or a personalization regression is evidence of a limitation, not a user study. Ablations use the same bounded generator and change the final ranking term; they do not isolate generator bias.",
    ]
    (output / "evaluation.md").write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps({"rows": len(rows), "report": str(output), "controlled": controlled})
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("../docs/reports"))
    evaluate(parser.parse_args().output)
