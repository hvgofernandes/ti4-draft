import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createClient } from "@supabase/supabase-js";

const env = Object.fromEntries(
  readFileSync(new URL("../../.env.local", import.meta.url), "utf8")
    .split(/\r?\n/)
    .filter((line) => line && !line.startsWith("#"))
    .map((line) => {
      const at = line.indexOf("=");
      return [line.slice(0, at), line.slice(at + 1)];
    }),
);
const url = env.VITE_SUPABASE_URL;
const key = env.VITE_SUPABASE_PUBLISHABLE_KEY;
assert.ok(url && key);
assert.ok(["127.0.0.1", "localhost"].includes(new URL(url).hostname));

async function anonymousClient() {
  const supabase = createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
  });
  const { data, error } = await supabase.auth.signInAnonymously();
  assert.ifError(error);
  return { supabase, userId: data.user.id };
}

const sessions = await Promise.all(Array.from({ length: 7 }, anonymousClient));
const [host, p2, p3, concurrentA, concurrentB, legacyHost, legacyGuest] = sessions;

function waitFor(readValue, label, milliseconds = 15000) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + milliseconds;
    const poll = () => {
      const value = readValue();
      if (value) return resolve(value);
      if (Date.now() >= deadline) return reject(new Error(`Timed out waiting for ${label}`));
      setTimeout(poll, 50);
    };
    poll();
  });
}

const { data: profiles, error: profilesError } = await host.supabase.rpc("list_player_profiles");
assert.ifError(profilesError);
assert.deepEqual(profiles.map(({ name }) => name), ["Gus", "Lucca", "Arthur", "Lustosa", "Phinha", "JP"]);
assert.equal(new Set(profiles.map(({ id }) => id)).size, 6);
assert.ok(profiles.every(({ unavailable }) => unavailable === false));
const [gus, lucca, arthur] = profiles;

const discoverySignals = [];
let subscribed = false;
const discoveryChannel = p2.supabase
  .channel("phase-3-3-discovery")
  .on("postgres_changes", {
    event: "*", schema: "public", table: "draft_discovery_signals",
  }, (event) => discoverySignals.push(event))
  .subscribe((status) => { subscribed = status === "SUBSCRIBED"; });
await waitFor(() => subscribed, "discovery Realtime subscription");

const { data: created, error: createError } = await host.supabase.rpc("create_draft", {
  p_profile_id: gus.id,
  p_player_count: 3,
});
assert.ifError(createError);
assert.equal(created.player.profile_id, gus.id);
assert.equal(created.player.name, "Gus");
const draftId = created.draft.id;
await waitFor(
  () => discoverySignals.find(({ new: row }) => row?.draft_id === draftId),
  "new draft discovery signal",
);

let discovery = await p2.supabase.rpc("list_joinable_drafts");
assert.ifError(discovery.error);
let card = discovery.data.find(({ draft_id }) => draft_id === draftId);
assert.ok(card);
assert.equal(card.host_profile_id, gus.id);
assert.equal(card.host_name, "Gus");
assert.equal(card.player_count, 1);
assert.equal(card.capacity, 3);
assert.deepEqual(card.used_profile_ids, [gus.id]);

const availability = await p2.supabase.rpc("list_player_profiles", { p_draft_id: draftId });
assert.ifError(availability.error);
assert.equal(availability.data.find(({ id }) => id === gus.id).unavailable, true);
assert.equal(availability.data.find(({ id }) => id === lucca.id).unavailable, false);

const directJoin = await p2.supabase.rpc("join_draft", {
  p_draft_id: draftId,
  p_profile_id: lucca.id,
});
assert.ifError(directJoin.error);
const codeJoin = await p3.supabase.rpc("join_draft", {
  p_code: created.draft.code,
  p_profile_id: arthur.id,
});
assert.ifError(codeJoin.error);

discovery = await p2.supabase.rpc("list_joinable_drafts");
assert.ifError(discovery.error);
assert.equal(discovery.data.some(({ draft_id }) => draft_id === draftId), false, "full draft must disappear");

const restoredMembership = await p2.supabase
  .from("players")
  .select("*")
  .eq("user_id", p2.userId)
  .eq("draft_id", draftId)
  .single();
assert.ifError(restoredMembership.error);
assert.equal(restoredMembership.data.profile_id, lucca.id, "anonymous session must restore its profile membership");
const restoredDraft = await p2.supabase.from("drafts").select("*").eq("id", draftId).single();
assert.ifError(restoredDraft.error);
assert.equal(restoredDraft.data.status, "waiting");

