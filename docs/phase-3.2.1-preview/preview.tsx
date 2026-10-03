import { useState } from "react";
import { createRoot } from "react-dom/client";
import type { ContentSet, Faction } from "../../src/domain/draft";
import { FactionPickModal } from "../../src/features/draft/FactionPickModal";

const contentSets: ContentSet[] = [
  { id: "base", name: "Base Game", slug: "base", active: true, sort_order: 1 },
  { id: "pok", name: "Prophecy of Kings", slug: "pok", active: true, sort_order: 2 },
];

const factions: Record<"base" | "fallback", Faction> = {
  base: { id: "sol", content_set_id: "base", name: "The Federation of Sol", slug: "the-federation-of-sol", active: true, sort_order: 1 },
  fallback: { id: "argent", content_set_id: "pok", name: "The Argent Flight", slug: "the-argent-flight", active: true, sort_order: 1 },
};

function ModalHarness() {
  const [selected, setSelected] = useState<Faction | null>(null);
  const [result, setResult] = useState("Nenhuma ação executada.");

  return <>
    <div className="actions" style={{ position: "static", justifyContent: "flex-start", background: "none", padding: 0 }}>
      <button type="button" onClick={() => setSelected(factions.base)}>Abrir Base</button>
      <button type="button" onClick={() => setSelected(factions.fallback)}>Abrir fallback PoK</button>
    </div>
    <p className="muted" aria-live="polite" style={{ margin: "14px 0 0" }}>{result}</p>
    {selected && <FactionPickModal
      faction={selected}
      contentSets={contentSets}
      submitting={false}
      error={null}
      onCancel={() => { setResult("Cancelar/Escape fechou o modal."); setSelected(null); }}
      onConfirm={() => { setResult(`Confirmação recebida para ${selected.name}.`); setSelected(null); }}
    />}
  </>;
}

const root = document.querySelector("#modal-harness");
if (root) createRoot(root).render(<ModalHarness />);
