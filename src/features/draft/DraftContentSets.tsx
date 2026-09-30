import type { ContentSet, Faction } from "../../domain/draft";

interface DraftContentSetsProps {
  contentSets: ContentSet[];
  factions: Faction[];
  enabledContentSetIds: string[];
  playerCount: number;
  editable: boolean;
  saving: boolean;
  onToggle: (contentSetId: string, enabled: boolean) => void;
}

export function DraftContentSets({
  contentSets,
  factions,
  enabledContentSetIds,
  playerCount,
  editable,
  saving,
  onToggle,
}: DraftContentSetsProps) {
  const enabled = new Set(enabledContentSetIds);
  const availableSetIds = new Set(
    contentSets.filter((contentSet) => contentSet.active && enabled.has(contentSet.id)).map((contentSet) => contentSet.id),
  );
  const availableFactions = factions.filter(
    (faction) => faction.active && availableSetIds.has(faction.content_set_id),
  ).length;

  return (
    <section className="room-section content-section" aria-labelledby="content-heading">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Configuração</span>
          <h3 id="content-heading">Conteúdo do draft</h3>
          <p className="section-copy">
            {editable ? "Escolha os conjuntos disponíveis nesta sala." : "Conjuntos disponíveis nesta sala."}
          </p>
        </div>
        {saving && <span className="feedback-muted" role="status">Salvando…</span>}
      </div>
      <div className="content-set-list">
        {contentSets.map((contentSet) => {
          const checked = enabled.has(contentSet.id);
          const factionCount = factions.filter(
            (faction) => faction.active && faction.content_set_id === contentSet.id,
          ).length;
          return (
            <label className="content-set-row" key={contentSet.id}>
              <input
                type="checkbox"
                checked={checked}
                disabled={!editable || saving || !contentSet.active}
                onChange={(event) => onToggle(contentSet.id, event.target.checked)}
              />
              <span className="content-set-name">{contentSet.name}</span>
              <span className="content-set-count">{factionCount} facções</span>
            </label>
          );
        })}
      </div>
      <p className="content-availability" aria-live="polite">
        Facções disponíveis: <strong>{availableFactions}</strong>
        {availableFactions < playerCount && (
          <span className="content-shortage"> · São necessárias ao menos {playerCount} para iniciar.</span>
        )}
      </p>
    </section>
  );
}
