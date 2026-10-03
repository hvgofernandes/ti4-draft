import { useEffect, useState } from "react";
import type { AuthenticatedUser } from "./application/ports";
import { authGateway, draftGateway, loadRoomSnapshot } from "./application/services";
import type { DraftMembership, DraftRoomSnapshot } from "./domain/draft";
import { DraftRoom } from "./features/draft/DraftRoom";
import { Lobby } from "./features/lobby/Lobby";

export function App() {
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [membership, setMembership] = useState<DraftMembership | null>(null);
  const [roomSnapshot, setRoomSnapshot] = useState<DraftRoomSnapshot | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  async function initializeSession() {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const authenticatedUser = await authGateway.ensureAnonymousSession();
      setUser(authenticatedUser);

      const memberships = await draftGateway.findMemberships(authenticatedUser.id);
      if (memberships.length > 1) {
        throw new Error("Esta sessão participa de mais de uma sala. Não é possível escolher uma sala para restaurar automaticamente.");
      }

      if (memberships.length === 1) {
        const player = memberships[0];
        const snapshot = await loadRoomSnapshot(draftGateway, player.draft_id);
        const restoredPlayer = snapshot.players.find(
          (candidate) => candidate.id === player.id && candidate.user_id === authenticatedUser.id,
        );
        if (!restoredPlayer) {
          throw new Error("Não foi possível confirmar sua participação na sala para restaurá-la.");
        }
        setRoomSnapshot(snapshot);
        setMembership({ draft: snapshot.draft, player: restoredPlayer });
      } else {
        setRoomSnapshot(null);
        setMembership(null);
      }
    } catch (cause) {
      setAuthError(cause instanceof Error ? cause.message : "Não foi possível autenticar.");
    } finally {
      setAuthLoading(false);
    }
  }

  async function enterRoom(nextMembership: DraftMembership) {
    if (!user) throw new Error("A sessão ainda não está disponível.");
    const snapshot = await loadRoomSnapshot(draftGateway, nextMembership.draft.id);
    const player = snapshot.players.find(
      (candidate) => candidate.id === nextMembership.player.id && candidate.user_id === user.id,
    );
    if (!player) throw new Error("Não foi possível confirmar sua participação na sala.");
    setRoomSnapshot(snapshot);
    setMembership({ draft: snapshot.draft, player });
  }

  useEffect(() => {
    void initializeSession();
  }, []);

  return (
    <div className="app-frame">
      <header className="site-header">
        <a className="brand" href="/" aria-label="Twilight Draft Pick início">
          <span className="brand-mark" aria-hidden="true">✦</span>
          <span><strong>TWILIGHT</strong><small>DRAFT PICK</small></span>
        </a>
        <span className="header-caption">Draft multiplayer de facções</span>
      </header>

      {authLoading ? (
        <main className="page-shell"><div className="panel loading-panel">Conectando ao Supabase…</div></main>
      ) : authError ? (
        <main className="page-shell"><div className="panel loading-panel"><p className="feedback feedback-error" role="alert">{authError}</p><button className="button button-primary" type="button" onClick={() => void initializeSession()}>Tentar novamente</button></div></main>
      ) : membership && roomSnapshot && user ? (
        <DraftRoom
          key={membership.draft.id}
          gateway={draftGateway}
          membership={membership}
          initialSnapshot={roomSnapshot}
          userId={user.id}
          onLeave={() => { setMembership(null); setRoomSnapshot(null); }}
        />
      ) : (
        <Lobby
          gateway={draftGateway}
          onCreate={(profileId, count) => draftGateway.createDraft(profileId, count)}
          onJoin={(profileId, code) => draftGateway.joinDraft(code, profileId)}
          onJoinDraft={(profileId, draftId) => draftGateway.joinDraftById(draftId, profileId)}
          onEnter={enterRoom}
        />
      )}

      <footer className="site-footer">Twilight Imperium · Draft Pick</footer>
    </div>
  );
}
