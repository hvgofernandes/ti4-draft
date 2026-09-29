import { useEffect, useState } from "react";
import type { AuthenticatedUser } from "./application/ports";
import { authGateway, draftGateway } from "./application/services";
import type { DraftMembership } from "./domain/draft";
import { DraftRoom } from "./features/draft/DraftRoom";
import { Lobby } from "./features/lobby/Lobby";

export function App() {
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [membership, setMembership] = useState<DraftMembership | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  async function initializeSession() {
    setAuthLoading(true);
    setAuthError(null);
    try {
      setUser(await authGateway.ensureAnonymousSession());
    } catch (cause) {
      setAuthError(cause instanceof Error ? cause.message : "Não foi possível autenticar.");
    } finally {
      setAuthLoading(false);
    }
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
      ) : membership && user ? (
        <DraftRoom
          key={membership.draft.id}
          gateway={draftGateway}
          membership={membership}
          userId={user.id}
          onLeave={() => setMembership(null)}
        />
      ) : (
        <Lobby
          onCreate={(name, count) => draftGateway.createDraft(name, count)}
          onJoin={(name, code) => draftGateway.joinDraft(code, name)}
          onEnter={setMembership}
        />
      )}

      <footer className="site-footer">Twilight Imperium · Draft Pick</footer>
    </div>
  );
}
