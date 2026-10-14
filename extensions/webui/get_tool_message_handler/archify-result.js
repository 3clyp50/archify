import { drawProcessStep, drawMessageToolSimple } from "/js/messages.js";
import { renderArchifyCard } from "/plugins/archify/webui/archify-card.js";

// The card is attached to the step itself (after its header), not inside the
// step detail: collapsed steps defer and discard their detail body, so a card
// placed there would be missing until the user expands the step.
export default function (context) {
  if (context.tool_name !== "archify_diagram") return;
  context.handler = async (log) => {
    const card = log.kvps?._archify_result;
    if (!card?.id) return drawMessageToolSimple({ ...log, code: "ARC" });
    const result = await drawProcessStep({
      id: log.id, title: log.heading, code: "ARC", kvps: {}, content: "", log,
    });
    const step = result?.step || result?.element;
    if (!step) return result;
    const existing = step.querySelector(":scope > .archify-card");
    if (card.chat === false) {
      existing?.remove();
      return result;
    }
    if (existing?.dataset.archifyId === card.id) return result;
    existing?.remove();
    const node = renderArchifyCard(card);
    node.classList.add("archify-card-attached");
    const header = step.querySelector(":scope > .process-step-header");
    if (header) header.insertAdjacentElement("afterend", node);
    else step.appendChild(node);
    return result;
  };
}
