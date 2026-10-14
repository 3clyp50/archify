import { store as archify } from "/plugins/archify/webui/archify-store.js";

// The canvas surface is opt-in: it registers only when "canvas_enabled" is on in Archify settings
// (reload the page after changing it). Default behavior is chat results only.
export default async function registerArchifySurface(surfaces) {
  const config = await archify.loadConfig(true);
  if (!config.canvas_enabled) return;
  surfaces.registerSurface({
    id: "archify",
    title: "Archify",
    icon: "schema",
    order: 40,
    modalPath: "/plugins/archify/webui/main.html",
    async open(payload = {}) {
      if (payload?.diagram?.id) archify.canvasDiagram = payload.diagram;
      await archify.refreshRecent();
      if (payload?.diagram?.id) archify.canvasDiagram = payload.diagram;
    },
    close() {},
  });
}
