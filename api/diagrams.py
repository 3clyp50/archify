"""List recent Archify diagrams and report runtime status for the canvas surface."""

from helpers.api import ApiHandler, Input, Output, Request
from helpers.plugins import get_plugin_config
from usr.plugins.archify.helpers import archify


class Diagrams(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        config = archify.effective_config(get_plugin_config(archify.PLUGIN_NAME, agent=None) or {})
        action = input.get("action", "list")
        if action == "status":
            return {"ok": True, "status": archify.runtime_status(), "config": config}
        if action == "get":
            record = archify.find_diagram(input.get("id", ""), config)
            if not record:
                return {"ok": False, "error": "Diagram not found"}
            return {"ok": True, "diagram": {k: record.get(k) for k in ("id", "type", "title", "created", "html", "bytes", "checks")}}
        if action == "list":
            limit = max(1, min(int(input.get("limit", 30) or 30), 100))
            return {"ok": True, "diagrams": archify.list_diagrams(config, limit), "config": config}
        return {"ok": False, "error": f"Unknown action: {action}"}
