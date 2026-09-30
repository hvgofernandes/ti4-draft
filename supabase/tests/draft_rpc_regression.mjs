import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createClient } from "@supabase/supabase-js";

const envText = readFileSync(new URL("../../.env.local", import.meta.url), "utf8");
const env = Object.fromEntries(
  envText
    .split(/\r?\n/)
    .filter((line) => line && !line.startsWith("#"))
    .map((line) => {
      const separator = line.indexOf("=");
      return [line.slice(0, separator), line.slice(separator + 1)];
    }),
);
const url = env.VITE_SUPABASE_URL;
const key = env.VITE_SUPABASE_PUBLISHABLE_KEY;
assert.ok(url && key, ".env.local must define the local Supabase URL and publishable key");
assert.ok(["127.0.0.1", "localhost"].includes(new URL(url).hostname), "Refusing to run against a remote Supabase project");

function client() {
  return createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
  });
}

function timeout(promise, label, ms = 15000) {
  let timer;
  return Promise.race([
    promise,
    new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(`Timed out waiting for ${label}`)), ms); }),
  ]).finally(() => clearTimeout(timer));
}

function waitForValue(readValue, label, ms = 15000) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + ms;
    const poll = () => {
      const value = readValue();
      if (value) return resolve(value);
      if (Date.now() >= deadline) return reject(new Error(`Timed out waiting for ${label}`));
      setTimeout(poll, 50);
    };
    poll();
  });
}

async function expectRpcError(request, expected) {
  const { error } = await request;
  assert.ok(error, `Expected RPC error containing: ${expected}`);
  assert.match(error.message, expected);
}

const users = await Promise.all(Array.from({ length: 4 }, async () => {
  const supabase = client();
  const { data, error } = await supabase.auth.signInAnonymously();
  assert.ifError(error);
  assert.ok(data.user);
  return { supabase, id: data.user.id };
}));

const [host, second, third, outsider] = users;
const { data: catalogSets, error: catalogSetError } = await host.supabase
  .from("content_sets").select("id,slug,active,sort_order").order("sort_order");
assert.ifError(catalogSetError);
assert.deepEqual(catalogSets.map((set) => set.slug), ["base", "pok", "thunders-edge", "discordant-stars"]);
assert.equal(new Set(catalogSets.map((set) => set.slug)).size, 4);
const { data: catalogFactions, error: catalogFactionError } = await host.supabase
  .from("factions").select("id,content_set_id,name,slug,active");
assert.ifError(catalogFactionError);
assert.equal(catalogFactions.length, 64);
assert.equal(new Set(catalogFactions.map((faction) => faction.slug)).size, 64);
assert.equal(new Set(catalogFactions.map((faction) => faction.name.toLowerCase())).size, 64);
assert.ok(catalogFactions.every((faction) => catalogSets.some((set) => set.id === faction.content_set_id)));
assert.deepEqual(catalogSets.map((set) => catalogFactions.filter((faction) => faction.content_set_id === set.id).length), [17, 7, 6, 34]);
const { data: outsiderCatalog, error: outsiderCatalogError } = await outsider.supabase
  .from("content_sets").select("id");
assert.ifError(outsiderCatalogError);
assert.equal(outsiderCatalog.length, 4);

const { data: created, error: createError } = await host.supabase.rpc("create_draft", {
  p_player_name: "RPC Test Host",
  p_player_count: 3,
});
assert.ifError(createError);
assert.ok(created?.draft?.id);
const draftId = created.draft.id;
const roomCode = created.draft.code;
const { data: baseSet, error: baseSetError } = await host.supabase
  .from("content_sets").select("id").eq("slug", "base").single();
assert.ifError(baseSetError);
const { data: enabledSets, error: enabledSetsError } = await host.supabase
  .from("draft_content_sets").select("content_set_id").eq("draft_id", draftId);
assert.ifError(enabledSetsError);
assert.deepEqual(enabledSets.map((set) => set.content_set_id), [baseSet.id]);
const { data: baseFactions, error: baseFactionsError } = await host.supabase
  .from("factions").select("id,name").eq("content_set_id", baseSet.id).order("sort_order").limit(3);
assert.ifError(baseFactionsError);
assert.equal(baseFactions.length, 3);

for (const [user, name] of [[second, "RPC Test Two"], [third, "RPC Test Three"]]) {
  const { error } = await user.supabase.rpc("join_draft", {
    p_code: roomCode,
    p_player_name: name,
  });
  assert.ifError(error);
}

const { data: initialPlayers, error: playersError } = await host.supabase
  .from("players")
  .select("id,user_id,seat")
  .eq("draft_id", draftId);
