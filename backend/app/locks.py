"""One save at a time per project, across every backend instance, via Redis.

The upstream has no versions, so two saves that overlap between our GET and PUT lose
one of them (DECISIONS.md). Holding this lock around the whole save closes that window
for every writer that goes through us. It does not cover writers that skip us, such
as the nightly import.

The lock is `SET lock:project:{id} <token> NX PX <ttl>`, renewed while held, so a
crashed instance frees it within one TTL and a long save (slow GETs, 504 retries)
never outlives it. Release and renewal check the token, so we never touch a lock
another instance has taken. If Redis is down we fail closed: no save runs unguarded.
"""

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from redis.asyncio import Redis
from redis.exceptions import RedisError

log = logging.getLogger(__name__)

# Delete / extend only if the key still holds our token.
RELEASE = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) end return 0"
RENEW = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('pexpire', KEYS[1], ARGV[2]) end return 0"


class LockError(Exception):
    """The save could not be guarded, so it did not run."""


class LockBusy(LockError):
    """Another save of the same project held the lock for longer than we wait."""


class LockUnavailable(LockError):
    """Redis could not be reached."""


class ProjectLocks:
    def __init__(self, redis: Redis, ttl: float = 10.0, wait: float = 10.0, poll: float = 0.05):
        self.redis = redis
        self.ttl = ttl
        self.wait = wait
        self.poll = poll
        self._release = redis.register_script(RELEASE)
        self._renew = redis.register_script(RENEW)

    async def aclose(self) -> None:
        await self.redis.aclose()

    @asynccontextmanager
    async def hold(self, project_id: str) -> AsyncIterator[None]:
        key = f"lock:project:{project_id}"
        token = uuid.uuid4().hex
        try:
            await self._acquire(key, token)
        except RedisError as exc:
            raise LockUnavailable(str(exc)) from exc
        renewal = asyncio.create_task(self._keep_alive(key, token))
        try:
            yield
        finally:
            renewal.cancel()
            try:
                await self._release(keys=[key], args=[token])
            except RedisError:
                log.warning("could not release %s; it expires in %.0fs", key, self.ttl)

    async def _acquire(self, key: str, token: str) -> None:
        deadline = asyncio.get_running_loop().time() + self.wait
        while not await self.redis.set(key, token, nx=True, px=int(self.ttl * 1000)):
            if asyncio.get_running_loop().time() >= deadline:
                raise LockBusy(key)
            await asyncio.sleep(self.poll)

    async def _keep_alive(self, key: str, token: str) -> None:
        while True:
            await asyncio.sleep(self.ttl / 3)
            try:
                if not await self._renew(keys=[key], args=[token, int(self.ttl * 1000)]):
                    log.warning("lost %s while saving; a concurrent save may overwrite this one", key)
                    return
            except RedisError:
                log.warning("could not renew %s", key)
