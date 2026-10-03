import type { ContentSet, Draft, DraftContentSet, DraftMembership, Faction, JoinableDraft, Pick as DraftPick, MakePickResult, Player, PlayerProfile } from "../../domain/draft";

type Table<Row, Insert, Update = Partial<Insert>> = {
  Row: Row;
  Insert: Insert;
  Update: Update;
  Relationships: [];
};

export type Database = {
  public: {
    Tables: {
      drafts: Table<
        Draft,
        Omit<Draft, "id" | "created_at" | "status" | "picks_per_player" | "host_id" | "current_player"> &
          Partial<Pick<Draft, "id" | "created_at" | "status" | "picks_per_player" | "host_id" | "current_player">>
      >;
      players: Table<
        Player,
        Omit<Player, "id" | "joined_at" | "connected" | "seat" | "user_id"> &
          Partial<Pick<Player, "id" | "joined_at" | "connected" | "seat" | "user_id">>
      >;
      picks: Table<
        DraftPick,
        Omit<DraftPick, "id" | "created_at"> & Partial<Pick<DraftPick, "id" | "created_at">>
      >;
      content_sets: Table<ContentSet, ContentSet>;
      factions: Table<Faction, Faction>;
      draft_content_sets: Table<DraftContentSet, DraftContentSet>;
      player_profiles: Table<
        { id: string; name: string; sort_order: number; active: boolean; created_at: string },
        never
      >;
      draft_discovery_signals: Table<
        { draft_id: string; revision: number; updated_at: string },
        { draft_id: string; revision?: number; updated_at?: string }
      >;
    };
    Views: { [_ in never]: never };
    Functions: {
      create_draft: {
        Args: { p_profile_id: string; p_player_count: number };
        Returns: DraftMembership;
      };
      join_draft: {
        Args: { p_code: string; p_profile_id: string } | { p_draft_id: string; p_profile_id: string };
        Returns: DraftMembership;
      };
      list_player_profiles: {
        Args: { p_draft_id?: string };
        Returns: PlayerProfile[];
      };
      list_joinable_drafts: {
        Args: Record<string, never>;
        Returns: JoinableDraft[];
      };
      set_player_order: {
        Args: { p_draft_id: string; p_player_ids: string[] };
        Returns: { success: boolean; player_count: number };
      };
      start_draft: {
        Args: { p_draft_id: string };
        Returns: { success: boolean; status: "active"; current_player: string };
      };
      make_pick: {
        Args: { p_draft_id: string; p_faction_id: string };
        Returns: MakePickResult;
      };
      set_draft_content_sets: {
        Args: { p_draft_id: string; p_content_set_ids: string[] };
        Returns: undefined;
      };
      is_draft_participant: {
        Args: { p_draft_id: string };
        Returns: boolean;
      };
    };
    Enums: { [_ in never]: never };
    CompositeTypes: { [_ in never]: never };
  };
};