assert.ifError(playersError);
const byUser = new Map(initialPlayers.map((player) => [player.user_id, player]));
const orderedPlayers = [byUser.get(second.id), byUser.get(host.id), byUser.get(third.id)];
assert.ok(orderedPlayers.every(Boolean));

const { error: orderError } = await host.supabase.rpc("set_player_order", {
  p_draft_id: draftId,
  p_player_ids: orderedPlayers.map((player) => player.id),
});
assert.ifError(orderError);

const { data: seatedPlayers, error: seatedError } = await host.supabase
  .from("players")
  .select("id,user_id,seat")
  .eq("draft_id", draftId)
  .order("seat");
assert.ifError(seatedError);
assert.deepEqual(seatedPlayers.map((player) => player.id), orderedPlayers.map((player) => player.id));

const draftEvents = [];
const pickEvents = [];
const channelStatuses = [];
let resolveSubscribed;
const subscribed = new Promise((resolve) => { resolveSubscribed = resolve; });
const channel = third.supabase
  .channel(`rpc-regression:${draftId}`)
  .on("postgres_changes", { event: "UPDATE", schema: "public", table: "drafts", filter: `id=eq.${draftId}` }, (event) => draftEvents.push(event.new))
  .on("postgres_changes", { event: "INSERT", schema: "public", table: "picks", filter: `draft_id=eq.${draftId}` }, (event) => pickEvents.push(event.new))
  .subscribe((status) => {
    channelStatuses.push(status);
    if (status === "SUBSCRIBED") resolveSubscribed();
  });
await timeout(subscribed, "Realtime subscription");

await expectRpcError(
  second.supabase.rpc("set_draft_content_sets", { p_draft_id: draftId, p_content_set_ids: [baseSet.id, catalogSets[1].id] }),
  /Somente o host/i,
);
const { error: enableError } = await host.supabase.rpc("set_draft_content_sets", {
  p_draft_id: draftId,
  p_content_set_ids: [baseSet.id, catalogSets[1].id],
});
assert.ifError(enableError);
await waitForValue(() => draftEvents.find((draft) => draft.content_version === 1), `config Realtime update (${channelStatuses.join(",")})`);
const { data: secondEnabled, error: secondEnabledError } = await second.supabase
  .from("draft_content_sets").select("content_set_id").eq("draft_id", draftId);
assert.ifError(secondEnabledError);
assert.deepEqual(new Set(secondEnabled.map((set) => set.content_set_id)), new Set([baseSet.id, catalogSets[1].id]));
const { error: disableError } = await host.supabase.rpc("set_draft_content_sets", {
  p_draft_id: draftId,
  p_content_set_ids: [baseSet.id],
});
assert.ifError(disableError);
await waitForValue(() => draftEvents.find((draft) => draft.content_version === 2), "config disable Realtime update");
const { data: secondAfterDisable, error: secondAfterDisableError } = await second.supabase
  .from("draft_content_sets").select("content_set_id").eq("draft_id", draftId);
assert.ifError(secondAfterDisableError);
assert.deepEqual(secondAfterDisable.map((set) => set.content_set_id), [baseSet.id]);

const { error: emptyError } = await host.supabase.rpc("set_draft_content_sets", {
  p_draft_id: draftId,
  p_content_set_ids: [],
});
assert.ifError(emptyError);
await expectRpcError(
  host.supabase.rpc("start_draft", { p_draft_id: draftId }),
  /Selecione ao menos um conjunto/i,
);
const { error: restoreError } = await host.supabase.rpc("set_draft_content_sets", {
  p_draft_id: draftId,
  p_content_set_ids: [baseSet.id],
});
assert.ifError(restoreError);

const seatUsers = seatedPlayers.map((player) => users.find((user) => user.id === player.user_id));
assert.ok(seatUsers.every(Boolean));

const { error: startError } = await host.supabase.rpc("start_draft", { p_draft_id: draftId });
assert.ifError(startError);
await waitForValue(() => draftEvents.find((item) => item.status === "active"), `active Realtime update (${channelStatuses.join(",")})`);
await expectRpcError(
  host.supabase.rpc("set_draft_content_sets", { p_draft_id: draftId, p_content_set_ids: [baseSet.id, catalogSets[1].id] }),
  /aguarda jogadores/i,
);

const { data: activeDraft, error: activeError } = await host.supabase
  .from("drafts").select("status,current_player").eq("id", draftId).single();
