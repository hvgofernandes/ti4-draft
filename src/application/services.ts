import { SupabaseAuthGateway } from "../infrastructure/supabase/supabaseAuthGateway";
import { SupabaseDraftGateway } from "../infrastructure/supabase/supabaseDraftGateway";

export const authGateway = new SupabaseAuthGateway();
export const draftGateway = new SupabaseDraftGateway();
