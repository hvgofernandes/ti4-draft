-- Stabilize the V1 draft rules and limit table access to the RPC contract.

CREATE OR REPLACE FUNCTION public.create_draft (
  p_player_name text,
  p_player_count integer
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
declare
    v_user_id uuid;
    v_draft public.drafts;
    v_player public.players;
    v_code text;
begin
    v_user_id := auth.uid();

    if v_user_id is null then
        raise exception 'Usuário não autenticado';
    end if;

    if p_player_name is null
       or char_length(trim(p_player_name)) < 1
       or char_length(trim(p_player_name)) > 20 then
        raise exception 'Nome inválido';
    end if;

    if p_player_count not between 3 and 6 then
        raise exception 'A sala deve ter entre 3 e 6 jogadores';
    end if;

    loop
        v_code := upper(substr(
            md5(random()::text || clock_timestamp()::text),
            1,
            6
        ));
        exit when not exists (
            select 1 from public.drafts where code = v_code
        );
    end loop;

    insert into public.drafts (code, status, host_id, player_count)
    values (v_code, 'waiting', v_user_id, p_player_count)
    returning * into v_draft;

    insert into public.players (draft_id, user_id, name, seat, connected)
    values (v_draft.id, v_user_id, trim(p_player_name), null, true)
    returning * into v_player;

    return jsonb_build_object(
        'draft', to_jsonb(v_draft),
        'player', to_jsonb(v_player)
    );
end;
$function$;

CREATE OR REPLACE FUNCTION public.join_draft (
  p_code text,
  p_player_name text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
declare
    v_user_id uuid;
    v_draft public.drafts;
    v_player public.players;
    v_player_count integer;
begin
    v_user_id := auth.uid();
    if v_user_id is null then
        raise exception 'Usuário não autenticado';
    end if;

    if p_player_name is null
       or char_length(trim(p_player_name)) < 1
       or char_length(trim(p_player_name)) > 20 then
        raise exception 'Nome inválido';
    end if;

    select * into v_draft
    from public.drafts
    where code = upper(trim(p_code))
    for update;

    if not found then
        raise exception 'Sala não encontrada';
    end if;
    if v_draft.status <> 'waiting' then
        raise exception 'O draft já começou';
    end if;
    if exists (
        select 1 from public.players
        where draft_id = v_draft.id and user_id = v_user_id
    ) then
        raise exception 'Você já está nesta sala';
    end if;

    select count(*) into v_player_count
    from public.players where draft_id = v_draft.id;
    if v_player_count >= v_draft.player_count then
        raise exception 'A sala está cheia';
    end if;

    insert into public.players (draft_id, user_id, name, seat, connected)
    values (v_draft.id, v_user_id, trim(p_player_name), null, true)
    returning * into v_player;

    return jsonb_build_object(
        'draft', to_jsonb(v_draft),
        'player', to_jsonb(v_player)
    );
end;
$function$;

CREATE OR REPLACE FUNCTION public.set_player_order (
  p_draft_id uuid,
  p_player_ids uuid[]
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
declare
    v_user_id uuid;
    v_host_id uuid;
    v_player_count integer;
    v_status text;
    v_id uuid;
    v_position integer;
begin
    v_user_id := auth.uid();
    if v_user_id is null then
        raise exception 'Usuário não autenticado';
    end if;

    select host_id, player_count, status
    into v_host_id, v_player_count, v_status
    from public.drafts
    where id = p_draft_id
    for update;

    if not found then
        raise exception 'Sala não encontrada';
    end if;
    if v_host_id is distinct from v_user_id then
        raise exception 'Somente o host pode definir a ordem';
    end if;
    if v_status <> 'waiting' then
        raise exception 'A ordem só pode ser definida enquanto a sala aguarda jogadores';
    end if;
    if coalesce(array_length(p_player_ids, 1), 0) <> v_player_count then
        raise exception 'A ordem precisa conter todos os jogadores da sala';
    end if;
    if (
        select count(distinct x) from unnest(p_player_ids) as x
    ) <> v_player_count then
        raise exception 'Existem jogadores duplicados na ordem';
    end if;
    if (
        select count(*) from public.players
        where draft_id = p_draft_id and id = any(p_player_ids)
    ) <> v_player_count then
        raise exception 'A lista contém jogadores que não pertencem a esta sala';
    end if;

    v_position := 1;
    foreach v_id in array p_player_ids loop
        update public.players
        set seat = v_position
        where id = v_id and draft_id = p_draft_id;
        v_position := v_position + 1;
    end loop;

    return jsonb_build_object('success', true, 'player_count', v_player_count);
end;
$function$;

CREATE OR REPLACE FUNCTION public.start_draft (p_draft_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
declare
    v_user_id uuid;
    v_host_id uuid;
    v_player_count integer;
    v_status text;
    v_player_total integer;
    v_seated_total integer;
    v_min_seat integer;
    v_max_seat integer;
    v_first_player_id uuid;
begin
    v_user_id := auth.uid();
    if v_user_id is null then
        raise exception 'Usuário não autenticado';
    end if;

    select host_id, player_count, status
    into v_host_id, v_player_count, v_status
    from public.drafts
    where id = p_draft_id
    for update;

    if not found then
        raise exception 'Sala não encontrada';
    end if;
    if v_host_id is distinct from v_user_id then
        raise exception 'Somente o host pode iniciar o draft';
    end if;
    if v_status <> 'waiting' then
        raise exception 'Somente uma sala aguardando pode ser iniciada';
    end if;

    select count(*), count(seat), min(seat), max(seat)
    into v_player_total, v_seated_total, v_min_seat, v_max_seat
    from public.players
    where draft_id = p_draft_id;

    if v_player_total <> v_player_count then
        raise exception 'É necessário ter todos os jogadores na sala';
    end if;
    if v_seated_total <> v_player_count
       or v_min_seat <> 1
       or v_max_seat <> v_player_count then
        raise exception 'É necessário definir a ordem completa dos jogadores antes de iniciar';
    end if;

    select id into v_first_player_id
    from public.players
    where draft_id = p_draft_id and seat = 1;
    if v_first_player_id is null then
        raise exception 'Não foi possível encontrar o primeiro jogador';
    end if;

    update public.drafts
    set status = 'active', current_player = v_first_player_id
    where id = p_draft_id;

    return jsonb_build_object(
        'success', true,
        'status', 'active',
        'current_player', v_first_player_id
    );
end;
$function$;

CREATE OR REPLACE FUNCTION public.make_pick (
  p_draft_id uuid,
  p_faction text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
declare
    v_draft public.drafts%rowtype;
    v_player public.players%rowtype;
    v_pick_order integer;
    v_next_player uuid;
begin
    select * into v_draft
    from public.drafts
    where id = p_draft_id
    for update;

    if not found then
        raise exception 'Draft não encontrado.';
    end if;
    if v_draft.status <> 'active' then
        raise exception 'O draft não está ativo.';
    end if;
    if p_faction is null or char_length(trim(p_faction)) = 0 then
        raise exception 'Facção inválida.';
    end if;

    select * into v_player
    from public.players
    where draft_id = p_draft_id and user_id = auth.uid();

    if not found then
        raise exception 'Você não pertence a este draft.';
    end if;
    if v_draft.current_player is distinct from v_player.id then
        raise exception 'Não é a sua vez.';
    end if;
    if exists (
        select 1 from public.picks
        where draft_id = p_draft_id
          and lower(trim(faction)) = lower(trim(p_faction))
    ) then
        raise exception 'Esta facção já foi escolhida.';
    end if;
    if exists (
        select 1 from public.picks where player_id = v_player.id
    ) then
        raise exception 'Você já escolheu uma facção.';
    end if;

    select coalesce(max(pick_order), 0) + 1
    into v_pick_order
    from public.picks
    where draft_id = p_draft_id;

    insert into public.picks (draft_id, player_id, faction, pick_order)
    values (p_draft_id, v_player.id, trim(p_faction), v_pick_order);

    select id into v_next_player
    from public.players
    where draft_id = p_draft_id and seat > v_player.seat
    order by seat
    limit 1;

    if v_next_player is null then
        update public.drafts
        set status = 'finished', current_player = null
        where id = p_draft_id;

        return jsonb_build_object(
            'success', true,
            'status', 'finished',
            'pick_order', v_pick_order,
            'faction', trim(p_faction),
            'player_id', v_player.id
        );
    end if;

    update public.drafts
    set current_player = v_next_player
    where id = p_draft_id;

    return jsonb_build_object(
        'success', true,
        'status', 'active',
        'pick_order', v_pick_order,
        'faction', trim(p_faction),
        'player_id', v_player.id,
        'next_player', v_next_player
    );
end;
$function$;

COMMENT ON COLUMN public.drafts.picks_per_player IS
  'Retained for compatibility; V1 enforces exactly one pick per player.';

-- SECURITY DEFINER is required for create_draft after client DML is revoked.
-- All RPC implementations validate auth.uid() and their own domain rules.
REVOKE ALL ON FUNCTION public.create_draft(text, integer) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.join_draft(text, text) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.set_player_order(uuid, uuid[]) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.start_draft(uuid) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.make_pick(uuid, text) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.create_draft(text, integer) TO authenticated;
GRANT EXECUTE ON FUNCTION public.join_draft(text, text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.set_player_order(uuid, uuid[]) TO authenticated;
GRANT EXECUTE ON FUNCTION public.start_draft(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.make_pick(uuid, text) TO authenticated;

-- Clients read only; writes go through the RPCs above.
REVOKE ALL PRIVILEGES ON TABLE public.drafts, public.players, public.picks
  FROM anon, authenticated;
GRANT SELECT ON TABLE public.drafts, public.players, public.picks TO authenticated;

DROP POLICY IF EXISTS "authenticated users can create drafts" ON public.drafts;
DROP POLICY IF EXISTS "authenticated users can view drafts" ON public.drafts;
DROP POLICY IF EXISTS "authenticated users can view players" ON public.players;
DROP POLICY IF EXISTS "authenticated users can view picks" ON public.picks;
DROP POLICY IF EXISTS "host can organize player order" ON public.players;
DROP POLICY IF EXISTS "users can join drafts" ON public.players;

CREATE OR REPLACE FUNCTION public.is_draft_participant(p_draft_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
    SELECT EXISTS (
        SELECT 1
        FROM public.players p
        WHERE p.draft_id = p_draft_id
          AND p.user_id = (SELECT auth.uid())
    );
$function$;

REVOKE ALL ON FUNCTION public.is_draft_participant(uuid) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.is_draft_participant(uuid) TO authenticated;

CREATE POLICY "participants can view drafts" ON public.drafts
  FOR SELECT TO authenticated
  USING (public.is_draft_participant(id));
CREATE POLICY "participants can view players" ON public.players
  FOR SELECT TO authenticated
  USING (public.is_draft_participant(draft_id));
CREATE POLICY "participants can view picks" ON public.picks
  FOR SELECT TO authenticated
  USING (public.is_draft_participant(draft_id));

-- Keep existing room/player feeds and add picks for the V1 pick UI.
DO $publication$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables
        WHERE pubname = 'supabase_realtime'
          AND schemaname = 'public'
          AND tablename = 'picks'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.picks;
    END IF;
END;
$publication$;