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
};

export type Player = {
  id: string;
  draft_id: string;
  name: string;
  seat: number | null;
  connected: boolean;
  joined_at: string;
  user_id: string | null;
};

export type Pick = {
  id: string;
  draft_id: string;
  player_id: string;
  faction: string;
  pick_order: number;
  created_at: string;
};

export type DraftMembership = {
  draft: Draft;
  player: Player;
};

export type MakePickResult =
  | {
      success: true;
      status: "active";
      pick_order: number;
      faction: string;
      player_id: string;
      next_player: string;
    }
  | {
      success: true;
      status: "finished";
      pick_order: number;
      faction: string;
      player_id: string;
    };
