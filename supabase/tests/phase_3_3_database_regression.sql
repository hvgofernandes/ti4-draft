BEGIN;

SELECT plan(6);

SELECT is(
    (SELECT array_agg(name ORDER BY sort_order) FROM public.player_profiles),
    ARRAY['Gus', 'Lucca', 'Arthur', 'Lustosa', 'Phinha', 'JP']::text[],
    'profile seed contains the six approved names in display order'
);

SELECT is((SELECT count(*) FROM public.player_profiles), 6::bigint,
    'profile seed contains exactly six rows');

SELECT is((SELECT count(DISTINCT id) FROM public.player_profiles), 6::bigint,
    'all seeded profiles have stable distinct UUIDs');

SELECT ok(
    NOT has_table_privilege('authenticated', 'public.player_profiles', 'SELECT')
    AND NOT has_table_privilege('anon', 'public.player_profiles', 'SELECT')
    AND has_table_privilege('authenticated', 'public.draft_discovery_signals', 'SELECT')
    AND NOT has_table_privilege('anon', 'public.draft_discovery_signals', 'SELECT'),
    'table grants expose only the minimal authenticated discovery signal'
);

SELECT ok(
    has_function_privilege('authenticated', 'public.list_player_profiles(uuid)', 'EXECUTE')
    AND NOT has_function_privilege('anon', 'public.list_player_profiles(uuid)', 'EXECUTE')
    AND has_function_privilege('authenticated', 'public.list_joinable_drafts()', 'EXECUTE')
    AND NOT has_function_privilege('anon', 'public.list_joinable_drafts()', 'EXECUTE'),
    'profile and discovery RPC grants are restricted to authenticated users'
);

SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'public'
          AND indexname = 'players_draft_profile_unique'
          AND indexdef LIKE '%WHERE (profile_id IS NOT NULL)%'
    )
    AND EXISTS (
        SELECT 1 FROM pg_publication_tables
        WHERE pubname = 'supabase_realtime'
          AND schemaname = 'public'
          AND tablename = 'draft_discovery_signals'
    ),
    'profile uniqueness and the Realtime discovery publication are installed'
);

SELECT * FROM finish();

ROLLBACK;
