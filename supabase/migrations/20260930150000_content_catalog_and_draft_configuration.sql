-- Phase 3.1: catalog, per-draft content selection, and faction-backed picks.
-- Keep this migration after the uncommitted Phase 2.5 seat-swap migration.

CREATE TABLE public.content_sets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (char_length(trim(name)) > 0),
    slug text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
    active boolean NOT NULL DEFAULT true,
    sort_order integer NOT NULL CHECK (sort_order >= 0)
);

CREATE TABLE public.factions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    content_set_id uuid NOT NULL REFERENCES public.content_sets(id),
    name text NOT NULL CHECK (char_length(trim(name)) > 0),
    slug text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
    active boolean NOT NULL DEFAULT true,
    sort_order integer NOT NULL CHECK (sort_order >= 0),
    CONSTRAINT factions_set_name_key UNIQUE (content_set_id, name),
    CONSTRAINT factions_set_sort_order_key UNIQUE (content_set_id, sort_order)
);
CREATE INDEX factions_content_set_id_idx ON public.factions (content_set_id);

CREATE TABLE public.draft_content_sets (
    draft_id uuid NOT NULL REFERENCES public.drafts(id) ON DELETE CASCADE,
    content_set_id uuid NOT NULL REFERENCES public.content_sets(id),
    PRIMARY KEY (draft_id, content_set_id)
);
CREATE INDEX draft_content_sets_content_set_id_idx
    ON public.draft_content_sets (content_set_id);

-- The existing drafts publication is the private, RLS-checked notification
-- channel for config changes. Clients reload draft_content_sets on this version.
ALTER TABLE public.drafts
    ADD COLUMN content_version integer NOT NULL DEFAULT 0
    CHECK (content_version >= 0);

-- Retain the old faction text for historical local picks and compatibility.
-- The RPC inserts canonical catalog names, and all new picks require an ID.
ALTER TABLE public.picks
    ADD COLUMN faction_id uuid REFERENCES public.factions(id);
CREATE UNIQUE INDEX picks_draft_id_faction_id_key
    ON public.picks (draft_id, faction_id);
ALTER TABLE public.picks
    ADD CONSTRAINT picks_faction_id_required CHECK (faction_id IS NOT NULL) NOT VALID;

ALTER TABLE public.content_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.factions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.draft_content_sets ENABLE ROW LEVEL SECURITY;

-- The catalog is public to authenticated users; draft selections are private.
CREATE POLICY "authenticated can view content sets" ON public.content_sets
    FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated can view factions" ON public.factions
    FOR SELECT TO authenticated USING (true);
CREATE POLICY "participants can view draft content sets" ON public.draft_content_sets
    FOR SELECT TO authenticated
    USING (public.is_draft_participant(draft_id));

REVOKE ALL PRIVILEGES ON TABLE
    public.content_sets, public.factions, public.draft_content_sets
    FROM PUBLIC, anon, authenticated;
GRANT SELECT ON TABLE public.content_sets, public.factions,
    public.draft_content_sets TO authenticated;

INSERT INTO public.content_sets (name, slug, active, sort_order) VALUES
    ('Base Game', 'base', true, 1),
    ('Prophecy of Kings', 'pok', true, 2),
    ('Thunder''s Edge', 'thunders-edge', true, 3),
    ('Discordant Stars', 'discordant-stars', true, 4);

