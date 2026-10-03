-- Phase 3.3: persistent player identities and safe waiting-room discovery.

CREATE TABLE public.player_profiles (
    id uuid PRIMARY KEY,
    name text NOT NULL CHECK (char_length(trim(name)) BETWEEN 1 AND 20),
    sort_order integer NOT NULL UNIQUE CHECK (sort_order > 0),
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT player_profiles_name_key UNIQUE (name)
);

ALTER TABLE public.player_profiles ENABLE ROW LEVEL SECURITY;

INSERT INTO public.player_profiles (id, name, sort_order) VALUES
    ('a1000000-0000-4000-8000-000000000001', 'Gus', 1),
    ('a1000000-0000-4000-8000-000000000002', 'Lucca', 2),
    ('a1000000-0000-4000-8000-000000000003', 'Arthur', 3),
    ('a1000000-0000-4000-8000-000000000004', 'Lustosa', 4),
    ('a1000000-0000-4000-8000-000000000005', 'Phinha', 5),
    ('a1000000-0000-4000-8000-000000000006', 'JP', 6);

ALTER TABLE public.players
    ADD COLUMN profile_id uuid REFERENCES public.player_profiles(id);
CREATE UNIQUE INDEX players_draft_profile_unique
    ON public.players (draft_id, profile_id)
    WHERE profile_id IS NOT NULL;
CREATE INDEX players_profile_id_idx
    ON public.players (profile_id)
    WHERE profile_id IS NOT NULL;

COMMENT ON COLUMN public.players.profile_id IS
    'Persistent player identity. Nullable only for drafts created before Phase 3.3 and legacy name-based RPC calls.';

