import { useState, type FormEvent } from "react";
import type { DraftMembership } from "../../domain/draft";

interface LobbyProps {
  onCreate: (name: string, playerCount: number) => Promise<DraftMembership>;
  onJoin: (name: string, code: string) => Promise<DraftMembership>;
  onEnter: (membership: DraftMembership) => void;
}

export function Lobby({ onCreate, onJoin, onEnter }: LobbyProps) {
  const [createName, setCreateName] = useState("");
  const [joinName, setJoinName] = useState("");
  const [roomCode, setRoomCode] = useState("");
  const [playerCount, setPlayerCount] = useState(6);
  const [busy, setBusy] = useState<"create" | "join" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("create");
    setError(null);
    try {
      onEnter(await onCreate(createName.trim(), playerCount));
    } catch (cause) {
      setError(messageOf(cause));
    } finally {
      setBusy(null);
    }
  }

  async function submitJoin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("join");
    setError(null);
    try {
      onEnter(await onJoin(joinName.trim(), roomCode.trim().toUpperCase()));
    } catch (cause) {
      setError(messageOf(cause));
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="page-shell">
      <section className="panel lobby-panel" aria-labelledby="create-heading">
        <div className="panel-heading">
          <span className="eyebrow">Twilight Imperium</span>
          <h2 id="create-heading">Criar novo draft</h2>
          <p>Monte uma sala e convide seus amigos pelo código.</p>
        </div>
        <form className="form-stack" onSubmit={submitCreate}>
          <label className="field-label" htmlFor="create-name">Seu nome</label>
          <input
            id="create-name"
            autoComplete="nickname"
            maxLength={20}
            placeholder="Como podemos chamar você?"
            required
            value={createName}
            onChange={(event) => setCreateName(event.target.value)}
          />
          <label className="field-label" htmlFor="player-count">Jogadores na sala</label>
          <select id="player-count" value={playerCount} onChange={(event) => setPlayerCount(Number(event.target.value))}>
            {[3, 4, 5, 6].map((count) => <option key={count} value={count}>{count} jogadores</option>)}
          </select>
          <button className="button button-primary" disabled={busy !== null} type="submit">
            {busy === "create" ? "Criando sala…" : "Criar sala"}
          </button>
        </form>

        <div className="divider"><span>ou entre em uma sala</span></div>

        <form className="form-stack" onSubmit={submitJoin}>
          <label className="field-label" htmlFor="join-name">Seu nome</label>
          <input
            id="join-name"
            autoComplete="nickname"
            maxLength={20}
            placeholder="Como podemos chamar você?"
            required
            value={joinName}
            onChange={(event) => setJoinName(event.target.value)}
          />
          <label className="field-label" htmlFor="room-code">Código da sala</label>
          <input
            id="room-code"
            autoCapitalize="characters"
            maxLength={6}
            placeholder="Ex.: A1B2C3"
            required
            value={roomCode}
            onChange={(event) => setRoomCode(event.target.value.toUpperCase())}
          />
          <button className="button button-secondary" disabled={busy !== null} type="submit">
            {busy === "join" ? "Entrando…" : "Entrar na sala"}
          </button>
        </form>
        {error && <p className="feedback feedback-error" role="alert">{error}</p>}
      </section>
    </main>
  );
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "Ocorreu um erro inesperado.";
}
