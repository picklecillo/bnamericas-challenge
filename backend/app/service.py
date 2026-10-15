"""Saving an edit safely on top of an upstream that keeps no versions.

Every attempt reads the upstream's current state and merges the user's edit onto it
(see app.merge). A 504 on PUT may or may not have landed, so we read again: if the
upstream now holds what we sent, we are done; otherwise the next attempt merges onto
whatever is there, which never re-applies a landed write blindly or clobbers a
concurrent one.

Known gap: between our GET and PUT another writer (another instance, the nightly
import) can still slip in and be overwritten. See DECISIONS.md.
"""

from app.merge import merge
from app.models import Conflict, Editable, ProjectDetail, SaveRequest
from app.upstream import UpstreamClient, UpstreamError, UpstreamTimeout

MAX_ATTEMPTS = 3


class SaveConflict(Exception):
    def __init__(self, conflicts: list[Conflict], current: ProjectDetail):
        self.conflicts = conflicts
        self.current = current


async def save_edit(upstream: UpstreamClient, project_id: str, request: SaveRequest) -> ProjectDetail:
    current = await upstream.get_project(project_id)
    for _ in range(MAX_ATTEMPTS):
        result = merge(base=request.base, theirs=Editable.model_validate(current), yours=request.yours)
        if result.conflicts:
            raise SaveConflict(result.conflicts, ProjectDetail.model_validate(current))
        body = result.merged.model_dump(mode="json") | {"linked_companies": current["linked_companies"]}
        try:
            return ProjectDetail.model_validate(await upstream.put_project(project_id, body))
        except UpstreamTimeout:
            current = await upstream.get_project(project_id)
            if Editable.model_validate(current) == result.merged:
                return ProjectDetail.model_validate(current)
    raise UpstreamError(f"save of {project_id} did not go through after {MAX_ATTEMPTS} attempts")