-- The catalog lists only draftable faction identities. Firmament/Obsidian is
-- one choice because its transformation happens during play; Council Keleres
-- is grouped with Thunder's Edge for this application's configuration.
WITH catalog(content_set_slug, name, slug, sort_order) AS (VALUES
    ('base', 'The Arborec', 'the-arborec', 1),
    ('base', 'The Barony of Letnev', 'the-barony-of-letnev', 2),
    ('base', 'The Clan of Saar', 'the-clan-of-saar', 3),
    ('base', 'The Embers of Muaat', 'the-embers-of-muaat', 4),
    ('base', 'The Emirates of Hacan', 'the-emirates-of-hacan', 5),
    ('base', 'The Federation of Sol', 'the-federation-of-sol', 6),
    ('base', 'The Ghosts of Creuss', 'the-ghosts-of-creuss', 7),
    ('base', 'The L1Z1X Mindnet', 'the-l1z1x-mindnet', 8),
    ('base', 'The Mentak Coalition', 'the-mentak-coalition', 9),
    ('base', 'The Naalu Collective', 'the-naalu-collective', 10),
    ('base', 'The Nekro Virus', 'the-nekro-virus', 11),
    ('base', 'Sardakk N''orr', 'sardakk-norr', 12),
    ('base', 'The Universities of Jol-Nar', 'the-universities-of-jol-nar', 13),
    ('base', 'The Winnu', 'the-winnu', 14),
    ('base', 'The Xxcha Kingdom', 'the-xxcha-kingdom', 15),
    ('base', 'The Yin Brotherhood', 'the-yin-brotherhood', 16),
    ('base', 'The Yssaril Tribes', 'the-yssaril-tribes', 17),
    ('pok', 'The Argent Flight', 'the-argent-flight', 1),
    ('pok', 'The Empyrean', 'the-empyrean', 2),
    ('pok', 'The Mahact Gene-Sorcerers', 'the-mahact-gene-sorcerers', 3),
    ('pok', 'The Naaz-Rokha Alliance', 'the-naaz-rokha-alliance', 4),
    ('pok', 'The Nomad', 'the-nomad', 5),
    ('pok', 'The Titans of Ul', 'the-titans-of-ul', 6),
    ('pok', 'The Vuil''Raith Cabal', 'the-vuilraith-cabal', 7),
    ('thunders-edge', 'Last Bastion', 'last-bastion', 1),
    ('thunders-edge', 'The Deepwrought Scholarate', 'the-deepwrought-scholarate', 2),
    ('thunders-edge', 'The Crimson Rebellion', 'the-crimson-rebellion', 3),
    ('thunders-edge', 'The Ral Nel Consortium', 'the-ral-nel-consortium', 4),
    ('thunders-edge', 'The Firmament / The Obsidian', 'the-firmament-the-obsidian', 5),
    ('thunders-edge', 'The Council Keleres', 'the-council-keleres', 6),
    ('discordant-stars', 'The Shipwrights of Axis', 'the-shipwrights-of-axis', 1),
    ('discordant-stars', 'The Celdauri Trade Confederation', 'the-celdauri-trade-confederation', 2),
    ('discordant-stars', 'The Savages of Cymiae', 'the-savages-of-cymiae', 3),
    ('discordant-stars', 'The Dih-Mohn Flotilla', 'the-dih-mohn-flotilla', 4),
    ('discordant-stars', 'The Florzen Profiteers', 'the-florzen-profiteers', 5),
    ('discordant-stars', 'The Free Systems Compact', 'the-free-systems-compact', 6),
    ('discordant-stars', 'The Ghemina Raiders', 'the-ghemina-raiders', 7),
    ('discordant-stars', 'The Augurs of Ilyxum', 'the-augurs-of-ilyxum', 8),
    ('discordant-stars', 'The Kollecc Society', 'the-kollecc-society', 9),
    ('discordant-stars', 'The Kortali Tribunal', 'the-kortali-tribunal', 10),
    ('discordant-stars', 'The Li-Zho Dynasty', 'the-li-zho-dynasty', 11),
    ('discordant-stars', 'The L''tokk Khrask', 'the-ltokk-khrask', 12),
    ('discordant-stars', 'The Mirveda Protectorate', 'the-mirveda-protectorate', 13),
    ('discordant-stars', 'The Glimmer of Mortheus', 'the-glimmer-of-mortheus', 14),
    ('discordant-stars', 'The Myko-Mentori', 'the-myko-mentori', 15),
    ('discordant-stars', 'The Nivyn Star Kings', 'the-nivyn-star-kings', 16),
    ('discordant-stars', 'The Olradin League', 'the-olradin-league', 17),
    ('discordant-stars', 'The Zealots of Rhodun', 'the-zealots-of-rhodun', 18),
    ('discordant-stars', 'Roh''Dhna Mechatronics', 'rohdhna-mechatronics', 19),
    ('discordant-stars', 'The Tnelis Syndicate', 'the-tnelis-syndicate', 20),
    ('discordant-stars', 'The Vaden Banking Clans', 'the-vaden-banking-clans', 21),
    ('discordant-stars', 'The Vaylerian Scourge', 'the-vaylerian-scourge', 22),
    ('discordant-stars', 'The Veldyr Sovereignty', 'the-veldyr-sovereignty', 23),
    ('discordant-stars', 'The Zelian Purifier', 'the-zelian-purifier', 24),
    ('discordant-stars', 'The Bentor Conglomerate', 'the-bentor-conglomerate', 25),
    ('discordant-stars', 'The Cheiran Hordes', 'the-cheiran-hordes', 26),
    ('discordant-stars', 'The Edyn Mandate', 'the-edyn-mandate', 27),
    ('discordant-stars', 'The Ghoti Wayfarers', 'the-ghoti-wayfarers', 28),
    ('discordant-stars', 'The GLEdge Union', 'the-gledge-union', 29),
    ('discordant-stars', 'The Berserkers of Kjalengard', 'the-berserkers-of-kjalengard', 30),
    ('discordant-stars', 'The Monks of Kolume', 'the-monks-of-kolume', 31),
    ('discordant-stars', 'The Kyro Sodality', 'the-kyro-sodality', 32),
    ('discordant-stars', 'The Lanefir Remnants', 'the-lanefir-remnants', 33),
    ('discordant-stars', 'The Nokar Sellships', 'the-nokar-sellships', 34)
)
INSERT INTO public.factions (content_set_id, name, slug, active, sort_order)
SELECT cs.id, catalog.name, catalog.slug, true, catalog.sort_order
FROM catalog
JOIN public.content_sets cs ON cs.slug = catalog.content_set_slug;

