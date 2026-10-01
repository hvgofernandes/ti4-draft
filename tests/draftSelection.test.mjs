import assert from "node:assert/strict";
import test from "node:test";

import {
  canUserPick,
  getEnabledFactions,
  getFactionAvailability,
} from "../.test-build/src/application/draftSelection.js";

const base = { id: "base", name: "Base Game", slug: "base", active: true, sort_order: 1 };
const pok = { id: "pok", name: "Prophecy of Kings", slug: "pok", active: true, sort_order: 2 };
const disabledSet = { id: "ds", name: "Discordant Stars", slug: "discordant-stars", active: false, sort_order: 3 };

const factions = [
  { id: "sol", content_set_id: "base", name: "Federation of Sol", slug: "sol", active: true, sort_order: 2 },
  { id: "arborec", content_set_id: "base", name: "The Arborec", slug: "arborec", active: true, sort_order: 1 },
  { id: "nekro", content_set_id: "pok", name: "The Nekro Virus", slug: "nekro", active: true, sort_order: 1 },
  { id: "vaden", content_set_id: "ds", name: "The Vaden Banking Clans", slug: "vaden", active: true, sort_order: 1 },
  { id: "retired", content_set_id: "base", name: "Retired", slug: "retired", active: false, sort_order: 9 },
];

function snapshot(overrides = {}) {
  return {
    draft: {
      id: "draft-1", code: "ABCD", status: "active", player_count: 2, picks_per_player: 1,
      created_at: "2026-01-01T00:00:00Z", host_id: "user-a", current_player: "player-a", content_version: 1,
    },
    players: [
      { id: "player-a", draft_id: "draft-1", name: "Ana", seat: 1, connected: true, joined_at: "2026-01-01T00:00:00Z", user_id: "user-a" },
      { id: "player-b", draft_id: "draft-1", name: "Bruno", seat: 2, connected: true, joined_at: "2026-01-01T00:00:01Z", user_id: "user-b" },
    ],
    picks: [],
    contentSets: [base, pok, disabledSet],
    factions,
    enabledContentSetIds: ["base", "pok", "ds"],
    ...overrides,
  };
}

test("catalog respects enabled and active content sets, then sorts by name", () => {
  const result = getEnabledFactions(snapshot({ enabledContentSetIds: ["base", "ds"] }));
  assert.deepEqual(result.map((faction) => faction.id), ["sol", "arborec"]);
});

test("picked factions stay visible and are unavailable with their authoritative pick", () => {
  const pick = {
    id: "pick-1", draft_id: "draft-1", player_id: "player-a", faction_id: "sol",
    faction: "Federation of Sol", pick_order: 1, created_at: "2026-01-01T00:02:00Z",
  };
  const result = getFactionAvailability(snapshot({ picks: [pick] }));
  const sol = result.find((entry) => entry.faction.id === "sol");
  const arborec = result.find((entry) => entry.faction.id === "arborec");

  assert.deepEqual(result.map((entry) => entry.faction.name), ["Federation of Sol", "The Arborec", "The Nekro Virus"]);
  assert.equal(sol?.available, false);
  assert.equal(sol?.pick, pick);
  assert.equal(arborec?.available, true);
  assert.equal(arborec?.pick, null);
});

test("only the user that owns the current player can confirm during an active draft", () => {
  const active = snapshot();
  assert.equal(canUserPick(active, "user-a"), true);
  assert.equal(canUserPick(active, "user-b"), false);
  assert.equal(canUserPick(active, "spectator"), false);
  assert.equal(canUserPick(snapshot({ draft: { ...active.draft, status: "waiting" } }), "user-a"), false);
  assert.equal(canUserPick(snapshot({ draft: { ...active.draft, status: "finished", current_player: null } }), "user-a"), false);
});

test("a realtime turn update makes the next player eligible without relying on stale pick state", () => {
  const before = snapshot();
  const after = snapshot({
    draft: { ...before.draft, current_player: "player-b" },
    picks: [{
      id: "pick-1", draft_id: "draft-1", player_id: "player-a", faction_id: "sol",
      faction: "Federation of Sol", pick_order: 1, created_at: "2026-01-01T00:02:00Z",
    }],
  });

  assert.equal(canUserPick(before, "user-b"), false);
  assert.equal(canUserPick(after, "user-a"), false);
  assert.equal(canUserPick(after, "user-b"), true);
  assert.equal(getFactionAvailability(after).find((entry) => entry.faction.id === "sol")?.available, false);
});
