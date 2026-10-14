import { createStore } from "/js/AlpineStore.js";
import { fetchApi } from "/js/api.js";
import { openModal } from "/js/modals.js";
import {
  toastFrontendError,
  toastFrontendInfo,
} from "/components/notifications/notification-store.js";

const PLUGIN = "archify";
const TITLE = "Archify";
const CONFIG_TTL_MS = 15000;

export const DEFAULT_CONFIG = {
  chat_results: true,
  canvas_enabled: false,
  auto_open_canvas: false,
  inline_preview: true,
  quality: "showcase",
};

export const TYPE_ICONS = {
  architecture: "hub",
  workflow: "account_tree",
  sequence: "swap_horiz",
  dataflow: "conversion_path",
  lifecycle: "autorenew",
  erd: "table_chart",
  class: "data_object",
  tree: "lan",
  timeline: "timeline",
  waterfall: "waterfall_chart",
};

export function viewUrl(id, download = false) {
  const params = new URLSearchParams({ id });
  if (download) params.set("download", "1");
  return `/api/plugins/${PLUGIN}/view?${params.toString()}`;
}

export function formatBytes(bytes = 0) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

async function postJson(path, body) {
  const response = await fetchApi(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  return response.json().catch(() => ({}));
}

export const store = createStore("archify", {
  config: { ...DEFAULT_CONFIG },
  configLoadedAt: 0,
  current: null,
  canvasDiagram: null,
  recent: [],
  loadingRecent: false,
  autoOpened: new Set(),

  init() {},

  async loadConfig(force = false) {
    if (!force && Date.now() - this.configLoadedAt < CONFIG_TTL_MS) return this.config;
    try {
      const result = await postJson("/plugins", { action: "get_config", plugin_name: PLUGIN });
      this.config = { ...DEFAULT_CONFIG, ...(result?.ok ? result.data || {} : {}) };
      if (!this.config.canvas_enabled) this.config.auto_open_canvas = false;
    } catch (error) {
      console.warn("Archify config load failed", error);
    }
    this.configLoadedAt = Date.now();
    return this.config;
  },

  openViewer(diagram) {
    if (!diagram?.id) return;
    this.current = diagram;
    openModal(`/plugins/${PLUGIN}/webui/viewer.html`);
  },

  openInNewTab(diagram) {
    if (!diagram?.id) return;
    globalThis.open(viewUrl(diagram.id), "_blank", "noopener");
  },

  download(diagram) {
    if (!diagram?.id) return;
    const link = document.createElement("a");
    link.href = viewUrl(diagram.id, true);
    link.rel = "noopener";
    document.body.appendChild(link);
    link.click();
    link.remove();
  },

  async copyPath(diagram) {
    if (!diagram?.html) return;
    try {
      await navigator.clipboard.writeText(diagram.html);
      toastFrontendInfo("Diagram path copied", TITLE);
    } catch {
      toastFrontendError("Clipboard is not available", TITLE);
    }
  },

  async openInCanvas(diagram) {
    await this.loadConfig();
    if (!this.config.canvas_enabled) {
      toastFrontendInfo("Enable the canvas in Archify settings to dock diagrams. Opening the viewer instead.", TITLE);
      this.openViewer(diagram);
      return;
    }
    try {
      const { store: canvas } = await import("/components/canvas/right-canvas-store.js");
      if (diagram) this.canvasDiagram = diagram;
      const opened = await canvas.open(PLUGIN, { diagram });
      if (!opened) this.openViewer(diagram);
    } catch (error) {
      console.error(error);
      toastFrontendError("Could not open the Archify canvas", TITLE);
      this.openViewer(diagram);
    }
  },

  maybeAutoOpen(diagram) {
    if (!diagram?.open_canvas || this.autoOpened.has(diagram.id)) return;
    this.autoOpened.add(diagram.id);
    // Only auto-open for fresh results, never for replayed history.
    const created = Number((diagram.id.match(/(\d{8})-(\d{6})/) || []).slice(1).join("")) || 0;
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const stamp = Number(`${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`);
    if (created && stamp - created > 120) return;
    this.openInCanvas(diagram);
  },

  async refreshRecent() {
    this.loadingRecent = true;
    try {
      const result = await postJson(`/plugins/${PLUGIN}/diagrams`, { action: "list", limit: 40 });
      this.recent = result?.ok ? result.diagrams || [] : [];
      if (!this.canvasDiagram && this.recent.length) this.canvasDiagram = this.recent[0];
    } catch (error) {
      console.error(error);
      toastFrontendError("Could not load diagrams", TITLE);
    } finally {
      this.loadingRecent = false;
    }
  },

  selectCanvasDiagram(id) {
    const found = this.recent.find((item) => item.id === id);
    if (found) this.canvasDiagram = found;
  },

  canvasUrl() {
    return this.canvasDiagram?.id ? viewUrl(this.canvasDiagram.id) : "";
  },

  viewerUrl() {
    return this.current?.id ? viewUrl(this.current.id) : "";
  },

  iconFor(type) {
    return TYPE_ICONS[type] || "schema";
  },

  formatBytes,
});
