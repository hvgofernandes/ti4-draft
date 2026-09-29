SET local check_function_bodies = off;

CREATE TABLE "public"."drafts" (
  "id"               uuid                     NOT NULL DEFAULT gen_random_uuid(),
  "code"             text                     NOT NULL,
  "status"           text                     NOT NULL DEFAULT 'waiting'::text,
  "player_count"     integer                  NOT NULL,
  "picks_per_player" integer                  NOT NULL DEFAULT 1,
  "created_at"       timestamp with time zone NOT NULL DEFAULT now(),
  "host_id"          uuid,
  "current_player"   uuid,
  CONSTRAINT "drafts_code_key" UNIQUE (code),
  CONSTRAINT "drafts_picks_per_player_check" CHECK (((picks_per_player >= 1) AND (picks_per_player <= 3))),
  CONSTRAINT "drafts_pkey" PRIMARY KEY (id),
  CONSTRAINT "drafts_player_count_check" CHECK (((player_count >= 3) AND (player_count <= 6))),
  CONSTRAINT "drafts_status_check" CHECK ((status = ANY (ARRAY['waiting'::text, 'active'::text, 'finished'::text])))
);

ALTER TABLE "public"."drafts"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."picks" (
  "id"         uuid                     NOT NULL DEFAULT gen_random_uuid(),
  "draft_id"   uuid                     NOT NULL,
  "player_id"  uuid                     NOT NULL,
  "faction"    text                     NOT NULL,
  "pick_order" integer                  NOT NULL,
  "created_at" timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT "picks_draft_id_faction_key" UNIQUE (draft_id, faction),
  CONSTRAINT "picks_draft_id_pick_order_key" UNIQUE (draft_id, pick_order),
  CONSTRAINT "picks_pkey" PRIMARY KEY (id)
);

ALTER TABLE "public"."picks"
  ENABLE ROW LEVEL SECURITY;

CREATE TABLE "public"."players" (
  "id"        uuid                     NOT NULL DEFAULT gen_random_uuid(),
  "draft_id"  uuid                     NOT NULL,
  "name"      text                     NOT NULL,
  "seat"      integer,
  "connected" boolean                  NOT NULL DEFAULT true,
  "joined_at" timestamp with time zone NOT NULL DEFAULT now(),
  "user_id"   uuid,
  CONSTRAINT "players_draft_id_seat_key" UNIQUE (draft_id, seat),
  CONSTRAINT "players_name_check" CHECK (((char_length(name) >= 1) AND (char_length(name) <= 20))),
  CONSTRAINT "players_pkey" PRIMARY KEY (id),
  CONSTRAINT "players_seat_check" CHECK (((seat >= 1) AND (seat <= 6)))
);