const { data: baseSet, error: baseSetError } = await host.supabase
  .from("content_sets").select("id").eq("slug", "base").single();
assert.ifError(baseSetError);
const configured = await host.supabase.rpc("set_draft_content_sets", {
  p_draft_id: draftId,
  p_content_set_ids: [baseSet.id],
});
assert.ifError(configured.error);
const { data: participants, error: participantError } = await host.supabase
  .from("players").select("id,user_id").eq("draft_id", draftId).order("joined_at");
assert.ifError(participantError);
const orderedIds = participants.map(({ id }) => id);
const ordered = await host.supabase.rpc("set_player_order", {
  p_draft_id: draftId,
  p_player_ids: orderedIds,
});
assert.ifError(ordered.error);
const started = await host.supabase.rpc("start_draft", { p_draft_id: draftId });
assert.ifError(started.error);

const { data: baseFactions, error: factionError } = await host.supabase
  .from("factions").select("id").eq("content_set_id", baseSet.id).order("sort_order").limit(3);
assert.ifError(factionError);
const sessionsByUser = new Map([host, p2, p3].map((session) => [session.userId, session]));
for (let index = 0; index < participants.length; index += 1) {
  const picker = sessionsByUser.get(participants[index].user_id);
  assert.ok(picker);
  const pick = await picker.supabase.rpc("make_pick", {
    p_draft_id: draftId,
    p_faction_id: baseFactions[index].id,
  });
  assert.ifError(pick.error);
}
const finishedDraft = await host.supabase.from("drafts").select("status,current_player").eq("id", draftId).single();
assert.ifError(finishedDraft.error);
assert.equal(finishedDraft.data.status, "finished");
assert.equal(finishedDraft.data.current_player, null);
const finalPicks = await host.supabase.from("picks").select("id").eq("draft_id", draftId);
assert.ifError(finalPicks.error);
assert.equal(finalPicks.data.length, 3);
discovery = await p2.supabase.rpc("list_joinable_drafts");
assert.ifError(discovery.error);
assert.equal(discovery.data.some(({ draft_id }) => draft_id === draftId), false);

const { data: raceDraft, error: raceCreateError } = await host.supabase.rpc("create_draft", {
  p_profile_id: gus.id,
  p_player_count: 4,
});
assert.ifError(raceCreateError);
const race = await Promise.all([
  concurrentA.supabase.rpc("join_draft", { p_draft_id: raceDraft.draft.id, p_profile_id: lucca.id }),
  concurrentB.supabase.rpc("join_draft", { p_draft_id: raceDraft.draft.id, p_profile_id: lucca.id }),
]);
assert.equal(race.filter(({ error }) => !error).length, 1);
assert.equal(race.filter(({ error }) => error && /perfil já está/i.test(error.message)).length, 1);

const legacyCreate = await legacyHost.supabase.rpc("create_draft", {
  p_player_name: "Legacy Host",
  p_player_count: 3,
});
assert.ifError(legacyCreate.error);
assert.equal(legacyCreate.data.player.profile_id, null);
const legacyJoin = await legacyGuest.supabase.rpc("join_draft", {
  p_code: legacyCreate.data.draft.code,
  p_player_name: "Legacy Guest",
});
assert.ifError(legacyJoin.error);
assert.equal(legacyJoin.data.player.profile_id, null);

const forbiddenProfiles = await host.supabase.from("player_profiles").select("*");
assert.ok(forbiddenProfiles.error, "profiles table must not be directly readable");
const outsiderPlayers = await concurrentA.supabase.from("players").select("*").eq("draft_id", draftId);
assert.ifError(outsiderPlayers.error);
assert.equal(outsiderPlayers.data.length, 0);

for (const { supabase } of sessions) {
  await supabase.removeAllChannels();
  supabase.realtime.disconnect();
}
console.log("PASS: exactly six stable seeded profiles through the safe RPC");
console.log("PASS: profile create, direct join, room-code join, availability and full-room discovery");
console.log("PASS: anonymous-session restoration and profile draft flow through configuration, order, picks and finished");
console.log("PASS: concurrent duplicate profile selection accepts exactly one request");
console.log("PASS: legacy name-based create/join remains compatible");
console.log("PASS: profiles have no direct SELECT and participant RLS remains private");
console.log("PASS: minimal discovery signal is delivered through Realtime");
