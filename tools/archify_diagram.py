import json

from helpers.plugins import get_plugin_config
from helpers.tool import Response, Tool
from usr.plugins.archify.helpers import archify


class ArchifyDiagram(Tool):
    async def execute(self, type="", diagram=None, title="", open_canvas=None, **kwargs):
        config = archify.effective_config(get_plugin_config(archify.PLUGIN_NAME, agent=self.agent) or {})
        diagram_type = str(type or "").strip().lower()

        if isinstance(diagram, str):
            try:
                diagram = json.loads(diagram)
            except ValueError:
                return self._error("diagram must be a JSON object (not a string that fails to parse).")
        if diagram_type not in archify.DIAGRAM_TYPES:
            return self._error("type must be one of: " + ", ".join(archify.DIAGRAM_TYPES))
        if not isinstance(diagram, dict) or not diagram:
            return self._error("diagram must be a non-empty Archify JSON object following the type's schema.")

        self.log.update(heading=f"Archify · Rendering {diagram_type} diagram")
        try:
            record = await archify.render(diagram_type, diagram, str(title or ""), config)
        except (ValueError, RuntimeError) as error:
            return self._error(str(error))

        if not record["ok"]:
            self.log.update(heading=f"Archify · {diagram_type} validation failed")
            return Response(
                message=json.dumps({
                    "ok": False,
                    "type": diagram_type,
                    "candidate": record["candidate"],
                    "errors": record.get("errors", []),
                    "hint": f"Fix the listed fields against {archify.RUNTIME}/schemas/{diagram_type}.schema.json and call archify_diagram again with the full corrected diagram.",
                }, ensure_ascii=False),
                break_loop=False,
            )

        want_canvas = config["canvas_enabled"] and (
            bool(open_canvas) if open_canvas is not None else config["auto_open_canvas"]
        )
        card = {
            "id": record["id"],
            "type": diagram_type,
            "title": record["title"],
            "html": record["html"],
            "bytes": record["bytes"],
            "checks": record["checks"],
            "warnings": record["warnings"],
            "quality": record["quality"],
            "chat": bool(config["chat_results"]),
            "preview": bool(config["inline_preview"]),
            "canvas": bool(config["canvas_enabled"]),
            "open_canvas": bool(want_canvas),
        }
        self.log.update(
            heading=f"Archify · {record['title']}",
            _archify_result=card,
        )
        return Response(
            message=json.dumps({
                "ok": True,
                "id": record["id"],
                "type": diagram_type,
                "title": record["title"],
                "html": record["html"],
                "checks": record["checks"],
                "shown_in": [p for p, on in (("chat", card["chat"]), ("canvas", want_canvas)) if on] or ["file"],
                "note": "Diagram rendered. In your response, link the HTML with its absolute path and add a one-line takeaway; do not paste the JSON.",
            }, ensure_ascii=False),
            break_loop=False,
        )

    def _error(self, message: str) -> Response:
        self.log.update(heading="Archify · Request error")
        return Response(message=json.dumps({"ok": False, "error": message}), break_loop=False)
