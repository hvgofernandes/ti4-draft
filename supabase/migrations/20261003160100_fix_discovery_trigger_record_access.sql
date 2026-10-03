-- Keep local databases that already applied the Phase 3.3 migration aligned
-- with the clean migration definition. PostgreSQL trigger records expose only
-- fields from their source table, so branch before reading either identifier.
CREATE OR REPLACE FUNCTION public.touch_draft_discovery_signal()
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
