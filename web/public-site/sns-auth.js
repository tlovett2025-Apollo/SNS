(() => {
  const config = window.SNS_CONFIG || {};
  const library = window.supabase;
  if (!library?.createClient || !config.supabaseUrl || !config.supabasePublishableKey) {
    window.SNS_AUTH = { configured: false };
    return;
  }

  const client = library.createClient(config.supabaseUrl, config.supabasePublishableKey, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true
    }
  });

  async function session() {
    const { data, error } = await client.auth.getSession();
    if (error) throw error;
    return data.session || null;
  }

  async function accessToken() {
    return (await session())?.access_token || "";
  }

  window.SNS_AUTH = {
    configured: true,
    client,
    session,
    accessToken,
    async signIn(email, password) {
      const { data, error } = await client.auth.signInWithPassword({ email, password });
      if (error) throw error;
      return data;
    },
    async signUp(email, password, displayName = "") {
      const { data, error } = await client.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: new URL("home.html", location.href).href,
          data: { display_name: displayName || email.split("@")[0] }
        }
      });
      if (error) throw error;
      return data;
    },
    async resetPassword(email) {
      const { data, error } = await client.auth.resetPasswordForEmail(email, {
        redirectTo: new URL("login.html?mode=recovery", location.href).href
      });
      if (error) throw error;
      return data;
    },
    async signOut() {
      const { error } = await client.auth.signOut();
      if (error) throw error;
    },
    onChange(callback) {
      return client.auth.onAuthStateChange((_event, currentSession) => callback(currentSession));
    }
  };
})();
