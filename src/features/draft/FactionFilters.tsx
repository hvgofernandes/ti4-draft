import type { ContentSet } from "../../domain/draft";

export type AvailabilityFilter = "all" | "available" | "picked";

interface FactionFiltersProps {
  query: string;
  contentSetId: string;
  availability: AvailabilityFilter;
  contentSets: ContentSet[];
  onQueryChange: (query: string) => void;
  onContentSetChange: (contentSetId: string) => void;
  onAvailabilityChange: (availability: AvailabilityFilter) => void;
}

export function FactionFilters(props: FactionFiltersProps) {
  return <div className="faction-filters">
    <label className="search-field">
      <span className="sr-only">Buscar facção</span>
      <input value={props.query} onChange={(event) => props.onQueryChange(event.target.value)} placeholder="Buscar facção…" type="search" />
    </label>
    <div className="filter-group" aria-label="Filtrar por conjunto de conteúdo">
      <button type="button" className={props.contentSetId === "all" ? "filter-active" : ""} onClick={() => props.onContentSetChange("all")}>Todas</button>
      {props.contentSets.map((contentSet) => <button key={contentSet.id} type="button" className={props.contentSetId === contentSet.id ? "filter-active" : ""} onClick={() => props.onContentSetChange(contentSet.id)}>{contentSet.name}</button>)}
    </div>
    <div className="filter-group" aria-label="Filtrar por disponibilidade">
      <button type="button" className={props.availability === "all" ? "filter-active" : ""} onClick={() => props.onAvailabilityChange("all")}>Todas</button>
      <button type="button" className={props.availability === "available" ? "filter-active" : ""} onClick={() => props.onAvailabilityChange("available")}>Disponíveis</button>
      <button type="button" className={props.availability === "picked" ? "filter-active" : ""} onClick={() => props.onAvailabilityChange("picked")}>Escolhidas</button>
    </div>
  </div>;
}
