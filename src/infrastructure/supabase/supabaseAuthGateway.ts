import type { AuthGateway, AuthenticatedUser } from "../../application/ports";
import { supabase } from "./client";

export class SupabaseAuthGateway implements AuthGateway {
  private pendingSession: Promise<AuthenticatedUser> | null = null;

  ensureAnonymousSession(): Promise<AuthenticatedUser> {
    if (!this.pendingSession) {
      this.pendingSession = this.loadOrCreateSession().finally(() => {
        this.pendingSession = null;
      });
    }
    return this.pendingSession;
  }

  private async loadOrCreateSession(): Promise<AuthenticatedUser> {
    const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
    if (sessionError) throw new Error(sessionError.message);

    if (sessionData.session?.user) {
      return { id: sessionData.session.user.id };
    }

    const { data, error } = await supabase.auth.signInAnonymously();
    if (error) throw new Error(error.message);
    if (!data.user) throw new Error("A autenticação não retornou um usuário.");

    return { id: data.user.id };
  }
}
