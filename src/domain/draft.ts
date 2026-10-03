export type DraftStatus = "waiting" | "active" | "finished";

export type Draft = {
  id: string;
  code: string;
  status: DraftStatus;
  player_count: number;
  picks_per_player: number;
  created_at: string;
  host_id: string | null;
  current_player: string | null;
  content_version: number;
};

export type Player = {
  id: string;
  draft_id: string;
  name: string;
  seat: number | null;
  connected: boolean;
  joined_at: string;
  user_id: string | null;
  profile_id?: string | null;
};

export type PlayerProfile = {
  id: string;
  name: string;
  sort_order: number;
  unavailable: boolean;
};

export type JoinableDraft = {
  draft_id: string;
  room_code: string;
  host_profile_id: string | null;
  host_name: string;
  player_count: number;
  capacity: number;
  used_profile_ids: string[];
};

export type Pick = {
  id: string;
  draft_id: string;
  player_id: string;
  faction_id: string | null;
  faction: string;
  pick_order: number;
  created_at: string;
};

export type ContentSet = {
  id: string;
  name: string;
  slug: string;
  active: boolean;
  sort_order: number;
};

export type Faction = {
  id: string;
  content_set_id: string;
  name: string;
  slug: string;
  active: boolean;
  sort_order: number;
};

export type DraftContentSet = {
  draft_id: string;
  content_set_id: string;
};

export type DraftMembership = {
  draft: Draft;
  player: Player;
};

export type DraftRoomSnapshot = {
  draft: Draft;
  players: Player[];
  picks: Pick[];
  contentSets: ContentSet[];
  factions: Faction[];
  enabledContentSetIds: string[];
};

export type MakePickResult =
  | {
      success: true;
      status: "active";
      pick_order: number;
      faction_id: string;
      faction: string;
      player_id: string;
      next_player: string;
    }
  | {
      success: true;
      status: "finished";
      pick_order: number;
      faction_id: string;
      faction: string;
      player_id: string;
    };