-- Link historical picks when the free-text name exactly matches a catalog
-- entry (case and surrounding whitespace ignored). Unmatched test picks stay
-- readable with faction_id NULL; the NOT VALID check rejects new null IDs.
WITH matches AS (
    SELECT p.id AS pick_id, f.id AS faction_id,
           row_number() OVER (
               PARTITION BY p.draft_id, f.id
               ORDER BY p.created_at, p.id
           ) AS duplicate_number
    FROM public.picks p
    JOIN public.factions f
      ON lower(trim(p.faction)) = lower(trim(f.name))
    WHERE p.faction_id IS NULL
)
UPDATE public.picks AS p
SET faction_id = matches.faction_id
FROM matches
WHERE p.id = matches.pick_id AND matches.duplicate_number = 1;

CREATE OR REPLACE FUNCTION public.create_draft (
    p_player_name text,
    p_player_count integer
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_user_id uuid := auth.uid();
    v_draft public.drafts;
    v_player public.players;
    v_code text;
    v_base_set_id uuid;
BEGIN
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'Usuário não autenticado';
    END IF;
    IF p_player_name IS NULL
       OR char_length(trim(p_player_name)) NOT BETWEEN 1 AND 20 THEN
        RAISE EXCEPTION 'Nome inválido';
    END IF;
    IF p_player_count NOT BETWEEN 3 AND 6 THEN
        RAISE EXCEPTION 'A sala deve ter entre 3 e 6 jogadores';
    END IF;

    SELECT id INTO v_base_set_id
    FROM public.content_sets
    WHERE slug = 'base' AND active;
    IF v_base_set_id IS NULL THEN
        RAISE EXCEPTION 'Catálogo Base Game indisponível';
    END IF;

    LOOP
        v_code := upper(substr(md5(random()::text || clock_timestamp()::text), 1, 6));
        EXIT WHEN NOT EXISTS (SELECT 1 FROM public.drafts WHERE code = v_code);
    END LOOP;

    INSERT INTO public.drafts (code, status, host_id, player_count)
    VALUES (v_code, 'waiting', v_user_id, p_player_count)
    RETURNING * INTO v_draft;

    INSERT INTO public.players (draft_id, user_id, name, seat, connected)
    VALUES (v_draft.id, v_user_id, trim(p_player_name), NULL, true)
    RETURNING * INTO v_player;

    INSERT INTO public.draft_content_sets (draft_id, content_set_id)
    VALUES (v_draft.id, v_base_set_id);

    RETURN jsonb_build_object('draft', to_jsonb(v_draft), 'player', to_jsonb(v_player));
END;
$function$;

CREATE FUNCTION public.set_draft_content_sets (
    p_draft_id uuid,
    p_content_set_ids uuid[]
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_draft public.drafts%rowtype;
    v_requested_count integer;
BEGIN
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'Usuário não autenticado';
    END IF;
    IF p_content_set_ids IS NULL THEN
        RAISE EXCEPTION 'Lista de conjuntos inválida';
    END IF;

    SELECT * INTO v_draft
    FROM public.drafts
    WHERE id = p_draft_id
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Sala não encontrada';
    END IF;
    IF v_draft.host_id IS DISTINCT FROM auth.uid() THEN
        RAISE EXCEPTION 'Somente o host pode alterar o conteúdo do draft';
    END IF;
    IF v_draft.status <> 'waiting' THEN
        RAISE EXCEPTION 'O conteúdo só pode ser alterado enquanto a sala aguarda jogadores';
    END IF;

    v_requested_count := cardinality(p_content_set_ids);
    IF (
        SELECT count(DISTINCT requested.id)
        FROM unnest(p_content_set_ids) AS requested(id)
    ) <> v_requested_count THEN
        RAISE EXCEPTION 'Lista de conjuntos contém IDs duplicados ou inválidos';
    END IF;
    IF (
        SELECT count(*)
        FROM public.content_sets
        WHERE id = ANY(p_content_set_ids) AND active
    ) <> v_requested_count THEN
        RAISE EXCEPTION 'Conjunto de conteúdo inexistente ou inativo';
    END IF;

    -- The draft row lock serializes concurrent host config/start calls.
    -- Intermediate rows remain invisible until this RPC commits.
    DELETE FROM public.draft_content_sets
    WHERE draft_id = p_draft_id;
    INSERT INTO public.draft_content_sets (draft_id, content_set_id)
    SELECT p_draft_id, requested.id
    FROM unnest(p_content_set_ids) AS requested(id);

    UPDATE public.drafts
    SET content_version = content_version + 1
    WHERE id = p_draft_id;
END;
$function$;

CREATE OR REPLACE FUNCTION public.start_draft (p_draft_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_user_id uuid := auth.uid();
    v_draft public.drafts%rowtype;
    v_player_total integer;
    v_seated_total integer;
    v_min_seat integer;
    v_max_seat integer;
    v_first_player_id uuid;
    v_set_count integer;
    v_available_factions integer;
BEGIN
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'Usuário não autenticado';
    END IF;
    SELECT * INTO v_draft
    FROM public.drafts
    WHERE id = p_draft_id
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Sala não encontrada';
    END IF;
    IF v_draft.host_id IS DISTINCT FROM v_user_id THEN
        RAISE EXCEPTION 'Somente o host pode iniciar o draft';
    END IF;
    IF v_draft.status <> 'waiting' THEN
        RAISE EXCEPTION 'Somente uma sala aguardando pode ser iniciada';
    END IF;

    SELECT count(*), count(seat), min(seat), max(seat)
    INTO v_player_total, v_seated_total, v_min_seat, v_max_seat
    FROM public.players
    WHERE draft_id = p_draft_id;
    IF v_player_total <> v_draft.player_count THEN
        RAISE EXCEPTION 'É necessário ter todos os jogadores na sala';
    END IF;
    IF v_seated_total <> v_draft.player_count
       OR v_min_seat <> 1
       OR v_max_seat <> v_draft.player_count THEN
        RAISE EXCEPTION 'É necessário definir a ordem completa dos jogadores antes de iniciar';
    END IF;

    SELECT count(*) INTO v_set_count
    FROM public.draft_content_sets
    WHERE draft_id = p_draft_id;
    IF v_set_count = 0 THEN
        RAISE EXCEPTION 'Selecione ao menos um conjunto de conteúdo';
    END IF;

    SELECT count(*) INTO v_available_factions
    FROM public.factions f
    JOIN public.content_sets cs ON cs.id = f.content_set_id
    JOIN public.draft_content_sets dcs ON dcs.content_set_id = cs.id
    WHERE dcs.draft_id = p_draft_id
      AND cs.active AND f.active;
    IF v_available_factions = 0 THEN
        RAISE EXCEPTION 'Nenhuma facção ativa disponível para este draft';
    END IF;
    IF v_available_factions < v_draft.player_count THEN
        RAISE EXCEPTION 'Não há facções suficientes para todos os jogadores';
    END IF;

    SELECT id INTO v_first_player_id
    FROM public.players
    WHERE draft_id = p_draft_id AND seat = 1;
    IF v_first_player_id IS NULL THEN
        RAISE EXCEPTION 'Não foi possível encontrar o primeiro jogador';
    END IF;

    UPDATE public.drafts
    SET status = 'active', current_player = v_first_player_id
    WHERE id = p_draft_id;
    RETURN jsonb_build_object(
        'success', true,
        'status', 'active',
        'current_player', v_first_player_id
    );
END;
$function$;

CREATE FUNCTION public.make_pick (
    p_draft_id uuid,
    p_faction_id uuid
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
    v_draft public.drafts%rowtype;
    v_player public.players%rowtype;
    v_faction public.factions%rowtype;
    v_pick_order integer;
    v_next_player uuid;
BEGIN
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'Usuário não autenticado';
    END IF;
    SELECT * INTO v_draft
    FROM public.drafts
    WHERE id = p_draft_id
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Draft não encontrado.';
    END IF;
    IF v_draft.status <> 'active' THEN
        RAISE EXCEPTION 'O draft não está ativo.';
    END IF;

    SELECT * INTO v_player
    FROM public.players
    WHERE draft_id = p_draft_id AND user_id = auth.uid();
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Você não pertence a este draft.';
    END IF;
    IF v_draft.current_player IS DISTINCT FROM v_player.id THEN
        RAISE EXCEPTION 'Não é a sua vez.';
    END IF;

    SELECT * INTO v_faction
    FROM public.factions
    WHERE id = p_faction_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Facção inexistente.';
    END IF;
    IF NOT v_faction.active THEN
        RAISE EXCEPTION 'Facção inativa.';
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM public.draft_content_sets dcs
        JOIN public.content_sets cs ON cs.id = dcs.content_set_id
        WHERE dcs.draft_id = p_draft_id
          AND dcs.content_set_id = v_faction.content_set_id
          AND cs.active
    ) THEN
        RAISE EXCEPTION 'Conjunto da facção não está habilitado neste draft.';
    END IF;
    IF EXISTS (
        SELECT 1 FROM public.picks
        WHERE draft_id = p_draft_id
          AND (faction_id = p_faction_id
               OR lower(trim(faction)) = lower(trim(v_faction.name)))
    ) THEN
        RAISE EXCEPTION 'Esta facção já foi escolhida.';
    END IF;
    IF EXISTS (SELECT 1 FROM public.picks WHERE player_id = v_player.id) THEN
        RAISE EXCEPTION 'Você já escolheu uma facção.';
    END IF;

    SELECT coalesce(max(pick_order), 0) + 1 INTO v_pick_order
    FROM public.picks
    WHERE draft_id = p_draft_id;
    INSERT INTO public.picks (draft_id, player_id, faction_id, faction, pick_order)
    VALUES (p_draft_id, v_player.id, p_faction_id, v_faction.name, v_pick_order);

    SELECT id INTO v_next_player
    FROM public.players
    WHERE draft_id = p_draft_id AND seat > v_player.seat
    ORDER BY seat
    LIMIT 1;
    IF v_next_player IS NULL THEN
        UPDATE public.drafts
        SET status = 'finished', current_player = NULL
        WHERE id = p_draft_id;
        RETURN jsonb_build_object(
            'success', true,
            'status', 'finished',
            'pick_order', v_pick_order,
            'faction_id', p_faction_id,
            'faction', v_faction.name,
            'player_id', v_player.id
        );
    END IF;

    UPDATE public.drafts
    SET current_player = v_next_player
    WHERE id = p_draft_id;
    RETURN jsonb_build_object(
        'success', true,
        'status', 'active',
        'pick_order', v_pick_order,
        'faction_id', p_faction_id,
        'faction', v_faction.name,
        'player_id', v_player.id,
        'next_player', v_next_player
    );
END;
$function$;

-- Eliminate the free-text endpoint; it must not remain callable by clients.
DROP FUNCTION public.make_pick(uuid, text);

REVOKE ALL ON FUNCTION public.set_draft_content_sets(uuid, uuid[]) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.make_pick(uuid, uuid) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.set_draft_content_sets(uuid, uuid[]) TO authenticated;
GRANT EXECUTE ON FUNCTION public.make_pick(uuid, uuid) TO authenticated;

-- draft_content_sets is intentionally absent from supabase_realtime: DELETE
-- changes cannot be safely scoped to a draft for every client. The drafts
-- publication delivers content_version changes, and RLS guards the reload.
