import { useEffect, useRef, useState } from "react";
import type { ContentSet, Faction } from "../../domain/draft";
import { contentSetLabel, factionAssetUrl } from "./factionAsset";

interface FactionPickModalProps {
  faction: Faction;
  contentSets: ContentSet[];
  submitting: boolean;
  error: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

export function FactionPickModal({ faction, contentSets, submitting, error, onCancel, onConfirm }: FactionPickModalProps) {
  const confirmButton = useRef<HTMLButtonElement>(null);
  const assetUrl = factionAssetUrl(faction, contentSets);
  const [assetFailed, setAssetFailed] = useState(false);
  useEffect(() => {
    confirmButton.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape" && !submitting) onCancel(); };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onCancel, submitting]);

  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !submitting) onCancel(); }}>
    <section className="pick-modal" role="dialog" aria-modal="true" aria-labelledby="pick-dialog-title">
      <span className="pick-modal-symbol" aria-hidden="true">{assetUrl && !assetFailed ? <img src={assetUrl} alt="" onError={() => setAssetFailed(true)} /> : "✦"}</span>
      <span className="eyebrow">{contentSetLabel(faction, contentSets)}</span>
      <h2 id="pick-dialog-title">{faction.name}</h2>
      <p>Confirmar esta facção?</p>
      {error && <p className="feedback feedback-error" role="alert">{error}</p>}
      <div className="modal-actions">
        <button className="button button-quiet" type="button" disabled={submitting} onClick={onCancel}>Cancelar</button>
        <button ref={confirmButton} className="button button-primary" type="button" disabled={submitting} onClick={onConfirm}>{submitting ? "Confirmando…" : "Confirmar escolha"}</button>
      </div>
    </section>
  </div>;
}
