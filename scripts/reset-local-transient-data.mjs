import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createClient } from "@supabase/supabase-js";

const execute = process.argv.includes("--execute");
const status = spawnSync("supabase status --output env", {
  cwd: process.cwd(),
  encoding: "utf8",
  shell: true,
});

if (status.status !== 0) {
  throw new Error(`Não foi possível consultar o Supabase local.\n${status.stderr.trim()}`);
}

const localEnv = Object.fromEntries(
  status.stdout
    .split(/\r?\n/)
    .map((line) => line.match(/^([A-Z0-9_]+)=(?:"(.*)"|(.*))$/))
    .filter(Boolean)
    .map((match) => [match[1], match[2] ?? match[3]]),
);
const apiUrl = localEnv.API_URL;
const serviceRoleKey = localEnv.SERVICE_ROLE_KEY ?? localEnv.SECRET_KEY;

assert.ok(apiUrl && serviceRoleKey, "O Supabase CLI não retornou a URL e a chave administrativa locais.");
const parsedUrl = new URL(apiUrl);
assert.ok(
  ["127.0.0.1", "localhost", "::1"].includes(parsedUrl.hostname),
  `RECUSADO: o endpoint ${parsedUrl.hostname} não é local.`,
);

const supabase = createClient(apiUrl, serviceRoleKey, {
  auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
});
const { data: draftRows, error: draftsError } = await supabase
  .from("drafts")
  .select("id,code,status,player_count,created_at")
  .order("created_at");
if (draftsError) throw new Error(draftsError.message);
const { data: playerRows, error: playersError } = await supabase
  .from("players")
  .select("draft_id,name,profile_id")
  .order("joined_at");
if (playersError) throw new Error(playersError.message);
const drafts = draftRows.map((draft) => ({
  ...draft,
  players: playerRows.filter((player) => player.draft_id === draft.id),
}));

const summary = Object.fromEntries(
  ["waiting", "active", "finished"].map((statusName) => [
    statusName,
    drafts.filter((draft) => draft.status === statusName).length,
  ]),
);
const joinable = drafts.filter(
  (draft) => draft.status === "waiting" && draft.players.length < draft.player_count,
);

console.log(`LOCAL confirmado: ${apiUrl}`);
console.log(`Drafts encontrados: ${drafts.length} (${summary.waiting} waiting, ${summary.active} active, ${summary.finished} finished)`);
console.log(`Visíveis na Session Discovery: ${joinable.length}`);
for (const draft of drafts) {
  console.log(`${draft.code} | ${draft.status} | ${draft.players.length}/${draft.player_count} | ${draft.players.map((player) => player.name).join(", ")}`);
}

if (!execute) {
  console.log("AUDITORIA APENAS. Para excluir os dados transitórios locais, execute: npm run dev:reset-local-data -- --execute");
  process.exit(0);
}

const { error: clearCurrentPlayerError } = await supabase
  .from("drafts")
  .update({ current_player: null })
  .not("current_player", "is", null);
if (clearCurrentPlayerError) throw new Error(clearCurrentPlayerError.message);

const { error: deleteError } = await supabase
  .from("drafts")
  .delete()
  .not("id", "is", null);
if (deleteError) throw new Error(deleteError.message);

const checks = await Promise.all([
  supabase.from("drafts").select("id", { count: "exact", head: true }),
  supabase.from("players").select("id", { count: "exact", head: true }),
  supabase.from("picks").select("id", { count: "exact", head: true }),
  supabase.from("player_profiles").select("id", { count: "exact", head: true }),
  supabase.from("factions").select("id", { count: "exact", head: true }),
  supabase.from("content_sets").select("id", { count: "exact", head: true }),
]);
for (const result of checks) if (result.error) throw new Error(result.error.message);
const [draftCount, playerCount, pickCount, profileCount, factionCount, contentSetCount] = checks.map((result) => result.count);

assert.equal(draftCount, 0, "Ainda existem drafts após a limpeza.");
assert.equal(playerCount, 0, "Ainda existem participantes transitórios após a limpeza.");
assert.equal(pickCount, 0, "Ainda existem picks transitórios após a limpeza.");
assert.equal(profileCount, 6, "A limpeza alterou os perfis persistentes.");
assert.equal(factionCount, 64, "A limpeza alterou o catálogo de facções.");
assert.equal(contentSetCount, 4, "A limpeza alterou os content sets.");

console.log("LIMPEZA LOCAL CONCLUÍDA: drafts, players, picks e dependências removidos.");
console.log("PRESERVADO: 6 profiles, 64 factions, 4 content sets, schema e migrations.");
