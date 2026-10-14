## archify_diagram
Render a validated, explorable Archify diagram (standalone HTML with inline SVG, pan/zoom, search, focus, dark/light themes, PNG/SVG/WebM export) from typed JSON. The result appears as a diagram card in chat; depending on user settings it can also open in the right canvas.

Use when the user asks to draw, diagram, visualize or map a system, process, request flow, pipeline, state machine, schema, class model, hierarchy, timeline or timing breakdown, including everyday subjects with steps, parts or states. Not for numeric charts or dashboards.

args:
- `type`: one of `architecture`, `workflow`, `sequence`, `dataflow`, `lifecycle`, `erd`, `class`, `tree`, `timeline`, `waterfall`
- `diagram`: the complete Archify JSON candidate (object) for that type
- `title`: optional short human title (defaults to `meta.title`)
- `open_canvas`: optional boolean; only honored when the user enabled the canvas in plugin settings

Type router: components/services/infrastructure → `architecture`; processes, approvals, runbooks, plans → `workflow`; API call chains, back-and-forth → `sequence`; pipelines, ETL, where money or documents go → `dataflow`; status/state transitions → `lifecycle`; tables and keys → `erd`; types and members → `class`; single-parent containment → `tree`; when things happened → `timeline`; where the time went → `waterfall`. Mermaid input: author fresh Archify JSON from its topology.

Authoring (runtime at `/a0/usr/plugins/archify/runtime/archify`):
1. Before the first candidate of a type in this chat, read `references/authoring-defaults.md`, the type's example in `examples/` (e.g. `examples/agent-tool-call.workflow.json`, `examples/web-app.architecture.json`, `examples/cache-miss-request.sequence.json`, `examples/product-analytics.dataflow.json`, `examples/deployment-release.lifecycle.json`, `examples/orders.erd.json`, `examples/payments.class.json`, `examples/payment-platform.tree.json`, `examples/payment-incident.timeline.json`, `examples/checkout-request.waterfall.json`) and `schemas/<type>.schema.json`. Examples teach shape, not facts: use fresh IDs and wording.
2. Write the whole candidate in one call. Do not plan coordinates in prose; use automatic routes first. Ask for missing personal facts instead of inventing dates or amounts.
3. If the result has `ok: false`, fix the listed fields (see `references/delivery-contract.md` and `references/authoring-contract.md` for layout failures) and call again with the full corrected diagram. Stop after 3 failed repairs and report the remaining errors.
4. On success reply briefly: a Markdown link to the returned `html` absolute path with a descriptive title, plus one takeaway sentence when explaining a system. Never paste the JSON.

example:
~~~json
{
  "thoughts": ["The user wants the release flow as a diagram; workflow fits. Schema and example already read."],
  "headline": "Rendering release workflow diagram",
  "tool_name": "archify_diagram",
  "tool_args": {
    "type": "workflow",
    "title": "Release approval flow",
    "diagram": {"meta": {"title": "Release approval flow"}, "...": "complete candidate per schemas/workflow.schema.json"}
  }
}
~~~
