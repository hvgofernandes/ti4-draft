DO $test$
DECLARE
    v_host_id uuid;
    v_auth_user_ids uuid[];
    v_second_user_id uuid;
    v_third_user_id uuid;
    v_result jsonb;
    v_draft_id uuid;
    v_host_player_id uuid;
    v_second_player_id uuid := gen_random_uuid();
    v_third_player_id uuid := gen_random_uuid();
    v_initial_order uuid[];
    v_final_order uuid[];
BEGIN
    SELECT array_agg(id ORDER BY created_at)
    INTO v_auth_user_ids
    FROM (
        SELECT id, created_at
        FROM auth.users
        ORDER BY created_at
        LIMIT 3
    ) AS existing_users;
    IF coalesce(array_length(v_auth_user_ids, 1), 0) < 3 THEN
        RAISE EXCEPTION 'The regression test requires three existing local auth users';
    END IF;
    v_host_id := v_auth_user_ids[1];
    v_second_user_id := v_auth_user_ids[2];
    v_third_user_id := v_auth_user_ids[3];

    PERFORM set_config('request.jwt.claim.sub', v_host_id::text, true);

    v_result := public.create_draft('Order swap host', 3);
    v_draft_id := (v_result->'draft'->>'id')::uuid;
    v_host_player_id := (v_result->'player'->>'id')::uuid;

    INSERT INTO public.players (id, draft_id, user_id, name, seat, connected)
    VALUES
        (v_second_player_id, v_draft_id, v_second_user_id, 'Order swap two', NULL, true),
        (v_third_player_id, v_draft_id, v_third_user_id, 'Order swap three', NULL, true);

    PERFORM public.set_player_order(
        v_draft_id,
        ARRAY[v_host_player_id, v_second_player_id, v_third_player_id]
    );

    SELECT array_agg(id ORDER BY seat)
    INTO v_initial_order
    FROM public.players
    WHERE draft_id = v_draft_id;

    IF v_initial_order IS DISTINCT FROM ARRAY[v_host_player_id, v_second_player_id, v_third_player_id] THEN
        RAISE EXCEPTION 'Initial seat assignment failed: order %', v_initial_order;
    END IF;

    PERFORM public.set_player_order(
        v_draft_id,
        ARRAY[v_second_player_id, v_host_player_id, v_third_player_id]
    );

    SELECT array_agg(id ORDER BY seat)
    INTO v_final_order
    FROM public.players
    WHERE draft_id = v_draft_id;

    IF v_final_order IS DISTINCT FROM ARRAY[v_second_player_id, v_host_player_id, v_third_player_id] THEN
        RAISE EXCEPTION 'Seat swap regression failed: final order %', v_final_order;
    END IF;

    DELETE FROM public.players WHERE draft_id = v_draft_id;
    DELETE FROM public.drafts WHERE id = v_draft_id;
END;
$test$;
