import { useEffect, useMemo, useState } from "react";
import type { ContentSet, Draft, Faction, Pick, Player } from "../../domain/draft";
import { FactionCard } from "./FactionCard";
import { FactionFilters, type AvailabilityFilter } from "./FactionFilters";
import { FactionPickModal } from "./FactionPickModal";
import { PlayerDraftOrder } from "./PlayerDraftOrder";

interface ActiveDraftProps { draft: Draft; players: Player[]; picks: Pick[]; factions: Faction[]; contentSets: ContentSet[]; enabledContentSetIds: string[]; currentUserId: string; onMakePick: (factionId: string) => Promise<unknown>; }

export function ActiveDraft(props: ActiveDraftProps) {
  const [query, setQuery] = useState(""); const [contentSetId, setContentSetId] = useState("all"); const [availability, setAvailability] = useState<AvailabilityFilter>("all"); const [selected, setSelected] = useState<Faction | null>(null); const [submitting, setSubmitting] = useState(false); const [modalError, setModalError] = useState<string | null>(null);
  const enabledSets = useMemo(() => props.contentSets.filter((set) => set.active && props.enabledContentSetIds.includes(set.id)), [props.contentSets, props.enabledContentSetIds]);
  const currentPlayer = props.players.find((player) => player.id === props.draft.current_player);
  const isCurrentUser = currentPlayer?.user_id === props.currentUserId;
  const picksByFaction = useMemo(() => new Map(props.picks.filter((pick) => pick.faction_id).map((pick) => [pick.faction_id as string, pick])), [props.picks]);
  const playersById = useMemo(() => new Map(props.players.map((player) => [player.id, player])), [props.players]);
  const enabledSetIds = useMemo(() => new Set(enabledSets.map((contentSet) => contentSet.id)), [enabledSets]);
  const visibleFactions = useMemo(() => props.factions.filter((faction) => faction.active && enabledSetIds.has(faction.content_set_id)).filter((faction) => contentSetId === "all" || faction.content_set_id === contentSetId).filter((faction) => faction.name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())).filter((faction) => availability === "all" || (availability === "picked" ? picksByFaction.has(faction.id) : !picksByFaction.has(faction.id))).sort((a,b) => a.name.localeCompare(b.name)), [props.factions, enabledSetIds, contentSetId, query, availability, picksByFaction]);
  useEffect(() => {
    if (selected && (!isCurrentUser || picksByFaction.has(selected.id))) {
      setSelected(null);
      setModalError(null);
    }
  }, [isCurrentUser, picksByFaction, selected]);
  async function confirm() { if (!selected || submitting || !isCurrentUser || picksByFaction.has(selected.id)) return; setSubmitting(true); setModalError(null); try { await props.onMakePick(selected.id); setSelected(null); } catch (cause) { setModalError(cause instanceof Error ? cause.message : "Não foi possível registrar a escolha."); } finally { setSubmitting(false); } }
  const progress = `${props.picks.length + 1} / ${props.players.length}`;
  return <section className="active-draft" aria-label="Draft em andamento">
    <header className="active-draft-header"><div><span className="eyebrow">Sala {props.draft.code} · Pick {progress}</span><h2>{currentPlayer ? `Vez de ${currentPlayer.name}` : "Atualizando a vez…"}</h2><p>{isCurrentUser ? "Escolha uma facção para confirmar." : "Você pode acompanhar as escolhas enquanto aguarda sua vez."}</p></div><span className="draft-status-chip">Em andamento</span></header>
    <div className="active-draft-layout"><section className="faction-catalog"><div className="section-heading"><div><span className="eyebrow">Catálogo de facções</span><h3>Escolha disponível</h3></div><span className="catalog-count">{visibleFactions.length} facções</span></div><FactionFilters query={query} contentSetId={contentSetId} availability={availability} contentSets={enabledSets} onQueryChange={setQuery} onContentSetChange={setContentSetId} onAvailabilityChange={setAvailability}/><div className="faction-grid">{visibleFactions.map((faction) => { const pick = picksByFaction.get(faction.id); return <FactionCard key={faction.id} faction={faction} contentSets={props.contentSets} pick={pick} pickedBy={pick ? playersById.get(pick.player_id) : undefined} selectable={isCurrentUser} onSelect={setSelected} />; })}</div>{visibleFactions.length === 0 && <p className="feedback-muted">Nenhuma facção corresponde aos filtros.</p>}</section><PlayerDraftOrder players={props.players} picks={props.picks} factions={props.factions} currentPlayerId={props.draft.current_player}/></div>
    {selected && <FactionPickModal faction={selected} contentSets={props.contentSets} submitting={submitting} error={modalError} onCancel={() => { if (!submitting) { setSelected(null); setModalError(null); } }} onConfirm={() => void confirm()} />}
  </section>;
}
