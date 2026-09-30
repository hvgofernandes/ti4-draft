import { useCallback, useEffect, useRef, useState } from "react";
import type { ContentSet, Draft, DraftRoomSnapshot, Faction, Pick, Player } from "../../domain/draft";
import type { DraftGateway } from "../../application/ports";

interface DraftRoomState {
  draft: Draft | null;
  players: Player[];
  picks: Pick[];
  contentSets: ContentSet[];
  factions: Faction[];
  enabledContentSetIds: string[];
  loading: boolean;
  error: string | null;
}

export function useDraftRoom(
  gateway: DraftGateway,
  draftId: string,
  initialSnapshot: DraftRoomSnapshot,
): DraftRoomState & { refresh: () => Promise<void> } {
  const [state, setState] = useState<DraftRoomState>(() => ({
    draft: initialSnapshot.draft,
    players: initialSnapshot.players,
    picks: initialSnapshot.picks,
    contentSets: initialSnapshot.contentSets,
    factions: initialSnapshot.factions,
    enabledContentSetIds: initialSnapshot.enabledContentSetIds,
    loading: false,
    error: null,
  }));
  const mounted = useRef(false);
  const versions = useRef({ draft: 0, players: 0, picks: 0, content: 0 });

  const loadEnabledContentSetIds = useCallback(async () => {
    const version = versions.current.content;
    try {
      const enabledContentSetIds = await gateway.loadEnabledContentSetIds(draftId);
      if (mounted.current && version === versions.current.content) {
        setState((current) => ({ ...current, enabledContentSetIds, error: null }));
      }
    } catch (error) {
      if (mounted.current) setState((current) => ({ ...current, error: messageOf(error) }));
    }
  }, [draftId, gateway]);

  const loadDraft = useCallback(async () => {
    const version = versions.current.draft;
    try {
      const draft = await gateway.loadDraft(draftId);
      if (mounted.current && version === versions.current.draft) {
        setState((current) => ({ ...current, draft, error: null }));
      }
    } catch (error) {
      if (mounted.current) setState((current) => ({ ...current, error: messageOf(error) }));
    }
  }, [draftId, gateway]);

  const loadPlayers = useCallback(async () => {
    const version = versions.current.players;
    try {
      const players = await gateway.loadPlayers(draftId);
      if (mounted.current && version === versions.current.players) {
        setState((current) => ({ ...current, players, error: null }));
      }
    } catch (error) {
      if (mounted.current) setState((current) => ({ ...current, error: messageOf(error) }));
    }
  }, [draftId, gateway]);

  const loadPicks = useCallback(async () => {
    const version = versions.current.picks;
    try {
      const picks = await gateway.loadPicks(draftId);
      if (mounted.current && version === versions.current.picks) {
        setState((current) => ({ ...current, picks, error: null }));
      }
    } catch (error) {
      if (mounted.current) setState((current) => ({ ...current, error: messageOf(error) }));
    }
  }, [draftId, gateway]);

  const refresh = useCallback(async () => {
    await Promise.all([loadDraft(), loadPlayers(), loadPicks(), loadEnabledContentSetIds()]);
    if (mounted.current) setState((current) => ({ ...current, loading: false }));
  }, [loadDraft, loadPlayers, loadPicks, loadEnabledContentSetIds]);

  useEffect(() => {
    mounted.current = true;
    const unsubscribeDraft = gateway.subscribeToDraft(
      draftId,
      (draft) => {
        versions.current.draft += 1;
        setState((current) => ({ ...current, draft, error: null }));
        versions.current.content += 1;
        void loadEnabledContentSetIds();
      },
      () => void refresh(),
    );
    const unsubscribePlayers = gateway.subscribeToPlayers(
      draftId,
      () => {
        versions.current.players += 1;
        void loadPlayers();
      },
      () => void loadPlayers(),
    );
    const unsubscribePicks = gateway.subscribeToPicks(
      draftId,
      () => {
        versions.current.picks += 1;
        void loadPicks();
      },
      () => void loadPicks(),
    );

    return () => {
      mounted.current = false;
      unsubscribeDraft();
      unsubscribePlayers();
      unsubscribePicks();
    };
  }, [draftId, gateway, loadDraft, loadPlayers, loadPicks, loadEnabledContentSetIds, refresh]);

  return { ...state, refresh };
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "Não foi possível carregar os dados da sala.";
}
