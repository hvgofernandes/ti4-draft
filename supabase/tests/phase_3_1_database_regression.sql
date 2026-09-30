-- Run against the local database only. The transaction always rolls back.
-- Requires at least three local anonymous Auth users created by the JS suite.
BEGIN;

DO $test$
DECLARE
    v_users uuid[];
    v_created jsonb;
    v_draft_id uuid;
    v_host_player_id uuid;
    v_second_player_id uuid := gen_random_uuid();
    v_third_player_id uuid := gen_random_uuid();
    v_base_set_id uuid;
    v_pok_set_id uuid;
    v_inactive_faction_id uuid;
    v_result jsonb;
BEGIN
    IF has_table_privilege('anon', 'public.content_sets', 'SELECT')
       OR has_table_privilege('anon', 'public.factions', 'SELECT')
       OR has_table_privilege('anon', 'public.draft_content_sets', 'SELECT') THEN
        RAISE EXCEPTION 'anon unexpectedly has catalog or config read grants';
    END IF;
    IF NOT has_table_privilege('authenticated', 'public.content_sets', 'SELECT')
       OR NOT has_table_privilege('authenticated', 'public.factions', 'SELECT')
       OR NOT has_table_privilege('authenticated', 'public.draft_content_sets', 'SELECT') THEN
        RAISE EXCEPTION 'authenticated is missing catalog/config read grants';
    END IF;
    IF has_table_privilege('authenticated', 'public.content_sets', 'INSERT')
       OR has_table_privilege('authenticated', 'public.factions', 'UPDATE')
       OR has_table_privilege('authenticated', 'public.draft_content_sets', 'DELETE') THEN
        RAISE EXCEPTION 'authenticated unexpectedly has catalog/config write grants';
    END IF;
    IF has_function_privilege('anon', 'public.set_draft_content_sets(uuid, uuid[])', 'EXECUTE')
       OR has_function_privilege('anon', 'public.make_pick(uuid, uuid)', 'EXECUTE') THEN
        RAISE EXCEPTION 'anon unexpectedly has domain RPC execution grants';
    END IF;
    IF NOT has_function_privilege('authenticated', 'public.set_draft_content_sets(uuid, uuid[])', 'EXECUTE')
       OR NOT has_function_privilege('authenticated', 'public.make_pick(uuid, uuid)', 'EXECUTE') THEN
        RAISE EXCEPTION 'authenticated is missing domain RPC execution grants';
    END IF;

    SELECT array_agg(id ORDER BY created_at) INTO v_users
    FROM (
        SELECT id, created_at FROM auth.users ORDER BY created_at LIMIT 3
    ) AS local_users;
    IF cardinality(v_users) < 3 THEN
        RAISE EXCEPTION 'Requires three local Auth users';
    END IF;

    SELECT id INTO STRICT v_base_set_id
    FROM public.content_sets WHERE slug = 'base';
    SELECT id INTO STRICT v_pok_set_id
    FROM public.content_sets WHERE slug = 'pok';

    PERFORM set_config('request.jwt.claim.sub', v_users[1]::text, true);
    v_created := public.create_draft('Catalog SQL host', 3);
    v_draft_id := (v_created->'draft'->>'id')::uuid;
    v_host_player_id := (v_created->'player'->>'id')::uuid;
    INSERT INTO public.players (id, draft_id, user_id, name, seat, connected)
    VALUES
        (v_second_player_id, v_draft_id, v_users[2], 'Catalog SQL second', NULL, true),
        (v_third_player_id, v_draft_id, v_users[3], 'Catalog SQL third', NULL, true);
    PERFORM public.set_player_order(
        v_draft_id,
        ARRAY[v_host_player_id, v_second_player_id, v_third_player_id]
    );

    -- An inactive content set cannot be selected, even by the host.
    UPDATE public.content_sets SET active = false WHERE id = v_pok_set_id;
    BEGIN
        PERFORM public.set_draft_content_sets(
            v_draft_id, ARRAY[v_base_set_id, v_pok_set_id]
        );
        RAISE EXCEPTION 'Expected inactive content set rejection';
    EXCEPTION WHEN OTHERS THEN
        IF SQLERRM NOT LIKE 'Conjunto de conteúdo inexistente ou inativo%' THEN
            RAISE;
        END IF;
    END;

    -- Base has only two active factions: start must reject 3 players.
    UPDATE public.factions
    SET active = (sort_order <= 2)
    WHERE content_set_id = v_base_set_id;
    BEGIN
        PERFORM public.start_draft(v_draft_id);
        RAISE EXCEPTION 'Expected insufficient faction rejection';
    EXCEPTION WHEN OTHERS THEN
        IF SQLERRM NOT LIKE 'Não há facções suficientes%' THEN
            RAISE;
        END IF;
    END;

    -- Re-enable a third faction; retain a fourth as inactive.
    UPDATE public.factions
    SET active = true
    WHERE content_set_id = v_base_set_id AND sort_order = 3;
    SELECT id INTO STRICT v_inactive_faction_id
    FROM public.factions
    WHERE content_set_id = v_base_set_id AND sort_order = 4;
    v_result := public.start_draft(v_draft_id);
    IF v_result->>'status' <> 'active' THEN
        RAISE EXCEPTION 'Expected active draft after adding third faction';
    END IF;
    BEGIN
        PERFORM public.make_pick(v_draft_id, v_inactive_faction_id);
        RAISE EXCEPTION 'Expected inactive faction rejection';
    EXCEPTION WHEN OTHERS THEN
        IF SQLERRM NOT LIKE 'Facção inativa%' THEN
            RAISE;
        END IF;
    END;

    RAISE NOTICE 'PASS: grants, inactive set, insufficient factions, inactive faction';
END;
$test$;

ROLLBACK;
