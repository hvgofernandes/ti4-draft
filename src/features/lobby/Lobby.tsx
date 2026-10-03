import { useEffect, useState, type FormEvent } from "react";
import { isProfileAvailable } from "../../application/lobbyDiscovery";
import type { DraftGateway } from "../../application/ports";
import type { DraftMembership, JoinableDraft, PlayerProfile } from "../../domain/draft";
import { useLobbyDiscovery } from "./useLobbyDiscovery";

interface LobbyProps { gateway: DraftGateway; onCreate: (profileId: string, playerCount: number) => Promise<DraftMembership>; onJoin: (profileId: string, code: string) => Promise<DraftMembership>; onJoinDraft: (profileId: string, draftId: string) => Promise<DraftMembership>; onEnter: (membership: DraftMembership) => void | Promise<void>; }

export function Lobby({ gateway, onCreate, onJoin, onJoinDraft, onEnter }: LobbyProps) {
  const { profiles, drafts, loading, error: discoveryError, refresh } = useLobbyDiscovery(gateway);
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [focusedDraftId, setFocusedDraftId] = useState<string | null>(null);
  const [roomCode, setRoomCode] = useState("");
  const [playerCount, setPlayerCount] = useState(6);
  const [busy, setBusy] = useState<"create" | "code" | string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selectedProfile = profiles.find((profile) => profile.id === selectedProfileId) ?? null;

  useEffect(() => { if (selectedProfileId && !profiles.some((profile) => profile.id === selectedProfileId && !profile.unavailable)) setSelectedProfileId(null); }, [profiles, selectedProfileId]);
  async function focusDraft(draft: JoinableDraft) { setFocusedDraftId(draft.draft_id); setError(null); await refresh(draft.draft_id); }
  async function submitCreate(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!selectedProfileId) return setError("Escolha seu perfil antes de criar a sala."); await run("create", () => onCreate(selectedProfileId, playerCount)); }
  async function submitJoin(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!selectedProfileId) return setError("Escolha seu perfil antes de entrar."); await run("code", () => onJoin(selectedProfileId, roomCode.trim().toUpperCase())); }
  async function joinDiscovered(draft: JoinableDraft) {
    if (!selectedProfileId) { await focusDraft(draft); setError("Escolha um perfil disponível para esta sala."); return; }
    if (!isProfileAvailable(draft, selectedProfileId)) { await focusDraft(draft); setError("Este perfil já participa da sala. Escolha outro perfil."); return; }
    await run(draft.draft_id, () => onJoinDraft(selectedProfileId, draft.draft_id));
  }
  async function run(key: "create" | "code" | string, action: () => Promise<DraftMembership>) { setBusy(key); setError(null); try { await onEnter(await action()); } catch (cause) { setError(messageOf(cause)); await refresh(focusedDraftId ?? undefined); } finally { setBusy(null); } }

  return <main className="page-shell lobby-shell">
    <section className="panel lobby-panel lobby-profile-panel" aria-labelledby="profile-heading"><div className="panel-heading"><span className="eyebrow">Identidade de jogador</span><h2 id="profile-heading">Quem é você?</h2><p>Escolha seu perfil antes de criar ou entrar em um draft.</p></div><div className="profile-grid" aria-label="Perfis disponíveis">{profiles.map((profile) => <ProfileButton key={profile.id} profile={profile} selected={profile.id === selectedProfileId} onSelect={() => setSelectedProfileId(profile.id)} />)}</div>{loading && profiles.length === 0 && <p className="feedback feedback-muted" role="status">Carregando perfis…</p>}{selectedProfile && <p className="selected-profile" aria-live="polite">Jogando como <strong>{selectedProfile.name}</strong></p>}</section>
    <section className="panel lobby-panel discovery-panel" aria-labelledby="discovery-heading"><div className="panel-heading discovery-heading"><div><span className="eyebrow">Partidas do grupo</span><h2 id="discovery-heading">Sessões disponíveis</h2><p>Salas aguardando jogadores aparecem aqui automaticamente.</p></div><button className="button button-quiet" type="button" disabled={loading} onClick={() => void refresh(focusedDraftId ?? undefined)}>Atualizar</button></div><div className="session-list">{drafts.map((draft) => { const available = selectedProfileId ? isProfileAvailable(draft, selectedProfileId) : true; return <article className={`session-card ${focusedDraftId === draft.draft_id ? "session-card-focused" : ""}`} key={draft.draft_id}><div><span className="session-status"><span className="status-dot" /> Aguardando</span><h3>Sala de {draft.host_name}</h3><p><span>{draft.player_count}/{draft.capacity} jogadores</span><span>Código {draft.room_code}</span></p></div><button className={available ? "button button-secondary" : "button button-quiet"} type="button" disabled={busy !== null} onClick={() => void joinDiscovered(draft)}>{busy === draft.draft_id ? "Entrando…" : !selectedProfileId ? "Escolher perfil" : available ? "Entrar" : "Perfil já presente"}</button></article>; })}{!loading && drafts.length === 0 && <div className="empty-sessions"><strong>Nenhuma sessão aberta</strong><span>Crie um draft para começar.</span></div>}</div></section>
    <section className="panel lobby-panel lobby-actions-panel"><div className="lobby-action-grid"><form className="form-stack" onSubmit={submitCreate}><span className="eyebrow">Nova sessão</span><h3>Criar novo draft</h3><label className="field-label" htmlFor="player-count">Jogadores na sala</label><select id="player-count" value={playerCount} onChange={(event) => setPlayerCount(Number(event.target.value))}>{[3, 4, 5, 6].map((count) => <option key={count} value={count}>{count} jogadores</option>)}</select><button className="button button-primary" disabled={busy !== null || !selectedProfileId} type="submit">{busy === "create" ? "Criando sala…" : "Criar sala"}</button></form><form className="form-stack code-entry" onSubmit={submitJoin}><span className="eyebrow">Entrada por convite</span><h3>Usar código da sala</h3><label className="field-label" htmlFor="room-code">Código da sala</label><input id="room-code" autoCapitalize="characters" maxLength={6} placeholder="Ex.: A1B2C3" required value={roomCode} onChange={(event) => setRoomCode(event.target.value.toUpperCase())} /><button className="button button-secondary" disabled={busy !== null || !selectedProfileId} type="submit">{busy === "code" ? "Entrando…" : "Entrar com código"}</button></form></div>{(error || discoveryError) && <p className="feedback feedback-error" role="alert">{error ?? discoveryError}</p>}</section>
  </main>;
}

function ProfileButton({ profile, selected, onSelect }: { profile: PlayerProfile; selected: boolean; onSelect: () => void }) { const initials = profile.name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase(); return <button className={`profile-card ${selected ? "profile-card-selected" : ""} ${profile.unavailable ? "profile-card-unavailable" : ""}`} type="button" disabled={profile.unavailable} aria-pressed={selected} onClick={onSelect}><span className="profile-avatar" aria-hidden="true">{initials}</span><span><strong>{profile.name}</strong><small>{profile.unavailable ? "Já está nesta sala" : selected ? "Perfil selecionado" : "Disponível"}</small></span></button>; }
function messageOf(value: unknown) { return value instanceof Error ? value.message : "Ocorreu um erro inesperado."; }
