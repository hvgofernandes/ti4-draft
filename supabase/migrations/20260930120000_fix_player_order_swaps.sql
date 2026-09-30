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

    -- The transaction keeps this temporary clearing invisible to other sessions.
    -- NULL seats do not conflict under the existing UNIQUE (draft_id, seat) constraint.
    update public.players
    set seat = null
    where draft_id = p_draft_id;

    update public.players as player
    set seat = ordered.position::integer
    from unnest(p_player_ids) with ordinality as ordered(player_id, position)
    where player.draft_id = p_draft_id
      and player.id = ordered.player_id;

    return jsonb_build_object('success', true, 'player_count', v_player_count);
end;
$function$;