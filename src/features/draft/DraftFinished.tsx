import { useState } from "react";
import type { ContentSet, Faction, Pick, Player } from "../../domain/draft";
import { factionAssetUrl } from "./factionAsset";

interface DraftFinishedProps { picks: Pick[]; players: Player[]; factions: Faction[]; contentSets: ContentSet[]; }
export function DraftFinished({ picks, players, factions, contentSets }: DraftFinishedProps) {
  return <section className="draft-finished" aria-labelledby="finished-heading">
    <span className="eyebrow">Resultado final</span><h2 id="finished-heading">Draft finalizado</h2><p>Cada jogador já definiu sua facção.</p>
    <ol className="finished-picks">{picks.map((pick) => <FinishedPick key={pick.id} pick={pick} player={players.find((item) => item.id === pick.player_id)} faction={factions.find((item) => item.id === pick.faction_id)} contentSets={contentSets} />)}</ol>
  </section>;
}

function FinishedPick({ pick, player, faction, contentSets }: { pick: Pick; player: Player | undefined; faction: Faction | undefined; contentSets: ContentSet[] }) {
  const [assetFailed, setAssetFailed] = useState(false);
  const url = faction ? factionAssetUrl(faction, contentSets) : null;
  return <li><span className="finished-symbol">{url && !assetFailed ? <img src={url} alt="" onError={() => setAssetFailed(true)} /> : "✦"}</span><span className="pick-number">{pick.pick_order}</span><span><strong>{player?.name ?? "Jogador"}</strong><small>{faction?.name ?? pick.faction}</small></span></li>;
}
