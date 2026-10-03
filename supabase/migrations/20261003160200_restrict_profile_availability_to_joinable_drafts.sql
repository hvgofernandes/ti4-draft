-- Profile occupancy is disclosed only for waiting rooms that still accept a
-- player. Active, finished, full, and unknown rooms remain private.
CREATE OR REPLACE FUNCTION public.list_player_profiles(p_draft_id uuid DEFAULT NULL)
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
