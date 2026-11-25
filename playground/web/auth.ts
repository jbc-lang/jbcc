import { initializeApp, type FirebaseOptions } from "firebase/app";
import {
  browserPopupRedirectResolver,
  browserSessionPersistence,
  GithubAuthProvider,
  initializeAuth,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
} from "firebase/auth";

export function connectAuth(config: FirebaseOptions) {
  const auth = initializeAuth(initializeApp(config), {
    persistence: browserSessionPersistence,
    popupRedirectResolver: browserPopupRedirectResolver,
  });
  const control = document.getElementById("sign-in") as HTMLButtonElement;
  const message = document.getElementById("auth-status")!;
  control.hidden = false;

  onAuthStateChanged(auth, async (user) => {
    control.textContent = user ? "Sign out" : "Sign in with GitHub";
    message.textContent = "";
    if (!user) return;
    try {
      const token = await user.getIdToken();
      const response = await fetch("/api/v1/auth/session", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (auth.currentUser === user && !response.ok) {
        message.textContent = response.status === 403
          ? "This GitHub account isn’t on the invite list"
          : "Could not verify your sign-in";
      }
    } catch {
      if (auth.currentUser === user) message.textContent = "Could not verify your sign-in";
    }
  });

  control.addEventListener("click", async () => {
    control.disabled = true;
    try {
      if (auth.currentUser) {
        await signOut(auth);
      } else {
        // GitHub authenticates identity only. No repository scopes are requested.
        await signInWithPopup(auth, new GithubAuthProvider());
      }
    } catch {
      message.textContent = "Could not complete GitHub sign-in";
    } finally {
      control.disabled = false;
    }
  });

  return {
    async session() {
      await auth.authStateReady();
      const user = auth.currentUser;
      if (!user) throw new Error("Sign in with GitHub first");
      return {
        uid: user.uid,
        headers: { Authorization: `Bearer ${await user.getIdToken()}` },
      };
    },
  };
}
