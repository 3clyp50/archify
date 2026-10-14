"""Serve a rendered Archify diagram (read-only, authenticated) for iframes in chat and canvas."""

from flask import Response, send_file

import re
from pathlib import Path

from helpers.api import ApiHandler, Input, Output, Request
from helpers.plugins import get_plugin_config
from usr.plugins.archify.helpers import archify


_SVG_TITLE_RE = re.compile(r'\s*<title id="archify-diagram-title">([^<]*)</title>')


def _without_container_tooltip(html: str) -> str:
    """Drop the SVG root <title> (native hover tooltip) but keep its accessible name."""
    match = _SVG_TITLE_RE.search(html)
    if not match:
        return html
    name = match.group(1)
    html = _SVG_TITLE_RE.sub("", html, count=1)
    return html.replace(
        'aria-labelledby="archify-diagram-title archify-diagram-description"',
        f'aria-label="{name}" aria-describedby="archify-diagram-description"',
        1,
    )


class View(ApiHandler):
    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    @classmethod
    def requires_csrf(cls) -> bool:
        # Read-only GET loaded by <iframe src>, which cannot send the CSRF header.
        # Session authentication is still required.
        return False

    async def process(self, input: Input, request: Request) -> Output:
        config = archify.effective_config(get_plugin_config(archify.PLUGIN_NAME, agent=None) or {})
        record = archify.find_diagram(request.args.get("id", ""), config)
        if not record:
            return Response("Diagram not found", status=404, mimetype="text/plain")
        if request.args.get("download") == "1":
            response = send_file(record["html"], mimetype="text/html", max_age=0)
        else:
            html = Path(record["html"]).read_text(encoding="utf-8")
            response = Response(_without_container_tooltip(html), mimetype="text/html")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        if request.args.get("download") == "1":
            safe = archify.slugify(record.get("title", "diagram")) + ".html"
            response.headers["Content-Disposition"] = f'attachment; filename="{safe}"'
        return response
