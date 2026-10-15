import asyncio

import fakeredis
import pytest

from app.locks import LockBusy, LockUnavailable, ProjectLocks
from app.models import SaveRequest
from app.service import save_edit
from app.upstream import UpstreamClient
from tests.fake_upstream import FakeUpstream, wide_project


def run(coro):
    return asyncio.run(coro)


def make_locks(server: fakeredis.FakeServer | None = None, **options) -> ProjectLocks:
    return ProjectLocks(fakeredis.FakeAsyncRedis(server=server or fakeredis.FakeServer()), **options)


def test_lock_is_released_after_the_block():
    async def scenario():
        locks = make_locks()
        async with locks.hold("P-1001"):
            assert await locks.redis.exists("lock:project:P-1001")
        assert not await locks.redis.exists("lock:project:P-1001")

    run(scenario())


def test_second_holder_waits_for_the_first():
    async def scenario():
        locks = make_locks()
        order: list[str] = []

        async def holder(name: str, delay: float):
            await asyncio.sleep(delay)
            async with locks.hold("P-1001"):
                order.append(f"{name} in")
                await asyncio.sleep(0.1)
                order.append(f"{name} out")

        await asyncio.gather(holder("a", 0), holder("b", 0.01))
        assert order == ["a in", "a out", "b in", "b out"]

    run(scenario())


def test_other_projects_do_not_wait():
    async def scenario():
        locks = make_locks(wait=0.05)
        async with locks.hold("P-1001"):
            async with locks.hold("P-1002"):
                pass

    run(scenario())


def test_gives_up_when_the_lock_stays_taken():
    async def scenario():
        locks = make_locks(wait=0.1)
        async with locks.hold("P-1001"):
            with pytest.raises(LockBusy):
                async with locks.hold("P-1001"):
                    pass

    run(scenario())


def test_lock_is_renewed_while_held():
    async def scenario():
        locks = make_locks(ttl=0.2, wait=0.05)
        async with locks.hold("P-1001"):
            await asyncio.sleep(0.5)  # well past the TTL
            with pytest.raises(LockBusy):
                async with locks.hold("P-1001"):
                    pass

    run(scenario())


def test_release_never_deletes_a_lock_someone_else_holds():
    async def scenario():
        locks = make_locks()
        async with locks.hold("P-1001"):
            # Our lock expired and another instance took it.
            await locks.redis.set("lock:project:P-1001", "someone-else")
        assert await locks.redis.get("lock:project:P-1001") == b"someone-else"

    run(scenario())


def test_unreachable_redis_fails_closed():
    async def scenario():
        server = fakeredis.FakeServer()
        server.connected = False
        with pytest.raises(LockUnavailable):
            async with make_locks(server).hold("P-1001"):
                pass

    run(scenario())


def test_overlapping_saves_on_one_project_both_survive():
    """The lost update `make race` measures: two saves read the same record, the
    second PUT drops the first one's key date. With the lock they run one after the other."""

    async def scenario():
        upstream = FakeUpstream(wide_project("P-1001"))
        upstream.get_delay = 0.05
        client = UpstreamClient(base_url="http://upstream", api_key="local-dev-key", transport=upstream.transport())
        locks = make_locks()
        base = {k: upstream.store["P-1001"][k] for k in ("name", "sector", "country", "stage", "key_dates")}

        def adding(label: str) -> SaveRequest:
            yours = base | {"key_dates": base["key_dates"] + [{"label": label, "date": "2030-01-01"}]}
            return SaveRequest.model_validate({"base": base, "yours": yours})

        await asyncio.gather(
            save_edit(client, locks, "P-1001", adding("Alice's date")),
            save_edit(client, locks, "P-1001", adding("Bob's date")),
        )
        await client.aclose()
        return {kd["label"] for kd in upstream.store["P-1001"]["key_dates"]}

    assert {"Alice's date", "Bob's date"} <= run(scenario())
