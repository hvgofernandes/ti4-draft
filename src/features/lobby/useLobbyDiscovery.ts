import { useCallback, useEffect, useRef, useState } from "react";
import type { DraftGateway } from "../../application/ports";
import { sortJoinableDrafts, sortProfiles } from "../../application/lobbyDiscovery";
import type { JoinableDraft, PlayerProfile } from "../../domain/draft";

export function useLobbyDiscovery(gateway: DraftGateway) {
  const [profiles, setProfiles] = useState<PlayerProfile[]>([]);
  const [drafts, setDrafts] = useState<JoinableDraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(false);
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const focusedDraftId = useRef<string | undefined>(undefined);
  const refresh = useCallback(async (draftId?: string) => {
    focusedDraftId.current = draftId;
    setLoading(true);
    try {
      const [nextProfiles, nextDrafts] = await Promise.all([gateway.loadProfiles(draftId), gateway.listJoinableDrafts()]);
      if (!mounted.current) return;
      setProfiles(sortProfiles(nextProfiles)); setDrafts(sortJoinableDrafts(nextDrafts)); setError(null);
    } catch (cause) { if (mounted.current) setError(messageOf(cause)); }
    finally { if (mounted.current) setLoading(false); }
  }, [gateway]);
  useEffect(() => {
    mounted.current = true;
    const scheduleRefresh = () => { if (refreshTimer.current !== null) return; refreshTimer.current = setTimeout(() => { refreshTimer.current = null; void refresh(focusedDraftId.current); }, 75); };
    const unsubscribe = gateway.subscribeToLobby(scheduleRefresh, scheduleRefresh);
    void refresh();
    const poll = setInterval(scheduleRefresh, 15_000);
    return () => { mounted.current = false; clearInterval(poll); if (refreshTimer.current !== null) clearTimeout(refreshTimer.current); unsubscribe(); };
  }, [gateway, refresh]);
  return { profiles, drafts, loading, error, refresh };
}
function messageOf(error: unknown): string { return error instanceof Error ? error.message : "Não foi possível atualizar as sessões."; }
