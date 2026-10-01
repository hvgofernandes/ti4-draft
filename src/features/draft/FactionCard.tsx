import { useState } from "react";
import type { ContentSet, Faction, Pick, Player } from "../../domain/draft";
import { contentSetLabel, factionAssetUrl } from "./factionAsset";

interface FactionCardProps {
  faction: Faction;
  contentSets: ContentSet[];
  pick?: Pick;
  pickedBy?: Player;
  selectable: boolean;
  onSelect: (faction: Faction) => void;
}

export function FactionCard({ faction, contentSets, pick, pickedBy, selectable, onSelect }: FactionCardProps) {
  const assetUrl = factionAssetUrl(faction, contentSets);
  const isPicked = Boolean(pick);
  const [assetFailed, setAssetFailed] = useState(false);

  return (
    <button
      className={`faction-card ${isPicked ? "faction-card-picked" : ""}`}
      type="button"
      disabled={isPicked || !selectable}
      onClick={() => onSelect(faction)}
      aria-label={isPicked ? `${faction.name}, escolhida por ${pickedBy?.name ?? "outro jogador"}` : `Selecionar ${faction.name}`}
    >
      <span className="faction-card-symbol" aria-hidden="true">
        {assetUrl && !assetFailed ? <img src={assetUrl} alt="" onError={() => setAssetFailed(true)} /> : <span>✦</span>}
      </span>
      <span className="faction-card-body">
        <strong>{faction.name}</strong>
        <small>{contentSetLabel(faction, contentSets)}</small>
      </span>
      {isPicked && <span className="faction-card-state">Escolhida{pickedBy ? ` · ${pickedBy.name}` : ""}</span>}
    </button>
  );
}
