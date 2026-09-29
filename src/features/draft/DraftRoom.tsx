import { useEffect, useMemo, useState } from "react";
import type { DraftMembership, Player } from "../../domain/draft";
import type { DraftGateway } from "../../application/ports";
import { useDraftRoom } from "./useDraftRoom";

interface DraftRoomProps {
  gateway: DraftGateway;
  membership: DraftMembership;
  userId: string;
  onLeave: () => void;
}

export function DraftRoom({ gateway, membership, userId, onLeave }: DraftRoomProps) {
  const { draft, players, picks, loading, error, refresh } = useDraftRoom(gateway, membership.draft.id);
  const [orderIds, setOrderIds] = useState<string[]>([]);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [pending, setPending] = useState<"order" | "start" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const isHost = draft?.host_id === userId;
  const orderedPlayers = useMemo(() => {
    const byId = new Map(players.map((player) => [player.id, player]));
    const ordered = orderIds.map((id) => byId.get(id)).filter((player): player is Player => player !== undefined);
    const included = new Set(ordered.map((player) => player.id));
    return [...ordered, ...players.filter((player) => !included.has(player.id))];
  }, [orderIds, players]);

  useEffect(() => {
    setOrderIds((current) => {
      const ids = players.map((player) => player.id);
      const allSeated = players.length > 0 && players.every((player) => player.seat !== null);
      if (allSeated || current.length === 0) return ids;
      const available = new Set(ids);
      return [...current.filter((id) => available.has(id)), ...ids.filter((id) => !current.includes(id))];
    });
  }, [players]);

  async function saveOrder() {
    setPending("order");
    setActionError(null);
    try {
      await gateway.setPlayerOrder(membership.draft.id, orderedPlayers.map((player) => player.id));
      await refresh();
    } catch (cause) {
      setActionError(messageOf(cause));
    } finally {
      setPending(null);
    }
  }

  async function startDraft() {
    setPending("start");
    setActionError(null);
    try {
      await gateway.startDraft(membership.draft.id);
      await refresh();
    } catch (cause) {
      setActionError(messageOf(cause));
    } finally {
      setPending(null);
    }
  }

  function movePlayer(playerId: string, targetId: string) {
    setOrderIds((current) => {
      const next = current.filter((id) => id !== playerId);
      const targetIndex = next.indexOf(targetId);
      next.splice(targetIndex < 0 ? next.length : targetIndex, 0, playerId);
      return next;
    });
  }

  const currentPlayer = players.find((player) => player.id === draft?.current_player);
  const statusLabel = draft?.status === "finished"
    ? "Draft finalizado"
    : draft?.status === "active"
      ? "Draft em andamento"
      : "Aguardando jogadores";

  return (
    <main className="page-shell room-shell">
      <section className="panel room-panel">
        <div className="room-topline">
          <div>
            <span className="eyebrow">Sala de draft</span>
            <h2>Código <span className="room-code">{draft?.code ?? membership.draft.code}</span></h2>
          </div>
          <button className="button button-quiet" type="button" onClick={onLeave}>Voltar ao lobby</button>
        </div>

        <div className={`status-banner status-${draft?.status ?? "waiting"}`} aria-live="polite">
          <span className="status-dot" />
          <div>
            <strong>{statusLabel}</strong>
            {draft?.status === "active" && <p>{currentPlayer ? `É a vez de ${currentPlayer.name}.` : "Atualizando a vez…"}</p>}
            {draft?.status === "waiting" && <p>Jogadores na sala: {players.length}/{draft.player_count}</p>}
            {draft?.status === "finished" && <p>Todos os jogadores fizeram sua escolha.</p>}
          </div>
        </div>

        {(loading || error || actionError) && (
          <p className={`feedback ${error || actionError ? "feedback-error" : "feedback-muted"}`} role={error || actionError ? "alert" : "status"}>
            {error ?? actionError ?? "Carregando estado atualizado da sala…"}
          </p>
        )}

        <section className="room-section" aria-labelledby="players-heading">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Participantes</span>
              <h3 id="players-heading">Jogadores</h3>
            </div>
            {isHost && draft?.status === "waiting" && <span className="host-chip">Você é o host</span>}
          </div>
          <div className="player-grid">
            {players.map((player) => (
              <article className="player-card" key={player.id}>
                <span className="seat-badge">{player.seat ?? "—"}</span>
                <div className="player-card-info">
                  <strong>{player.name}</strong>
                  <span className={player.connected ? "connection connection-on" : "connection"}>
                    <span className="status-dot" />{player.connected ? "Conectado" : "Desconectado"}
                  </span>
                </div>
                {player.user_id === draft?.host_id && <span className="host-mark" aria-label="Host">✦</span>}
              </article>
            ))}
            {players.length === 0 && <p className="feedback-muted">Nenhum jogador carregado.</p>}
          </div>
        </section>

        {isHost && draft?.status === "waiting" && (
          <section className="room-section order-section" aria-labelledby="order-heading">
            <div className="section-heading">
              <div>
                <span className="eyebrow">Preparação</span>
                <h3 id="order-heading">Ordem do draft</h3>
                <p className="section-copy">Arraste ou use as setas para organizar os assentos.</p>
              </div>
            </div>
            <ol className="order-list">
              {orderedPlayers.map((player, index) => (
                <li
                  className={`order-row ${draggedId === player.id ? "order-row-dragging" : ""}`}
                  draggable
                  key={player.id}
                  onDragStart={() => setDraggedId(player.id)}
                  onDragEnd={() => setDraggedId(null)}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={(event) => {
                    event.preventDefault();
                    if (draggedId) movePlayer(draggedId, player.id);
                    setDraggedId(null);
                  }}
                >
                  <span className="drag-grip" aria-hidden="true">⠿</span>
                  <span className="order-number">{index + 1}</span>
                  <span className="order-player-name">{player.name}</span>
                  <div className="order-controls">
                    <button type="button" aria-label={`Mover ${player.name} para cima`} disabled={index === 0} onClick={() => movePlayer(player.id, orderedPlayers[index - 1].id)}>↑</button>
                    <button type="button" aria-label={`Mover ${player.name} para baixo`} disabled={index === orderedPlayers.length - 1} onClick={() => movePlayer(player.id, orderedPlayers[index + 1].id)}>↓</button>
                  </div>
                </li>
              ))}
            </ol>
            <div className="room-actions">
              <button className="button button-secondary" type="button" disabled={pending !== null} onClick={() => void saveOrder()}>
                {pending === "order" ? "Salvando ordem…" : "Salvar ordem"}
              </button>
              <button className="button button-primary" type="button" disabled={pending !== null} onClick={() => void startDraft()}>
                {pending === "start" ? "Iniciando…" : "Iniciar draft"}
              </button>
            </div>
          </section>
        )}

        <section className="room-section picks-section" aria-labelledby="picks-heading">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Escolhas registradas</span>
              <h3 id="picks-heading">Facções escolhidas</h3>
            </div>
          </div>
          {picks.length > 0 ? (
            <ol className="pick-list">
              {picks.map((pick) => {
                const player = players.find((candidate) => candidate.id === pick.player_id);
                return <li key={pick.id}><span className="pick-number">{pick.pick_order}</span><strong>{pick.faction}</strong><span>{player?.name ?? "Jogador"}</span></li>;
              })}
            </ol>
          ) : <p className="feedback-muted">As escolhas aparecerão aqui quando forem registradas.</p>}
        </section>
      </section>
    </main>
  );
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "Ocorreu um erro inesperado.";
}
