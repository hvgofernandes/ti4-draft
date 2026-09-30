import type { ContentSet, Draft, DraftMembership, Faction, MakePickResult, Pick, Player } from "../domain/draft";

export interface AuthenticatedUser {
  id: string;
}

export interface AuthGateway {
  ensureAnonymousSession(): Promise<AuthenticatedUser>;
}

export interface DraftGateway {
  findMemberships(userId: string): Promise<Player[]>;
  createDraft(playerName: string, playerCount: number): Promise<DraftMembership>;
  joinDraft(code: string, playerName: string): Promise<DraftMembership>;
  loadDraft(draftId: string): Promise<Draft>;
  loadPlayers(draftId: string): Promise<Player[]>;
  loadPicks(draftId: string): Promise<Pick[]>;
  loadContentSets(): Promise<ContentSet[]>;
  loadFactions(): Promise<Faction[]>;
  loadEnabledContentSetIds(draftId: string): Promise<string[]>;
  setDraftContentSets(draftId: string, contentSetIds: string[]): Promise<void>;
  setPlayerOrder(draftId: string, playerIds: string[]): Promise<void>;
  startDraft(draftId: string): Promise<void>;
  makePick(draftId: string, factionId: string): Promise<MakePickResult>;
  subscribeToDraft(
    draftId: string,
    onChange: (draft: Draft) => void,
    onReconnect: () => void,
  ): () => void;
  subscribeToPlayers(draftId: string, onChange: () => void, onReconnect: () => void): () => void;
  subscribeToPicks(draftId: string, onChange: () => void, onReconnect: () => void): () => void;
}
