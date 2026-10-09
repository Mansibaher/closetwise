from hypothesis import given, settings, strategies as st
from app.schemas import Context
from app.seed import DATA
from app.engine import candidates, diverse, conflicts, adjust, update_preferences


def closet():
    return [
        dict(
            id=str(i),
            owner_id="u",
            name=n,
            category=cat,
            slot=s,
            primary_color=col,
            warmth=w,
            formality=f,
            pattern="solid",
            weather=["dry", "rain", "wind"],
            laundry="dirty" if i == 30 else "unavailable" if i == 31 else "clean",
            archived=False,
        )
        for i, (n, cat, s, col, w, f) in enumerate(DATA)
    ]


def test_demo_and_one_item_substitution():
    c = Context()
    ws = closet()
    ranked, error = candidates(ws, c, "u")
    assert not error
    boards = diverse(ranked)
    assert len(boards) == 3
    for items, _ in boards:
        assert not conflicts(items, c, "u")
        assert {g["id"] for g in items} <= {g["id"] for g in ws}
    items = boards[0][0]
    result = adjust(items, ws, c, "u", "casual")
    assert result
    updated, old, new, _ = result
    assert len({g["id"] for g in items} ^ {g["id"] for g in updated}) == 2
    assert old["slot"] == new["slot"] and new["formality"] < old["formality"]
    assert not conflicts(updated, c, "u")


def test_warmer_replacement():
    ws = closet()
    c = Context(required=["0", "8", "14", "19"])
    items = [g for g in ws if g["id"] in c.required]
    assert adjust(items, ws, c, "u", "warmer") is None
    c.required = ["0", "8", "14"]
    result = adjust(items, ws, c, "u", "warmer")
    assert result and result[2]["warmth"] > result[1]["warmth"]


def test_required_and_template_conflicts():
    ws = closet()
    for required, code in [
        (["30"], "REQUIRED_ITEM_UNAVAILABLE"),
        (["31"], "REQUIRED_ITEM_UNAVAILABLE"),
        (["0", "1"], "INCOMPATIBLE_REQUIRED_ITEMS"),
        (["0", "24"], "INCOMPATIBLE_REQUIRED_ITEMS"),
        (["fake"], "REQUIRED_ITEM_UNAVAILABLE"),
    ]:
        assert candidates(ws, Context(required=required), "u")[1][0] == code
    for required in [["24"], ["0", "8"]]:
        ranked, error = candidates(ws, Context(required=required), "u")
        assert not error
        assert all(set(required) <= {g["id"] for g in items} for items, _ in ranked)


def test_ownership_and_laundry():
    ws = closet()
    ws[0]["owner_id"] = "other"
    ranked, _ = candidates(ws, Context(), "u")
    assert all(g["id"] not in ("0", "30", "31") for items, _ in ranked for g in items)


def test_rain_wind_and_impossible():
    ws = closet()
    c = Context(precipitation="rain", wind=30)
    ranked, error = candidates(ws, c, "u")
    assert not error
    assert all(not conflicts(items, c, "u") for items, _ in ranked)
    for g in ws:
        if g["slot"] == "shoes" and g["formality"] == 4:
            g["weather"] = ["dry"]
    assert candidates(
        ws, Context(min_formality=4, max_formality=4, precipitation="rain"), "u"
    )[1]


def test_sparse_feedback_skips_and_ranking_change():
    ws = closet()
    c = Context()
    ranked, _ = candidates(ws, c, "u", exhaustive=True)
    v, n = update_preferences([0.0] * 4, 0, ranked[0][0], "skipped")
    assert v == [0.0] * 4 and n == 0
    v, n = update_preferences(v, n, ranked[0][0], "liked")
    assert max(map(abs, v)) < 0.1
    before = {tuple(g["id"] for g in items) for items, _ in ranked}
    for _ in range(30):
        v, n = update_preferences(v, n, ranked[0][0], "disliked", "too formal")
    after, _ = candidates(ws, c, "u", v, exhaustive=True)
    assert before == {tuple(g["id"] for g in items) for items, _ in after}
    assert [g["id"] for g in ranked[0][0]] != [g["id"] for g in after[0][0]]


@settings(max_examples=35, deadline=None)
@given(
    st.floats(min_value=-10, max_value=40, allow_nan=False),
    st.integers(0, 4),
    st.sampled_from(["dry", "rain"]),
)
def test_constraint_invariants(temp, minimum, rain):
    ws = closet()
    c = Context(temperature=temp, min_formality=minimum, precipitation=rain)
    ranked, _ = candidates(ws, c, "u", beam=40)
    for items, _ in ranked:
        assert not conflicts(items, c, "u")
        for direction in ["warmer", "cooler", "casual", "formal"]:
            result = adjust(items, ws, c, "u", direction)
            if result:
                changed, old, new, _ = result
                assert not conflicts(changed, c, "u")
                assert len({g["id"] for g in items} ^ {g["id"] for g in changed}) == 2
                assert not ({old["id"], new["id"]} & set(c.required))
        break
