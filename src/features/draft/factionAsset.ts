import type { ContentSet, Faction } from "../../domain/draft";

const assetDirectoryByContentSet: Record<string, string> = {
  base: "base",
  pok: "pok",
  "thunders-edge": "thunders-edge",
  "thunder-s-edge": "thunders-edge",
  "discordant-stars": "discordant-stars",
};

/**
 * The Vite public directory exposes the reviewed, normalized PNG candidates
 * under /faction-assets. The database remains the source of faction identity.
 */
export function factionAssetUrl(faction: Faction, contentSets: ContentSet[]): string | null {
  const contentSet = contentSets.find((candidate) => candidate.id === faction.content_set_id);
  const directory = contentSet ? assetDirectoryByContentSet[contentSet.slug] : undefined;
  return directory ? `/faction-assets/${directory}/${faction.slug}.png` : null;
}

export function contentSetLabel(faction: Faction, contentSets: ContentSet[]): string {
  return contentSets.find((candidate) => candidate.id === faction.content_set_id)?.name ?? "Conteúdo adicional";
}
