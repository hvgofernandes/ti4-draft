import { useEffect, useMemo, useState } from "react";
import type { DraftMembership, DraftRoomSnapshot, Player } from "../../domain/draft";
import type { DraftGateway } from "../../application/ports";
import { ActiveDraft } from "./ActiveDraft";
import { DraftContentSets } from "./DraftContentSets";
import { DraftFinished } from "./DraftFinished";
import { useDraftRoom } from "./useDraftRoom";

interface DraftRoomProps { gateway: DraftGateway; membership: DraftMembership; initialSnapshot: DraftRoomSnapshot; userId: string; onLeave: () => void; }

export function DraftRoom({ gateway, membership, initialSnapshot, userId, onLeave }: DraftRoomProps) {
  const room = useDraftRoom(gateway, membership.draft.id, initialSnapshot);
  const { draft, players, picks, contentSets, factions, enabledContentSetIds, loading, error, refresh, makePick } = room;
  const [orderIds, setOrderIds] = useState<string[]>([]);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [pending, setPending] = useState<"order" | "start" | "content" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const isHost = draft?.host_id === userId;
  const orderedPlayers = useMemo(() => orderPlayers(players, orderIds), [players, orderIds]);

  useEffect(() => {
    setOrderIds((current) => reconcileOrder(players, current));
  }, [players]);

  async function saveOrder() { await withPending("order", async () => { await gateway.setPlayerOrder(membership.draft.id, orderedPlayers.map((player) => player.id)); await refresh(); }); }
  async function startDraft() { await withPending("start", async () => { await gateway.startDraft(membership.draft.id); await refresh(); }); }
  async function toggleContentSet(id: string, enabled: boolean) {
    if (!isHost || draft?.status !== "waiting" || pending !== null) return;
    await withPending("content", async () => { const next = enabled ? [...enabledContentSetIds, id] : enabledContentSetIds.filter((item) => item !== id); await gateway.setDraftContentSets(membership.draft.id, next); await refresh(); });
  }
  async function withPending(kind: "order" | "start" | "content", action: () => Promise<void>) { setPending(kind); setActionError(null); try { await action(); } catch (cause) { setActionError(messageOf(cause)); } finally { setPending(null); } }
  function movePlayer(playerId: string, targetId: string) { setOrderIds((current) => moveInOrder(current, playerId, targetId)); }
  const currentPlayer = players.find((player) => player.id === draft?.current_player);

  return <main className="page-shell room-shell"><section className="panel room-panel">
    <div className="room-topline"><div><span className="eyebrow">Sala de draft</span><h2>Código <span className="room-code">{draft?.code ?? membership.draft.code}</span></h2></div><button className="button button-quiet" type="button" onClick={onLeave}>Voltar ao lobby</button></div>
    <div className={`status-banner status-${draft?.status ?? "waiting"}`} aria-live="polite"><span className="status-dot" /><div><strong>{statusLabel(draft?.status)}</strong><p>{draft?.status === "active" ? currentPlayer ? `É a vez de ${currentPlayer.name}.` : "Atualizando a vez…" : draft?.status === "finished" ? "Todos os jogadores fizeram sua escolha." : `Jogadores na sala: ${players.length}/${draft?.player_count ?? membership.draft.player_count}`}</p></div></div>
    {(loading || error || actionError) && <p className={`feedback ${error || actionError ? "feedback-error" : "feedback-muted"}`} role={error || actionError ? "alert" : "status"}>{error ?? actionError ?? "Carregando estado atualizado da sala…"}</p>}
    {draft?.status === "active" ? <ActiveDraft draft={draft} players={players} picks={picks} factions={factions} contentSets={contentSets} enabledContentSetIds={enabledContentSetIds} currentUserId={userId} onMakePick={makePick} /> : draft?.status === "finished" ? <DraftFinished picks={picks} players={players} factions={factions} contentSets={contentSets} /> : <WaitingRoom players={players} factions={factions} contentSets={contentSets} enabledContentSetIds={enabledContentSetIds} playerCount={draft?.player_count ?? membership.draft.player_count} isHost={isHost} pending={pending} orderedPlayers={orderedPlayers} draggedId={draggedId} onDragId={setDraggedId} onMove={movePlayer} onSave={() => void saveOrder()} onStart={() => void startDraft()} onToggle={(id, enabled) => void toggleContentSet(id, enabled)} />}
  </section></main>;
}

