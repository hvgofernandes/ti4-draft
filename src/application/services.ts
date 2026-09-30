import { SupabaseAuthGateway } from "../infrastructure/supabase/supabaseAuthGateway";
import { SupabaseDraftGateway } from "../infrastructure/supabase/supabaseDraftGateway";
import type { DraftRoomSnapshot } from "../domain/draft";
import type { DraftGateway } from "./ports";

export const authGateway = new SupabaseAuthGateway();
export const draftGateway = new SupabaseDraftGateway();

export async function loadRoomSnapshot(gateway: DraftGateway, draftId: string): Promise<DraftRoomSnapshot> {
  const [draft, players, picks, contentSets, factions, enabledContentSetIds] = await Promise.all([
    gateway.loadDraft(draftId),
    gateway.loadPlayers(draftId),
    gateway.loadPicks(draftId),
    gateway.loadContentSets(),
    gateway.loadFactions(),
    gateway.loadEnabledContentSetIds(draftId),
  ]);
  return { draft, players, picks, contentSets, factions, enabledContentSetIds };
}
