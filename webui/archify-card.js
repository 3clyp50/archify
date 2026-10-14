import { store, viewUrl, formatBytes, TYPE_ICONS } from "/plugins/archify/webui/archify-store.js";

const STYLE_ID = "archify-card-style";

function ensureStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const link = document.createElement("link");
  link.id = STYLE_ID;
  link.rel = "stylesheet";
  link.href = "/plugins/archify/webui/archify.css";
  document.head.appendChild(link);
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function icon(name) {
  const node = document.createElement("x-icon");
  node.setAttribute("name", name);
  node.setAttribute("aria-hidden", "true");
  return node;
}

function actionButton(label, iconName, handler, primary = false) {
  const button = el("button", `archify-action${primary ? " primary" : ""}`);
  button.type = "button";
  button.title = label;
  button.append(icon(iconName), el("span", "", label));
  button.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    handler();
  });
  return button;
}

export function renderArchifyCard(card) {
  ensureStyles();
  const root = el("div", "archify-card");
  root.dataset.archifyId = card.id;

  const header = el("div", "archify-card-header");
  const badge = el("div", "archify-type-badge");
  badge.append(icon(TYPE_ICONS[card.type] || "schema"));
  const info = el("div", "archify-card-info");
  info.append(el("div", "archify-card-title", card.title || "Archify diagram"));
  const meta = el("div", "archify-card-meta");
  const parts = [card.type, card.checks ? `${card.checks} checks` : "", formatBytes(card.bytes), card.quality];
  parts.filter(Boolean).forEach((part) => meta.append(el("span", "", part)));
  info.append(meta);
  header.append(badge, info);
  root.append(header);

  if (card.preview !== false) {
    // The diagram itself is shown inline and is fully interactive (pan, zoom, theme, export).
    const preview = el("div", "archify-preview");
    const frame = document.createElement("iframe");
    frame.loading = "lazy";
    frame.src = viewUrl(card.id);
    frame.setAttribute("aria-label", card.title || "Archify diagram");
    frame.setAttribute("sandbox", "allow-scripts allow-same-origin allow-downloads allow-popups");
    const expand = el("button", "archify-preview-expand");
    expand.type = "button";
    expand.title = "Open full size";
    expand.setAttribute("aria-label", "Open diagram full size");
    expand.append(icon("open_in_full"));
    expand.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      store.openViewer(card);
    });
    preview.append(frame, expand);
    root.append(preview);
  }

  const actions = el("div", "archify-card-actions");
  actions.append(actionButton("Open", "open_in_full", () => store.openViewer(card), true));
  // Visibility follows the live plugin config, not the value captured when the diagram was rendered.
  const canvasButton = actionButton("Canvas", "right_panel_open", () => store.openInCanvas(card));
  canvasButton.hidden = !store.config?.canvas_enabled;
  actions.append(canvasButton);
  store.loadConfig?.().then((cfg) => { canvasButton.hidden = !cfg?.canvas_enabled; }).catch(() => {});
  actions.append(
    actionButton("New tab", "open_in_new", () => store.openInNewTab(card)),
    actionButton("Download", "download", () => store.download(card)),
    actionButton("Copy path", "content_copy", () => store.copyPath(card)),
  );
  root.append(actions);

  store.maybeAutoOpen?.(card);
  return root;
}
