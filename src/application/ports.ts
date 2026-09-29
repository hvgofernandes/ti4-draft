import type { Draft, DraftMembership, MakePickResult, Pick, Player } from "../domain/draft";

export interface AuthenticatedUser {
  id: string;
}

export interface AuthGateway {
  ensureAnonymousSession(): Promise<AuthenticatedUser>;
}

export interface DraftGateway {
  createDraft(playerName: string, playerCount: number): Promise<DraftMembership>;
  joinDraft(code: string, playerName: string): Promise<DraftMembership>;
  loadDraft(draftId: string): Promise<Draft>;
  loadPlayers(draftId: string): Promise<Player[]>;
  loadPicks(draftId: string): Promise<Pick[]>;
  setPlayerOrder(draftId: string, playerIds: string[]): Promise<void>;
  startDraft(draftId: string): Promise<void>;
  makePick(draftId: string, faction: string): Promise<MakePickResult>;
  subscribeToDraft(
    draftId: string,
    onChange: (draft: Draft) => void,
    onReconnect: () => void,
  ): () => void;
  subscribeToPlayers(draftId: string, onChange: () => void, onReconnect: () => void): () => void;
  subscribeToPicks(draftId: string, onChange: () => void, onReconnect: () => void): () => void;
}
