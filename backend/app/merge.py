"""Three-way merge of one user's edit against whatever the upstream holds now.

For every field: if only one side changed it since `base`, that change wins. If both
changed it to different values, it is a conflict and the user saving now must decide.

Each key date is its own field, identified by its label. A missing label counts as the
value `None`, so adding, removing and moving a date all follow the same rule.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.models import Conflict, Editable, KeyDate

SCALAR_FIELDS = ("name", "sector", "country", "stage")


@dataclass
class MergeResult:
    merged: Editable
    conflicts: list[Conflict] = field(default_factory=list)


def merge(base: Editable, theirs: Editable, yours: Editable) -> MergeResult:
    conflicts: list[Conflict] = []

    def pick(name: str, b: Any, t: Any, y: Any) -> Any:
        if y == b or y == t:
            return t
        if t == b:
            return y
        conflicts.append(Conflict(field=name, base=b, theirs=t, yours=y))
        return t

    merged = theirs.model_copy()
    for name in SCALAR_FIELDS:
        setattr(merged, name, pick(name, getattr(base, name), getattr(theirs, name), getattr(yours, name)))

    b_dates, t_dates, y_dates = _by_label(base), _by_label(theirs), _by_label(yours)
    merged_dates: dict[str, date] = {}
    for label in {**b_dates, **t_dates, **y_dates}:
        value = pick(f"key_dates:{label}", b_dates.get(label), t_dates.get(label), y_dates.get(label))
        if value is not None:
            merged_dates[label] = value
    merged.key_dates = [
        KeyDate(label=label, date=d) for label, d in sorted(merged_dates.items(), key=lambda kv: (kv[1], kv[0]))
    ]

    return MergeResult(merged=merged, conflicts=conflicts)


def _by_label(editable: Editable) -> dict[str, date]:
    return {kd.label: kd.date for kd in editable.key_dates}
