import type { DraftRoomSnapshot, Faction, Pick } from "../domain/draft";

export type FactionAvailability = {
  faction: Faction;
  pick: Pick | null;
  available: boolean;
};

/**
 * Produces the catalog a draft is allowed to display. The server still
 * validates every selection; this is solely a projection of its configuration.
 */
export function getEnabledFactions(snapshot: DraftRoomSnapshot): Faction[] {
  const enabledIds = new Set(snapshot.enabledContentSetIds);
  const activeSetIds = new Set(
    snapshot.contentSets
      .filter((contentSet) => contentSet.active && enabledIds.has(contentSet.id))
      .map((contentSet) => contentSet.id),
  );

  return snapshot.factions
    .filter((faction) => faction.active && activeSetIds.has(faction.content_set_id))
    .sort((left, right) => left.name.localeCompare(right.name, "pt-BR"));
}

/**
 * Keeps picked factions in the catalog and associates them with their pick.
 */
export function getFactionAvailability(snapshot: DraftRoomSnapshot): FactionAvailability[] {
  const picksByFactionId = new Map(
    snapshot.picks
      .filter((pick): pick is Pick & { faction_id: string } => pick.faction_id !== null)
      .map((pick) => [pick.faction_id, pick]),
  );

  return getEnabledFactions(snapshot).map((faction) => {
    const pick = picksByFactionId.get(faction.id) ?? null;
    return { faction, pick, available: pick === null };
  });
}

/**
 * A UI guard for the confirmation action. It mirrors the current room state
 * but is deliberately not an authorization boundary: make_pick owns that.
 */
export function canUserPick(snapshot: DraftRoomSnapshot, userId: string): boolean {
  if (snapshot.draft.status !== "active" || snapshot.draft.current_player === null) return false;
  return snapshot.players.some(
    (player) => player.id === snapshot.draft.current_player && player.user_id === userId,
  );
}
