import type { JoinableDraft, PlayerProfile } from "../domain/draft";

export function isProfileAvailable(draft: JoinableDraft, profileId: string): boolean {
  return draft.player_count < draft.capacity && !draft.used_profile_ids.includes(profileId);
}

export function sortProfiles(profiles: PlayerProfile[]): PlayerProfile[] {
  return [...profiles]
    .sort((left, right) => left.sort_order - right.sort_order || left.name.localeCompare(right.name));
}

export function sortJoinableDrafts(drafts: JoinableDraft[]): JoinableDraft[] {
  return drafts.filter((draft) => draft.player_count < draft.capacity);
}