assert.ifError(activeError);
assert.equal(activeDraft.status, "active");
assert.equal(activeDraft.current_player, seatedPlayers[0].id);
await expectRpcError(
  seatUsers[1].supabase.rpc("make_pick", { p_draft_id: draftId, p_faction_id: baseFactions[1].id }),
  /Não é a sua vez/i,
);
await expectRpcError(
  seatUsers[0].supabase.rpc("make_pick", { p_draft_id: draftId, p_faction_id: "00000000-0000-0000-0000-000000000001" }),
  /Facção inexistente/i,
);
const { data: disabledFaction, error: disabledFactionError } = await host.supabase
  .from("factions").select("id").eq("content_set_id", catalogSets[1].id).limit(1).single();
assert.ifError(disabledFactionError);
await expectRpcError(
  seatUsers[0].supabase.rpc("make_pick", { p_draft_id: draftId, p_faction_id: disabledFaction.id }),
  /não está habilitado/i,
);

await expectRpcError(
  host.supabase.rpc("set_player_order", { p_draft_id: draftId, p_player_ids: seatedPlayers.map((player) => player.id) }),
  /aguarda jogadores/i,
);

let result = await seatUsers[0].supabase.rpc("make_pick", { p_draft_id: draftId, p_faction_id: baseFactions[0].id });
assert.ifError(result.error);
assert.equal(result.data.status, "active");
assert.equal(result.data.next_player, seatedPlayers[1].id);
await expectRpcError(
  seatUsers[0].supabase.rpc("make_pick", { p_draft_id: draftId, p_faction_id: baseFactions[2].id }),
  /Não é a sua vez/i,
);
await expectRpcError(
  seatUsers[1].supabase.rpc("make_pick", { p_draft_id: draftId, p_faction_id: baseFactions[0].id }),
  /já foi escolhida/i,
);

result = await seatUsers[1].supabase.rpc("make_pick", { p_draft_id: draftId, p_faction_id: baseFactions[1].id });
assert.ifError(result.error);
assert.equal(result.data.status, "active");
assert.equal(result.data.next_player, seatedPlayers[2].id);

result = await seatUsers[2].supabase.rpc("make_pick", { p_draft_id: draftId, p_faction_id: baseFactions[2].id });
assert.ifError(result.error);
assert.equal(result.data.status, "finished");
await waitForValue(() => draftEvents.find((item) => item.status === "finished"), "finished Realtime update");
await waitForValue(() => pickEvents.length === 3 ? true : null, "three Realtime pick inserts");

const { data: finalDraft, error: finalDraftError } = await host.supabase
  .from("drafts").select("status,current_player").eq("id", draftId).single();
assert.ifError(finalDraftError);
assert.equal(finalDraft.status, "finished");
assert.equal(finalDraft.current_player, null);
await expectRpcError(
  host.supabase.rpc("set_draft_content_sets", { p_draft_id: draftId, p_content_set_ids: [baseSet.id, catalogSets[1].id] }),
  /aguarda jogadores/i,
);
const { data: picks, error: picksError } = await host.supabase
  .from("picks").select("player_id,faction_id,faction,pick_order").eq("draft_id", draftId).order("pick_order");
assert.ifError(picksError);
assert.equal(picks.length, 3);
assert.equal(new Set(picks.map((pick) => pick.faction.toLowerCase())).size, 3);
assert.deepEqual(picks.map((pick) => pick.faction_id), baseFactions.map((faction) => faction.id));
assert.deepEqual(picks.map((pick) => pick.player_id), seatedPlayers.map((player) => player.id));

for (const [table, idColumn] of [["drafts", "id"], ["players", "draft_id"], ["picks", "draft_id"], ["draft_content_sets", "draft_id"]]) {
  const { data, error } = await outsider.supabase.from(table).select("*").eq(idColumn, draftId);
  assert.ifError(error);
  assert.equal(data.length, 0, `Nonparticipant could read ${table}`);
}

await Promise.all(users.map(({ supabase }) => supabase.removeAllChannels()));
for (const { supabase } of users) supabase.realtime.disconnect();
console.log("PASS: local anonymous auth and create/join");
console.log("PASS: catalog totals, unique slugs/names, valid set references, outsider catalog access");
console.log("PASS: Base default, host config enable/disable, non-host rejection, empty config rejection");
console.log("PASS: config Realtime updates, active/finished config freeze");
console.log("PASS: host seat swap and exact seat order");
console.log("PASS: out-of-turn, nonexistent/disabled/duplicate-faction rejection");
console.log("PASS: start/current_player, three distinct picks, finished state");
console.log("PASS: Realtime draft updates and all three pick inserts");
console.log("PASS: RLS hides draft data from a nonparticipant");