-- A deliberately small Realtime surface. Events tell clients to refresh the
-- SECURITY DEFINER discovery RPC; they do not expose draft or player data.
CREATE TABLE public.draft_discovery_signals (
    draft_id uuid PRIMARY KEY REFERENCES public.drafts(id) ON DELETE CASCADE,
    revision bigint NOT NULL DEFAULT 1 CHECK (revision > 0),
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.draft_discovery_signals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "authenticated can receive discovery signals"
    ON public.draft_discovery_signals
    FOR SELECT TO authenticated
    USING (true);

REVOKE ALL PRIVILEGES ON TABLE public.player_profiles,
    public.draft_discovery_signals FROM PUBLIC, anon, authenticated;
GRANT SELECT ON TABLE public.draft_discovery_signals TO authenticated;

CREATE FUNCTION public.touch_draft_discovery_signal()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_draft_id uuid;
BEGIN
    IF TG_TABLE_NAME = 'drafts' THEN
        v_draft_id := NEW.id;
    ELSE
        v_draft_id := NEW.draft_id;
    END IF;
    INSERT INTO public.draft_discovery_signals (draft_id)
    VALUES (v_draft_id)
    ON CONFLICT (draft_id) DO UPDATE
    SET revision = public.draft_discovery_signals.revision + 1,
        updated_at = now();
    RETURN NEW;
END;
$function$;

CREATE TRIGGER drafts_touch_discovery
AFTER INSERT OR UPDATE OF status, player_count ON public.drafts
FOR EACH ROW EXECUTE FUNCTION public.touch_draft_discovery_signal();

CREATE TRIGGER players_touch_discovery
AFTER INSERT OR UPDATE OF profile_id, draft_id ON public.players
FOR EACH ROW EXECUTE FUNCTION public.touch_draft_discovery_signal();

CREATE FUNCTION public.delete_player_discovery_signal()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    IF EXISTS (SELECT 1 FROM public.drafts WHERE id = OLD.draft_id) THEN
        INSERT INTO public.draft_discovery_signals (draft_id)
        VALUES (OLD.draft_id)
        ON CONFLICT (draft_id) DO UPDATE
        SET revision = public.draft_discovery_signals.revision + 1,
            updated_at = now();
    END IF;
    RETURN OLD;
END;
$function$;

CREATE TRIGGER players_delete_touch_discovery
AFTER DELETE ON public.players
FOR EACH ROW EXECUTE FUNCTION public.delete_player_discovery_signal();

CREATE FUNCTION public.list_player_profiles(p_draft_id uuid DEFAULT NULL)
RETURNS TABLE (
    id uuid,
    name text,
    sort_order integer,
    unavailable boolean
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'Usuário não autenticado';
    END IF;
    IF p_draft_id IS NOT NULL AND NOT EXISTS (
        SELECT 1
        FROM public.drafts draft
        WHERE draft.id = p_draft_id
          AND draft.status = 'waiting'
          AND (SELECT count(*) FROM public.players player
               WHERE player.draft_id = draft.id) < draft.player_count
    ) THEN
        RAISE EXCEPTION 'Sala indisponível';
    END IF;
    RETURN QUERY
    SELECT profile.id, profile.name, profile.sort_order,
           CASE WHEN p_draft_id IS NULL THEN false ELSE EXISTS (
               SELECT 1 FROM public.players player
               WHERE player.draft_id = p_draft_id
                 AND player.profile_id = profile.id
           ) END
    FROM public.player_profiles profile
    WHERE profile.active
    ORDER BY profile.sort_order;
END;
$function$;

CREATE FUNCTION public.list_joinable_drafts()
RETURNS TABLE (
    draft_id uuid,
    room_code text,
    host_profile_id uuid,
    host_name text,
    player_count integer,
    capacity integer,
    used_profile_ids uuid[]
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
BEGIN
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'Usuário não autenticado';
    END IF;
    RETURN QUERY
    SELECT draft.id,
           draft.code,
           host_player.profile_id,
           coalesce(host_profile.name, host_player.name),
           count(player.id)::integer,
           draft.player_count,
           coalesce(
               array_agg(player.profile_id ORDER BY profile.sort_order)
                   FILTER (WHERE player.profile_id IS NOT NULL),
               ARRAY[]::uuid[]
           )
    FROM public.drafts draft
    JOIN public.players host_player
      ON host_player.draft_id = draft.id
     AND host_player.user_id = draft.host_id
    LEFT JOIN public.player_profiles host_profile ON host_profile.id = host_player.profile_id
    LEFT JOIN public.players player ON player.draft_id = draft.id
    LEFT JOIN public.player_profiles profile ON profile.id = player.profile_id
    WHERE draft.status = 'waiting'
    GROUP BY draft.id, draft.code, draft.player_count,
             host_player.profile_id, host_profile.name, host_player.name,
             draft.created_at
    HAVING count(player.id) < draft.player_count
    ORDER BY draft.created_at;
END;
$function$;

CREATE FUNCTION public.create_draft(
    p_profile_id uuid,
    p_player_count integer
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_user_id uuid := auth.uid();
    v_profile public.player_profiles%rowtype;
    v_draft public.drafts%rowtype;
    v_player public.players%rowtype;
    v_code text;
    v_base_set_id uuid;
BEGIN
    IF v_user_id IS NULL THEN RAISE EXCEPTION 'Usuário não autenticado'; END IF;
    SELECT * INTO v_profile FROM public.player_profiles
    WHERE id = p_profile_id AND active;
    IF NOT FOUND THEN RAISE EXCEPTION 'Perfil inexistente ou inativo'; END IF;
    IF p_player_count NOT BETWEEN 3 AND 6 THEN
        RAISE EXCEPTION 'A sala deve ter entre 3 e 6 jogadores';
    END IF;
    SELECT id INTO v_base_set_id FROM public.content_sets
    WHERE slug = 'base' AND active;
    IF v_base_set_id IS NULL THEN RAISE EXCEPTION 'Catálogo Base Game indisponível'; END IF;

    LOOP
        v_code := upper(substr(md5(random()::text || clock_timestamp()::text), 1, 6));
        EXIT WHEN NOT EXISTS (SELECT 1 FROM public.drafts WHERE code = v_code);
    END LOOP;
    INSERT INTO public.drafts (code, status, host_id, player_count)
    VALUES (v_code, 'waiting', v_user_id, p_player_count)
    RETURNING * INTO v_draft;
    INSERT INTO public.players (draft_id, user_id, profile_id, name, seat, connected)
    VALUES (v_draft.id, v_user_id, v_profile.id, v_profile.name, NULL, true)
    RETURNING * INTO v_player;
    INSERT INTO public.draft_content_sets (draft_id, content_set_id)
    VALUES (v_draft.id, v_base_set_id);
    RETURN jsonb_build_object('draft', to_jsonb(v_draft), 'player', to_jsonb(v_player));
END;
$function$;

CREATE FUNCTION public.join_draft(
    p_code text,
    p_profile_id uuid
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_draft_id uuid;
    v_result jsonb;
BEGIN
    IF auth.uid() IS NULL THEN RAISE EXCEPTION 'Usuário não autenticado'; END IF;
    SELECT id INTO v_draft_id FROM public.drafts
    WHERE code = upper(trim(p_code));
    IF NOT FOUND THEN RAISE EXCEPTION 'Sala não encontrada'; END IF;
    -- Dynamic invocation keeps this room-code compatibility wrapper independent
    -- from declaration order while still delegating all join rules atomically.
    EXECUTE 'SELECT public.join_draft($1, $2)'
    INTO v_result
    USING v_draft_id, p_profile_id;
    RETURN v_result;
END;
$function$;

CREATE FUNCTION public.join_draft(
    p_draft_id uuid,
    p_profile_id uuid
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_user_id uuid := auth.uid();
    v_profile public.player_profiles%rowtype;
    v_draft public.drafts%rowtype;
    v_player public.players%rowtype;
    v_player_count integer;
BEGIN
    IF v_user_id IS NULL THEN RAISE EXCEPTION 'Usuário não autenticado'; END IF;
    SELECT * INTO v_profile FROM public.player_profiles
    WHERE id = p_profile_id AND active;
    IF NOT FOUND THEN RAISE EXCEPTION 'Perfil inexistente ou inativo'; END IF;

    SELECT * INTO v_draft FROM public.drafts
    WHERE id = p_draft_id FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Sala não encontrada'; END IF;
    IF v_draft.status <> 'waiting' THEN RAISE EXCEPTION 'O draft já começou'; END IF;
    IF EXISTS (SELECT 1 FROM public.players
               WHERE draft_id = v_draft.id AND user_id = v_user_id) THEN
        RAISE EXCEPTION 'Você já está nesta sala';
    END IF;
    IF EXISTS (SELECT 1 FROM public.players
               WHERE draft_id = v_draft.id AND profile_id = v_profile.id) THEN
        RAISE EXCEPTION 'Este perfil já está nesta sala';
    END IF;
    SELECT count(*) INTO v_player_count FROM public.players
    WHERE draft_id = v_draft.id;
    IF v_player_count >= v_draft.player_count THEN RAISE EXCEPTION 'A sala está cheia'; END IF;

    INSERT INTO public.players (draft_id, user_id, profile_id, name, seat, connected)
    VALUES (v_draft.id, v_user_id, v_profile.id, v_profile.name, NULL, true)
    RETURNING * INTO v_player;
    RETURN jsonb_build_object('draft', to_jsonb(v_draft), 'player', to_jsonb(v_player));
END;
$function$;

REVOKE ALL ON FUNCTION public.touch_draft_discovery_signal() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.delete_player_discovery_signal() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.list_player_profiles(uuid) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.list_joinable_drafts() FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.create_draft(uuid, integer) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.join_draft(text, uuid) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.join_draft(uuid, uuid) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.list_player_profiles(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.list_joinable_drafts() TO authenticated;
GRANT EXECUTE ON FUNCTION public.create_draft(uuid, integer) TO authenticated;
GRANT EXECUTE ON FUNCTION public.join_draft(text, uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.join_draft(uuid, uuid) TO authenticated;

DO $publication$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables
        WHERE pubname = 'supabase_realtime'
          AND schemaname = 'public'
          AND tablename = 'draft_discovery_signals'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.draft_discovery_signals;
    END IF;
END;
$publication$;