ALTER TABLE "public"."players"
  ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.create_draft (
  p_player_name  text,
  p_player_count integer
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO 'public'
  AS $function$
declare
    v_user_id uuid;
    v_draft public.drafts;
    v_player public.players;
    v_code text;
begin

    -- Identidade do jogador atual
    v_user_id := (select auth.uid());

    if v_user_id is null then
        raise exception 'Usuário não autenticado';
    end if;


    -- Validar nome
    if p_player_name is null
       or char_length(trim(p_player_name)) < 1
       or char_length(trim(p_player_name)) > 20 then
        raise exception 'Nome inválido';
    end if;


    -- Validar quantidade de jogadores
    if p_player_count not between 3 and 6 then
        raise exception 'A sala deve ter entre 3 e 6 jogadores';
    end if;


    -- Gerar código único
    loop
        v_code := upper(substr(
            md5(random()::text || clock_timestamp()::text),
            1,
            6
        ));

        exit when not exists (
            select 1
            from public.drafts
            where code = v_code
        );
    end loop;


    -- Criar a sala
    insert into public.drafts (
        code,
        status,
        host_id,
        player_count
    )
    values (
        v_code,
        'waiting',
        v_user_id,
        p_player_count
    )
    returning * into v_draft;


    -- Criar o host como primeiro jogador
    insert into public.players (
        draft_id,
        user_id,
        name,
        seat,
        connected
    )
    values (
        v_draft.id,
        v_user_id,
        trim(p_player_name),
        null,
        true
    )
    returning * into v_player;


    -- Retornar informações necessárias ao frontend
    return jsonb_build_object(
        'draft', to_jsonb(v_draft),
        'player', to_jsonb(v_player)
    );

end;
$function$;

CREATE OR REPLACE FUNCTION public.join_draft (
  p_code        text,
  p_player_name text
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SECURITY DEFINER
  SET search_path TO 'public'
  AS $function$
declare
    v_user_id uuid;
    v_draft public.drafts;
    v_player public.players;
    v_player_count integer;
begin

    v_user_id := (select auth.uid());

    if v_user_id is null then
        raise exception 'Usuário não autenticado';
    end if;


    -- Validar nome
    if p_player_name is null
       or char_length(trim(p_player_name)) < 1
       or char_length(trim(p_player_name)) > 20 then
        raise exception 'Nome inválido';
    end if;


    -- Procurar a sala pelo código
    select *
    into v_draft
    from public.drafts
    where code = upper(trim(p_code))
    for update;


    if not found then
        raise exception 'Sala não encontrada';
    end if;


    -- Só é possível entrar enquanto a sala estiver aguardando
    if v_draft.status <> 'waiting' then
        raise exception 'O draft já começou';
    end if;


    -- Verificar se este usuário já está na sala
    if exists (
        select 1
        from public.players
        where draft_id = v_draft.id
          and user_id = v_user_id
    ) then
        raise exception 'Você já está nesta sala';
    end if;


    -- Contar jogadores
    select count(*)
    into v_player_count
    from public.players
    where draft_id = v_draft.id;


    -- Sala cheia
    if v_player_count >= v_draft.player_count then
        raise exception 'A sala está cheia';
    end if;


    -- Adicionar jogador
    insert into public.players (
        draft_id,
        user_id,
        name,
        seat,
        connected
    )
    values (
        v_draft.id,
        v_user_id,
        trim(p_player_name),
        null,
        true
    )
    returning * into v_player;


    return jsonb_build_object(
        'draft', to_jsonb(v_draft),
        'player', to_jsonb(v_player)
    );

end;
$function$;

CREATE OR REPLACE FUNCTION public.make_pick (
  p_draft_id uuid,
  p_faction  text
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SECURITY DEFINER
  SET search_path TO 'public'
  AS $function$
declare
    v_draft public.drafts%rowtype;
    v_player public.players%rowtype;
    v_pick_order integer;
    v_next_player uuid;
    v_total_players integer;
    v_total_picks integer;
begin

    /*
     * 1. Buscar o draft
     */
    select *
    into v_draft
    from public.drafts
    where id = p_draft_id
    for update;

    if not found then
        raise exception 'Draft não encontrado.';
    end if;


    /*
     * 2. O draft precisa estar ativo
     */
    if v_draft.status <> 'active' then
        raise exception 'O draft não está ativo.';
    end if;


    /*
     * 3. Descobrir o jogador autenticado
     */
    select *
    into v_player
    from public.players
    where draft_id = p_draft_id
      and user_id = auth.uid();

    if not found then
        raise exception 'Você não pertence a este draft.';
    end if;


    /*
     * 4. Verificar se é realmente a vez dele
     */
    if v_draft.current_player <> v_player.id then
        raise exception 'Não é a sua vez.';
    end if;


    /*
     * 5. Verificar se a facção já foi escolhida
     */
    if exists (
        select 1
        from public.picks
        where draft_id = p_draft_id
          and faction = p_faction
    ) then
        raise exception 'Esta facção já foi escolhida.';
    end if;


    /*
     * 6. Definir número do pick
     */
    select coalesce(max(pick_order), 0) + 1
    into v_pick_order
    from public.picks
    where draft_id = p_draft_id;


    /*
     * 7. Registrar a escolha
     */
    insert into public.picks (
        draft_id,
        player_id,
        faction,
        pick_order
    )
    values (
        p_draft_id,
        v_player.id,
        p_faction,
        v_pick_order
    );


    /*
     * 8. Quantidade total de jogadores
     */
    select count(*)
    into v_total_players
    from public.players
    where draft_id = p_draft_id;


    /*
     * 9. Encontrar o próximo jogador pela ordem dos seats
     */
    select p.id
    into v_next_player
    from public.players p
    where p.draft_id = p_draft_id
      and p.seat > v_player.seat
    order by p.seat
    limit 1;


    /*
     * 10. Se chegamos ao último jogador,
     * o draft termina.
     */
    if v_next_player is null then

        update public.drafts
        set
            status = 'completed',
            current_player = null
        where id = p_draft_id;

        return jsonb_build_object(
            'success', true,
            'status', 'completed',
            'pick_order', v_pick_order,
            'faction', p_faction,
            'player_id', v_player.id
        );

    end if;


    /*
     * 11. Passar a vez para o próximo jogador
     */
    update public.drafts
    set current_player = v_next_player
    where id = p_draft_id;


    /*
     * 12. Retornar resultado
     */
    return jsonb_build_object(
        'success', true,
        'status', 'active',
        'pick_order', v_pick_order,
        'faction', p_faction,
        'player_id', v_player.id,
        'next_player', v_next_player
    );

end;
$function$;

CREATE OR REPLACE FUNCTION public.set_player_order (
  p_draft_id   uuid,
  p_player_ids uuid[]
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SECURITY DEFINER
  SET search_path TO 'public'
  AS $function$
declare
    v_user_id uuid;
    v_host_id uuid;
    v_player_count integer;
    v_id uuid;
    v_position integer;
begin

    v_user_id := auth.uid();

    if v_user_id is null then
        raise exception 'Usuário não autenticado';
    end if;


    select host_id, player_count
    into v_host_id, v_player_count
    from public.drafts
    where id = p_draft_id;


    if v_host_id is null then
        raise exception 'Sala não encontrada';
    end if;


    if v_host_id <> v_user_id then
        raise exception 'Somente o host pode definir a ordem';
    end if;


    if array_length(p_player_ids, 1) <> v_player_count then
        raise exception
            'A ordem precisa conter todos os jogadores da sala';
    end if;


    if (
        select count(distinct x)
        from unnest(p_player_ids) as x
    ) <> v_player_count then

        raise exception 'Existem jogadores duplicados na ordem';

    end if;


    if (
        select count(*)
        from public.players
        where draft_id = p_draft_id
          and id = any(p_player_ids)
    ) <> v_player_count then

        raise exception
            'A lista contém jogadores que não pertencem a esta sala';

    end if;


    v_position := 1;

    foreach v_id in array p_player_ids
    loop

        update public.players
        set seat = v_position
        where id = v_id
          and draft_id = p_draft_id;

        v_position := v_position + 1;

    end loop;


    return jsonb_build_object(
        'success', true,
        'player_count', v_player_count
    );

end;
$function$;

CREATE OR REPLACE FUNCTION public.start_draft (
  p_draft_id uuid
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SECURITY DEFINER
  SET search_path TO 'public'
  AS $function$
declare
    v_user_id uuid;
    v_host_id uuid;
    v_player_count integer;
    v_status text;
    v_player_total integer;
    v_seated_total integer;
    v_first_player_id uuid;
begin

    -- Usuário autenticado
    v_user_id := auth.uid();

    if v_user_id is null then
        raise exception 'Usuário não autenticado';
    end if;


    -- Buscar informações da sala
    select
        host_id,
        player_count,
        status
    into
        v_host_id,
        v_player_count,
        v_status
    from public.drafts
    where id = p_draft_id;


    if v_host_id is null then
        raise exception 'Sala não encontrada';
    end if;


    -- Somente o host pode iniciar
    if v_host_id <> v_user_id then
        raise exception 'Somente o host pode iniciar o draft';
    end if;


    -- Verificar se já começou
    if v_status = 'active' then
        raise exception 'O draft já foi iniciado';
    end if;


    -- Contar jogadores
    select count(*)
    into v_player_total
    from public.players
    where draft_id = p_draft_id;


    if v_player_total <> v_player_count then
        raise exception
            'É necessário ter todos os jogadores na sala';
    end if;


    -- Verificar se todos possuem posição
    select count(*)
    into v_seated_total
    from public.players
    where draft_id = p_draft_id
      and seat is not null;


    if v_seated_total <> v_player_count then
        raise exception
            'É necessário definir a ordem dos jogadores antes de iniciar';
    end if;


    -- Encontrar o jogador da posição 1
    select id
    into v_first_player_id
    from public.players
    where draft_id = p_draft_id
      and seat = 1
    limit 1;


    if v_first_player_id is null then
        raise exception
            'Não foi possível encontrar o primeiro jogador';
    end if;


    -- Iniciar o draft
    update public.drafts
    set
        status = 'active',
        current_player = v_first_player_id
    where id = p_draft_id;


    return jsonb_build_object(
        'success', true,
        'status', 'active',
        'current_player', v_first_player_id
    );

end;
$function$;

ALTER TABLE "public"."drafts"
  ADD CONSTRAINT "drafts_host_id_fkey" FOREIGN KEY (host_id) REFERENCES auth.users(id);

ALTER TABLE "public"."picks"
  ADD CONSTRAINT "picks_draft_id_fkey" FOREIGN KEY (draft_id) REFERENCES public.drafts(id) ON DELETE CASCADE;

ALTER TABLE "public"."players"
  ADD CONSTRAINT "players_draft_id_fkey" FOREIGN KEY (draft_id) REFERENCES public.drafts(id) ON DELETE CASCADE;

ALTER TABLE "public"."drafts"
  ADD CONSTRAINT "drafts_current_player_fkey" FOREIGN KEY (current_player) REFERENCES public.players(id);

ALTER TABLE "public"."picks"
  ADD CONSTRAINT "picks_player_id_fkey" FOREIGN KEY (player_id) REFERENCES public.players(id) ON DELETE CASCADE;

ALTER TABLE "public"."players"
  ADD CONSTRAINT "players_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id);

CREATE INDEX picks_draft_id_idx ON public.picks USING btree (draft_id);

CREATE INDEX picks_player_id_idx ON public.picks USING btree (player_id);

CREATE INDEX players_draft_id_idx ON public.players USING btree (draft_id);

CREATE UNIQUE INDEX players_draft_user_unique ON public.players USING btree (draft_id, user_id);

CREATE POLICY "authenticated users can create drafts" ON "public"."drafts"
  FOR INSERT
  TO "authenticated"
  WITH CHECK ((( SELECT auth.uid() AS uid) = host_id));

CREATE POLICY "authenticated users can view drafts" ON "public"."drafts"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "authenticated users can view picks" ON "public"."picks"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "authenticated users can view players" ON "public"."players"
  FOR SELECT
  TO "authenticated"
  USING (true);

CREATE POLICY "host can organize player order" ON "public"."players"
  FOR UPDATE
  TO "authenticated"
  USING ((EXISTS ( SELECT 1
   FROM public.drafts d
  WHERE ((d.id = players.draft_id) AND (d.host_id = ( SELECT auth.uid() AS uid)) AND (d.status = 'waiting'::text)))))
  WITH CHECK ((EXISTS ( SELECT 1
   FROM public.drafts d
  WHERE ((d.id = players.draft_id) AND (d.host_id = ( SELECT auth.uid() AS uid)) AND (d.status = 'waiting'::text)))));

CREATE POLICY "users can join drafts" ON "public"."players"
  FOR INSERT
  TO "authenticated"
  WITH CHECK ((( SELECT auth.uid() AS uid) = user_id));

ALTER PUBLICATION "supabase_realtime" ADD TABLE "public"."drafts";

ALTER PUBLICATION "supabase_realtime" ADD TABLE "public"."players";

GRANT EXECUTE ON FUNCTION "public"."create_draft"(text, integer) TO PUBLIC, "anon", "authenticated", "postgres", "service_role";

GRANT EXECUTE ON FUNCTION "public"."join_draft"(text, text) TO PUBLIC, "anon", "authenticated", "postgres", "service_role";

GRANT EXECUTE ON FUNCTION "public"."make_pick"(uuid, text) TO PUBLIC, "anon", "authenticated", "postgres", "service_role";

GRANT EXECUTE ON FUNCTION "public"."set_player_order"(uuid, uuid[]) TO PUBLIC, "anon", "authenticated", "postgres", "service_role";

GRANT EXECUTE ON FUNCTION "public"."start_draft"(uuid) TO PUBLIC, "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."drafts" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."picks" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."players" TO "anon", "authenticated", "postgres", "service_role";

