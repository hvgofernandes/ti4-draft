import type { ContentSet, Draft, DraftMembership, Faction, JoinableDraft, MakePickResult, Pick, Player, PlayerProfile } from "../../domain/draft";
import type { DraftGateway } from "../../application/ports";
import { supabase } from "./client";

function requireData<T>(data: T | null, error: { message: string } | null): T {
  if (error) throw new Error(error.message);
  if (data === null) throw new Error("O serviço não retornou dados.");
  return data;
}

export class SupabaseDraftGateway implements DraftGateway {
  async findMemberships(userId: string): Promise<Player[]> {
    const { data, error } = await supabase
      .from("players")
      .select("*")
      .eq("user_id", userId);
    return requireData(data, error);
  }

  async loadProfiles(draftId?: string): Promise<PlayerProfile[]> {
    const { data, error } = await supabase.rpc("list_player_profiles", {
      p_draft_id: draftId ?? undefined,
    });
    return requireData(data, error);
  }

  async listJoinableDrafts(): Promise<JoinableDraft[]> {
    const { data, error } = await supabase.rpc("list_joinable_drafts");
    return requireData(data, error);
  }

  async createDraft(profileId: string, playerCount: number): Promise<DraftMembership> {
    const { data, error } = await supabase.rpc("create_draft", {
      p_profile_id: profileId,
      p_player_count: playerCount,
    });
    return requireData(data, error);
  }

  async joinDraft(code: string, profileId: string): Promise<DraftMembership> {
    const { data, error } = await supabase.rpc("join_draft", {
      p_code: code,
      p_profile_id: profileId,
    });
    return requireData(data, error);
  }

  async joinDraftById(draftId: string, profileId: string): Promise<DraftMembership> {
    const { data, error } = await supabase.rpc("join_draft", {
      p_draft_id: draftId,
      p_profile_id: profileId,
    });
    return requireData(data, error);
  }

  async loadDraft(draftId: string): Promise<Draft> {
    const { data, error } = await supabase
      .from("drafts")
      .select("*")
      .eq("id", draftId)
      .single();
    return requireData(data, error);
  }

  async loadPlayers(draftId: string): Promise<Player[]> {
    const { data, error } = await supabase
      .from("players")
      .select("*")
      .eq("draft_id", draftId)
      .order("seat", { ascending: true, nullsFirst: false })
      .order("joined_at", { ascending: true });
    return requireData(data, error);
  }

  async loadPicks(draftId: string): Promise<Pick[]> {
    const { data, error } = await supabase
      .from("picks")
      .select("*")
      .eq("draft_id", draftId)
      .order("pick_order", { ascending: true });
    return requireData(data, error);
  }

  async loadContentSets(): Promise<ContentSet[]> {
    const { data, error } = await supabase
      .from("content_sets")
      .select("*")
      .order("sort_order", { ascending: true });
    return requireData(data, error);
  }

  async loadFactions(): Promise<Faction[]> {
    const { data, error } = await supabase
      .from("factions")
      .select("*")
      .order("sort_order", { ascending: true });
    return requireData(data, error);
  }

  async loadEnabledContentSetIds(draftId: string): Promise<string[]> {
    const { data, error } = await supabase
      .from("draft_content_sets")
      .select("content_set_id")
      .eq("draft_id", draftId);
    return requireData(data, error).map(({ content_set_id }) => content_set_id);
  }

  async setDraftContentSets(draftId: string, contentSetIds: string[]): Promise<void> {
    const { error } = await supabase.rpc("set_draft_content_sets", {
      p_draft_id: draftId,
      p_content_set_ids: contentSetIds,
    });
    if (error) throw new Error(error.message);
  }

  async setPlayerOrder(draftId: string, playerIds: string[]): Promise<void> {
    const { error } = await supabase.rpc("set_player_order", {
      p_draft_id: draftId,
      p_player_ids: playerIds,
    });
    if (error) throw new Error(error.message);
  }

  async startDraft(draftId: string): Promise<void> {
    const { error } = await supabase.rpc("start_draft", { p_draft_id: draftId });
    if (error) throw new Error(error.message);
  }

  async makePick(draftId: string, factionId: string): Promise<MakePickResult> {
    const { data, error } = await supabase.rpc("make_pick", {
      p_draft_id: draftId,
      p_faction_id: factionId,
    });
    return requireData(data, error);
  }

  subscribeToDraft(
    draftId: string,
    onChange: (draft: Draft) => void,
    onReconnect: () => void,
  ): () => void {
    const channel = supabase
      .channel(`draft:${draftId}`)
      .on(
        "postgres_changes",
        { event: "UPDATE", schema: "public", table: "drafts", filter: `id=eq.${draftId}` },
        (payload) => onChange(payload.new as Draft),
      )
      .subscribe((status) => {
        if (status === "SUBSCRIBED") onReconnect();
      });

    return () => {
      void supabase.removeChannel(channel);
    };
  }

  subscribeToPlayers(draftId: string, onChange: () => void, onReconnect: () => void): () => void {
    const channel = supabase
      .channel(`players:${draftId}`)
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "players", filter: `draft_id=eq.${draftId}` },
        onChange,
      )
      .subscribe((status) => {
        if (status === "SUBSCRIBED") onReconnect();
      });

    return () => {
      void supabase.removeChannel(channel);
    };
  }

  subscribeToPicks(draftId: string, onChange: () => void, onReconnect: () => void): () => void {
    const channel = supabase
      .channel(`picks:${draftId}`)
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "picks", filter: `draft_id=eq.${draftId}` },
        onChange,
      )
      .subscribe((status) => {
        if (status === "SUBSCRIBED") onReconnect();
      });

    return () => {
      void supabase.removeChannel(channel);
    };
  }

  subscribeToLobby(onChange: () => void, onReconnect: () => void): () => void {
    const channel = supabase
      .channel("draft-discovery")
      .on("postgres_changes", { event: "*", schema: "public", table: "draft_discovery_signals" }, onChange)
      .subscribe((status) => {
        if (status === "SUBSCRIBED") onReconnect();
      });

    return () => {
      void supabase.removeChannel(channel);
    };
  }
}
