import type { Faction, Pick, Player } from "../../domain/draft";

interface PlayerDraftOrderProps { players: Player[]; picks: Pick[]; factions: Faction[]; currentPlayerId: string | null; }

export function PlayerDraftOrder({ players, picks, factions, currentPlayerId }: PlayerDraftOrderProps) {
  const pickFor = (playerId: string) => picks.find((pick) => pick.player_id === playerId);
  return <aside className="draft-sidebar" aria-labelledby="draft-order-heading">
    <span className="eyebrow">Ordem e escolhas</span><h3 id="draft-order-heading">Mesa de draft</h3>
    <ol className="draft-player-order">
      {players.map((player) => {
        const pick = pickFor(player.id);
        const faction = pick ? factions.find((candidate) => candidate.id === pick.faction_id) : undefined;
        const state = pick ? "picked" : player.id === currentPlayerId ? "current" : "waiting";
        return <li key={player.id} className={`draft-player draft-player-${state}`}>
          <span className="draft-seat">{player.seat ?? "—"}</span>
          <span><strong>{state === "picked" ? "✓" : state === "current" ? "→" : "○"} {player.name}</strong><small>{faction?.name ?? (state === "current" ? "Escolhendo…" : "Aguardando")}</small></span>
        </li>;
      })}
    </ol>
  </aside>;
}