interface WaitingRoomProps { players: Player[]; factions: DraftRoomSnapshot["factions"]; contentSets: DraftRoomSnapshot["contentSets"]; enabledContentSetIds: string[]; playerCount: number; isHost: boolean; pending: string | null; orderedPlayers: Player[]; draggedId: string | null; onDragId: (id: string | null) => void; onMove: (playerId: string, targetId: string) => void; onSave: () => void; onStart: () => void; onToggle: (id: string, enabled: boolean) => void; }
function WaitingRoom(props: WaitingRoomProps) { return <>
  <section className="room-section" aria-labelledby="players-heading"><div className="section-heading"><div><span className="eyebrow">Participantes</span><h3 id="players-heading">Jogadores</h3></div>{props.isHost && <span className="host-chip">Você é o host</span>}</div><div className="player-grid">{props.players.map((player) => <article className="player-card" key={player.id}><span className="seat-badge">{player.seat ?? "—"}</span><div className="player-card-info"><strong>{player.name}</strong><span className={player.connected ? "connection connection-on" : "connection"}><span className="status-dot" />{player.connected ? "Conectado" : "Desconectado"}</span></div></article>)}</div></section>
  <DraftContentSets contentSets={props.contentSets} factions={props.factions} enabledContentSetIds={props.enabledContentSetIds} playerCount={props.playerCount} editable={props.isHost} saving={props.pending !== null} onToggle={props.onToggle} />
  {props.isHost && <section className="room-section order-section" aria-labelledby="order-heading"><div className="section-heading"><div><span className="eyebrow">Preparação</span><h3 id="order-heading">Ordem do draft</h3><p className="section-copy">Arraste ou use as setas para organizar os assentos.</p></div></div><ol className="order-list">{props.orderedPlayers.map((player, index) => <li className={`order-row ${props.draggedId === player.id ? "order-row-dragging" : ""}`} draggable key={player.id} onDragStart={() => props.onDragId(player.id)} onDragEnd={() => props.onDragId(null)} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); if (props.draggedId) props.onMove(props.draggedId, player.id); props.onDragId(null); }}><span className="drag-grip" aria-hidden="true">⠿</span><span className="order-number">{index + 1}</span><span className="order-player-name">{player.name}</span><div className="order-controls"><button type="button" aria-label={`Mover ${player.name} para cima`} disabled={index === 0} onClick={() => props.onMove(player.id, props.orderedPlayers[index - 1].id)}>↑</button><button type="button" aria-label={`Mover ${player.name} para baixo`} disabled={index === props.orderedPlayers.length - 1} onClick={() => props.onMove(player.id, props.orderedPlayers[index + 1].id)}>↓</button></div></li>)}</ol><div className="room-actions"><button className="button button-secondary" type="button" disabled={props.pending !== null} onClick={props.onSave}>{props.pending === "order" ? "Salvando ordem…" : "Salvar ordem"}</button><button className="button button-primary" type="button" disabled={props.pending !== null} onClick={props.onStart}>{props.pending === "start" ? "Iniciando…" : "Iniciar draft"}</button></div></section>}
</>; }

export function moveInOrder(current: string[], playerId: string, targetId: string): string[] { const from = current.indexOf(playerId); const target = current.indexOf(targetId); if (from < 0 || target < 0 || from === target) return current; const next = [...current]; const [moved] = next.splice(from, 1); next.splice(target, 0, moved); return next; }
function reconcileOrder(players: Player[], current: string[]): string[] { const ids = players.map((player) => player.id); if (players.length > 0 && players.every((player) => player.seat !== null)) return ids; const valid = new Set(ids); return [...current.filter((id) => valid.has(id)), ...ids.filter((id) => !current.includes(id))]; }
function orderPlayers(players: Player[], orderIds: string[]): Player[] { const byId = new Map(players.map((player) => [player.id, player])); const ordered = orderIds.map((id) => byId.get(id)).filter((player): player is Player => player !== undefined); const included = new Set(ordered.map((player) => player.id)); return [...ordered, ...players.filter((player) => !included.has(player.id))]; }
function statusLabel(status: DraftRoomSnapshot["draft"]["status"] | undefined) { return status === "finished" ? "Draft finalizado" : status === "active" ? "Draft em andamento" : "Aguardando jogadores"; }
function messageOf(error: unknown): string { return error instanceof Error ? error.message : "Ocorreu um erro inesperado."; }
