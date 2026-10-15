"""Race detector: counts saves the backend confirmed that later vanished.

Every simulated editor loads one of a few "hot" projects and adds a key date with a
label nobody else uses. Adds of distinct labels never conflict in the three-way merge
(backend/app/merge.py), so every save the backend answers 200 for must still be on the
record when the run ends. A missing label was silently overwritten by a concurrent
save inside the GET→PUT window (DECISIONS.md, risk 1).

Saves that end in 502 are tracked separately: after repeated upstream 504s nobody
knows whether they landed, so they cannot count as lost. Saves that end in 503 waited
too long for another save of the same project to finish; nothing was written.

Production runs several backend instances behind a load balancer. To play that, set
BACKEND_HOSTS to a comma-separated list of base URLs: each request picks one at random.

Run it single-process (no --processes / distributed mode): the ledger lives in memory.
The process exits 1 if any confirmed save was lost, 0 otherwise.
"""

import os
import random
import uuid
from collections import defaultdict
from datetime import date, timedelta

import requests
from locust import HttpUser, between, events, task
from locust.runners import WorkerRunner

HOT_PROJECTS = int(os.environ.get("HOT_PROJECTS", "2"))
EDITABLE_FIELDS = ("name", "sector", "country", "stage", "key_dates")
BACKEND_HOSTS = [h.rstrip("/") for h in os.environ.get("BACKEND_HOSTS", "").split(",") if h]

# Scopes labels to this run, so runs against an upstream that was not restarted do not mix.
RUN_ID = uuid.uuid4().hex[:6]

hot_ids: list[str] = []
confirmed: dict[str, set[str]] = defaultdict(set)  # project id -> labels saved with 200
ambiguous: dict[str, set[str]] = defaultdict(set)  # project id -> labels whose save gave 502
busy: dict[str, int] = defaultdict(int)  # project id -> saves refused with 503
lost_total = 0


@events.test_start.add_listener
def pick_hot_projects(environment, **kwargs):
    if isinstance(environment.runner, WorkerRunner):
        return
    response = requests.get(f"{environment.host}/api/projects", timeout=10)
    response.raise_for_status()
    hot_ids[:] = [p["id"] for p in response.json()[:HOT_PROJECTS]]
    print(f"race detector run {RUN_ID}: hot projects {', '.join(hot_ids)}")


class Editor(HttpUser):
    # Short waits keep many saves overlapping on the same few records.
    wait_time = between(0, 0.5)

    @task
    def add_key_date(self):
        project_id = random.choice(hot_ids)
        loaded = self.client.get(f"{_instance()}/api/projects/{project_id}", name="/api/projects/[id]")
        if not loaded.ok:
            return
        base = {field: loaded.json()[field] for field in EDITABLE_FIELDS}
        label = f"lt-{RUN_ID}-{uuid.uuid4().hex[:8]}"
        new_date = (date(2030, 1, 1) + timedelta(days=random.randrange(3650))).isoformat()
        yours = base | {"key_dates": base["key_dates"] + [{"label": label, "date": new_date}]}

        with self.client.put(
            f"{_instance()}/api/projects/{project_id}",
            json={"base": base, "yours": yours},
            name="/api/projects/[id] (save)",
            catch_response=True,
        ) as saved:
            if saved.status_code == 200:
                if any(kd["label"] == label for kd in saved.json()["key_dates"]):
                    confirmed[project_id].add(label)
                else:
                    saved.failure("200 response does not contain the added key date")
            elif saved.status_code == 502:
                ambiguous[project_id].add(label)
            elif saved.status_code == 503:
                busy[project_id] += 1
            elif saved.status_code == 409:
                saved.failure("unexpected conflict: adds of distinct labels should always merge")


@events.test_stop.add_listener
def report(environment, **kwargs):
    global lost_total
    if isinstance(environment.runner, WorkerRunner):
        return

    print(f"\n=== race detector, run {RUN_ID} ===")
    print(f"{'project':<12}{'confirmed':>10}{'lost':>7}{'lost %':>8}{'502s':>7}{'502s landed':>13}{'503s':>7}")
    total_confirmed = 0
    for project_id in hot_ids:
        present = _labels_on_record(environment.host, project_id)
        lost = confirmed[project_id] - present
        landed = ambiguous[project_id] & present
        total_confirmed += len(confirmed[project_id])
        lost_total += len(lost)
        rate = 100 * len(lost) / len(confirmed[project_id]) if confirmed[project_id] else 0.0
        print(
            f"{project_id:<12}{len(confirmed[project_id]):>10}{len(lost):>7}{rate:>7.1f}%"
            f"{len(ambiguous[project_id]):>7}{len(landed):>13}{busy[project_id]:>7}"
        )
    rate = 100 * lost_total / total_confirmed if total_confirmed else 0.0
    print(f"\n{lost_total} of {total_confirmed} confirmed saves were silently lost ({rate:.1f}%).")


@events.quitting.add_listener
def exit_code(environment, **kwargs):
    # Only lost updates fail the run. 502s and 503s are the backend working as designed.
    if not isinstance(environment.runner, WorkerRunner):
        environment.process_exit_code = 1 if lost_total else 0


def _labels_on_record(host: str, project_id: str) -> set[str]:
    # Read back through the backend; its GET passes the upstream's record through.
    for _ in range(3):
        response = requests.get(f"{host}/api/projects/{project_id}", timeout=10)
        if response.ok:
            return {kd["label"] for kd in response.json()["key_dates"]}
    response.raise_for_status()
    return set()


def _instance() -> str:
    # Empty means "the --host", which Locust prepends to relative paths.
    return random.choice(BACKEND_HOSTS) if BACKEND_HOSTS else ""
