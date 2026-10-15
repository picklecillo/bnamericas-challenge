import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.upstream import UpstreamClient
from tests.fake_upstream import FakeUpstream, wide_project


@pytest.fixture
def upstream() -> FakeUpstream:
    return FakeUpstream(wide_project("P-1001"), wide_project("P-1002", name="Rio Quemen Wind Farm"))


@pytest.fixture
def api(upstream: FakeUpstream) -> TestClient:
    client = UpstreamClient(base_url="http://upstream", api_key="local-dev-key", transport=upstream.transport())
    with TestClient(create_app(client)) as test_client:
        yield test_client


def test_lists_projects_as_slim_summaries(api: TestClient):
    response = api.get("/api/projects")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "P-1001", "name": "Cerro Talvi Solar Park", "sector": "energy", "country": "Chile", "stage": "feasibility"},
        {"id": "P-1002", "name": "Rio Quemen Wind Farm", "sector": "energy", "country": "Chile", "stage": "feasibility"},
    ]


def test_returns_one_project_with_editable_fields_and_companies_only(api: TestClient):
    response = api.get("/api/projects/P-1001")

    assert response.status_code == 200
    assert response.json() == {
        "id": "P-1001",
        "name": "Cerro Talvi Solar Park",
        "sector": "energy",
        "country": "Chile",
        "stage": "feasibility",
        "key_dates": [
            {"label": "Tender launch", "date": "2026-01-10"},
            {"label": "Financial close", "date": "2026-07-29"},
        ],
        "linked_companies": [{"name": "Varelo Energia SA", "role": "owner"}],
    }


def test_unknown_project_is_404(api: TestClient):
    assert api.get("/api/projects/P-9999").status_code == 404


EDITABLE_KEYS = ("name", "sector", "country", "stage", "key_dates")


def load(api: TestClient, project_id: str = "P-1001") -> dict:
    """What an edit form holds after opening a project."""
    project = api.get(f"/api/projects/{project_id}").json()
    return {k: project[k] for k in EDITABLE_KEYS}


def save(api: TestClient, base: dict, project_id: str = "P-1001", **changes):
    return api.put(f"/api/projects/{project_id}", json={"base": base, "yours": base | changes})


def test_two_editors_changing_different_fields_both_survive(api: TestClient, upstream: FakeUpstream):
    alice_base = load(api)
    bob_base = load(api)

    assert save(api, alice_base, name="Alice's name").status_code == 200
    response = save(api, bob_base, stage="construction")

    assert response.status_code == 200
    assert response.json()["name"] == "Alice's name"
    assert response.json()["stage"] == "construction"
    assert upstream.store["P-1001"]["name"] == "Alice's name"
    assert upstream.store["P-1001"]["stage"] == "construction"


def test_same_field_conflict_is_returned_and_nothing_is_written(api: TestClient, upstream: FakeUpstream):
    alice_base = load(api)
    bob_base = load(api)
    save(api, alice_base, name="Alice's name")
    puts_before = len(upstream.puts)

    response = save(api, bob_base, name="Bob's name")

    assert response.status_code == 409
    assert response.json()["conflicts"] == [
        {"field": "name", "base": "Cerro Talvi Solar Park", "theirs": "Alice's name", "yours": "Bob's name"}
    ]
    assert response.json()["current"]["name"] == "Alice's name"
    assert len(upstream.puts) == puts_before
    assert upstream.store["P-1001"]["name"] == "Alice's name"


def test_second_saver_decides_by_resubmitting_on_the_current_state(api: TestClient, upstream: FakeUpstream):
    alice_base = load(api)
    bob_base = load(api)
    save(api, alice_base, name="Alice's name")
    current = save(api, bob_base, name="Bob's name").json()["current"]

    new_base = {k: current[k] for k in EDITABLE_KEYS}
    response = save(api, new_base, name="Bob's name")

    assert response.status_code == 200
    assert upstream.store["P-1001"]["name"] == "Bob's name"


def test_save_that_timed_out_but_landed_is_reported_as_saved(api: TestClient, upstream: FakeUpstream):
    base = load(api)
    upstream.put_outcomes = ["504_landed"]

    response = save(api, base, name="Renamed")

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"
    assert len(upstream.puts) == 1


def test_save_that_timed_out_and_was_lost_is_retried(api: TestClient, upstream: FakeUpstream):
    base = load(api)
    upstream.put_outcomes = ["504_lost"]

    response = save(api, base, name="Renamed")

    assert response.status_code == 200
    assert upstream.store["P-1001"]["name"] == "Renamed"
    assert len(upstream.puts) == 2


def test_retry_after_lost_save_keeps_a_write_that_happened_meanwhile(api: TestClient, upstream: FakeUpstream):
    base = load(api)
    upstream.put_outcomes = ["504_lost"]
    upstream.before_put = lambda: upstream.write("P-1001", stage="operation")  # e.g. the nightly import

    response = save(api, base, name="Renamed")

    assert response.status_code == 200
    assert upstream.store["P-1001"]["name"] == "Renamed"
    assert upstream.store["P-1001"]["stage"] == "operation"


def test_gives_up_with_502_when_saves_keep_timing_out(api: TestClient, upstream: FakeUpstream):
    base = load(api)
    upstream.put_outcomes = ["504_lost"] * 3

    response = save(api, base, name="Renamed")

    assert response.status_code == 502
    assert upstream.store["P-1001"]["name"] == "Cerro Talvi Solar Park"


def test_unreachable_upstream_is_502(api: TestClient, upstream: FakeUpstream):
    upstream.down = True

    assert api.get("/api/projects").status_code == 502


def test_save_preserves_linked_companies_changed_elsewhere(api: TestClient, upstream: FakeUpstream):
    base = load(api)
    companies = [{"name": "Quintora Capital SAS", "role": "financier"}]
    upstream.write("P-1001", linked_companies=companies)

    save(api, base, name="Renamed")

    assert upstream.store["P-1001"]["linked_companies"] == companies
