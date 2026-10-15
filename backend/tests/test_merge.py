from app.merge import merge
from app.models import Editable


def editable(**overrides) -> Editable:
    fields = {
        "name": "Cerro Talvi Solar Park",
        "sector": "energy",
        "country": "Chile",
        "stage": "feasibility",
        "key_dates": [
            {"label": "Tender launch", "date": "2026-01-10"},
            {"label": "Financial close", "date": "2026-07-29"},
        ],
    }
    return Editable.model_validate(fields | overrides)


def test_takes_users_change_when_nobody_else_changed_the_field():
    base = editable()
    yours = editable(name="Renamed")

    result = merge(base=base, theirs=base, yours=yours)

    assert result.conflicts == []
    assert result.merged.name == "Renamed"


def test_keeps_both_changes_when_users_change_different_fields():
    base = editable()
    theirs = editable(stage="tender")
    yours = editable(name="Renamed")

    result = merge(base=base, theirs=theirs, yours=yours)

    assert result.conflicts == []
    assert result.merged.name == "Renamed"
    assert result.merged.stage == "tender"


def test_reports_conflict_when_both_changed_the_same_field_differently():
    base = editable()
    theirs = editable(name="Their name")
    yours = editable(name="Your name")

    result = merge(base=base, theirs=theirs, yours=yours)

    assert [c.model_dump() for c in result.conflicts] == [
        {"field": "name", "base": "Cerro Talvi Solar Park", "theirs": "Their name", "yours": "Your name"}
    ]


def test_no_conflict_when_both_made_the_same_change():
    base = editable()
    theirs = editable(name="Same")
    yours = editable(name="Same")

    result = merge(base=base, theirs=theirs, yours=yours)

    assert result.conflicts == []
    assert result.merged.name == "Same"


def dates(**by_label) -> list[dict]:
    return [{"label": label.replace("_", " "), "date": d} for label, d in by_label.items()]


def key_dates_of(result) -> dict[str, str]:
    return {kd.label: kd.date.isoformat() for kd in result.merged.key_dates}


def test_keeps_both_key_date_changes_when_different_labels_changed():
    base = editable()
    theirs = editable(key_dates=dates(Tender_launch="2026-02-01", Financial_close="2026-07-29"))
    yours = editable(key_dates=dates(Tender_launch="2026-01-10", Financial_close="2026-09-30"))

    result = merge(base=base, theirs=theirs, yours=yours)

    assert result.conflicts == []
    assert key_dates_of(result) == {"Tender launch": "2026-02-01", "Financial close": "2026-09-30"}


def test_reports_conflict_when_both_moved_the_same_key_date():
    base = editable()
    theirs = editable(key_dates=dates(Tender_launch="2026-02-01", Financial_close="2026-07-29"))
    yours = editable(key_dates=dates(Tender_launch="2026-03-01", Financial_close="2026-07-29"))

    result = merge(base=base, theirs=theirs, yours=yours)

    assert [c.model_dump(mode="json") for c in result.conflicts] == [
        {"field": "key_dates:Tender launch", "base": "2026-01-10", "theirs": "2026-02-01", "yours": "2026-03-01"}
    ]


def test_adds_a_new_key_date_alongside_their_change():
    base = editable()
    theirs = editable(key_dates=dates(Tender_launch="2026-02-01", Financial_close="2026-07-29"))
    yours = editable(key_dates=dates(
        Tender_launch="2026-01-10", Financial_close="2026-07-29", Construction_start="2027-01-01"
    ))

    result = merge(base=base, theirs=theirs, yours=yours)

    assert result.conflicts == []
    assert key_dates_of(result) == {
        "Tender launch": "2026-02-01", "Financial close": "2026-07-29", "Construction start": "2027-01-01"
    }


def test_removing_a_key_date_someone_else_moved_is_a_conflict():
    base = editable()
    theirs = editable(key_dates=dates(Tender_launch="2026-02-01", Financial_close="2026-07-29"))
    yours = editable(key_dates=dates(Financial_close="2026-07-29"))

    result = merge(base=base, theirs=theirs, yours=yours)

    assert [c.model_dump(mode="json") for c in result.conflicts] == [
        {"field": "key_dates:Tender launch", "base": "2026-01-10", "theirs": "2026-02-01", "yours": None}
    ]


def test_removes_a_key_date_nobody_else_touched():
    base = editable()
    yours = editable(key_dates=dates(Financial_close="2026-07-29"))

    result = merge(base=base, theirs=base, yours=yours)

    assert result.conflicts == []
    assert key_dates_of(result) == {"Financial close": "2026-07-29"}


def test_rejects_duplicate_key_date_labels():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="duplicate key date label"):
        editable(key_dates=[
            {"label": "Tender launch", "date": "2026-01-10"},
            {"label": "Tender launch", "date": "2026-02-10"},
        ])
