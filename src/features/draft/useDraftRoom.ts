import { useCallback, useEffect, useRef, useState } from "react";
import { loadRoomSnapshot } from "../../application/services";
import type { ContentSet, Draft, DraftRoomSnapshot, Faction, MakePickResult, Pick, Player } from "../../domain/draft";
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
): DraftRoomState & {
  refresh: () => Promise<void>;
  makePick: (factionId: string) => Promise<MakePickResult>;
  isPicking: boolean;
  clearError: () => void;
} {
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
  const refreshVersion = useRef(0);
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const picking = useRef(false);
  const [isPicking, setIsPicking] = useState(false);

  const refresh = useCallback(async () => {
    const version = ++refreshVersion.current;
    if (mounted.current) setState((current) => ({ ...current, loading: true }));
    try {
      const snapshot = await loadRoomSnapshot(gateway, draftId);
      if (mounted.current && version === refreshVersion.current) {
        setState({ ...snapshot, loading: false, error: null });
      }
    } catch (error) {
      if (mounted.current && version === refreshVersion.current) {
        setState((current) => ({ ...current, loading: false, error: messageOf(error) }));
      }
    }
  }, [draftId, gateway]);

  const scheduleRefresh = useCallback(() => {
    if (refreshTimer.current !== null) return;
    refreshTimer.current = setTimeout(() => {
      refreshTimer.current = null;
      void refresh();
    }, 50);
  }, [refresh]);

  const makePick = useCallback(async (factionId: string): Promise<MakePickResult> => {
    if (picking.current) throw new Error("Uma escolha já está sendo enviada.");
    picking.current = true;
    setIsPicking(true);
    if (mounted.current) setState((current) => ({ ...current, error: null }));

    try {
      const result = await gateway.makePick(draftId, factionId);
      await refresh();
      return result;
    } catch (error) {
      // A stale client may lose a race for the turn or faction. Always reconcile
      // with the server before returning the domain error to the UI.
      await refresh();
      if (mounted.current) setState((current) => ({ ...current, error: messageOf(error) }));
      throw error;
    } finally {
      picking.current = false;
      if (mounted.current) setIsPicking(false);
    }
  }, [draftId, gateway, refresh]);

  const clearError = useCallback(() => {
    if (mounted.current) setState((current) => ({ ...current, error: null }));
  }, []);

  useEffect(() => {
    mounted.current = true;
    const unsubscribeDraft = gateway.subscribeToDraft(
      draftId,
      () => scheduleRefresh(),
      scheduleRefresh,
    );
    const unsubscribePlayers = gateway.subscribeToPlayers(
      draftId,
      scheduleRefresh,
      scheduleRefresh,
    );
    const unsubscribePicks = gateway.subscribeToPicks(
      draftId,
      scheduleRefresh,
      scheduleRefresh,
    );
    // Reconcile the server snapshot before Realtime becomes the sole source of
    // changes. This covers a reload and events missed while a channel reconnects.
    void refresh();

    return () => {
      mounted.current = false;
      if (refreshTimer.current !== null) clearTimeout(refreshTimer.current);
      refreshTimer.current = null;
      unsubscribeDraft();
      unsubscribePlayers();
      unsubscribePicks();
    };
  }, [draftId, gateway, refresh, scheduleRefresh]);

  return { ...state, refresh, makePick, isPicking, clearError };
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "Não foi possível carregar os dados da sala.";
}
