// auth.js — Supabase Google-only authentication helpers

let supabaseClient = null;
let currentSession = null;

function authElements() {
  return {
    signInBtn: document.getElementById("authSignInBtn"),
    profileBtn: document.getElementById("profileBtn"),
    profileMenu: document.getElementById("profileMenu"),
    profileEmail: document.getElementById("profileEmail"),
    profileSignOutBtn: document.getElementById("profileSignOutBtn"),
    authNavArea: document.getElementById("authNavArea"),
    modal: document.getElementById("authModal"),
    modalCloseBtn: document.getElementById("authModalCloseBtn"),
    googleSignInBtn: document.getElementById("googleSignInBtn"),
  };
}

function setAuthButtonState() {
  const { signInBtn, profileBtn, profileMenu, profileEmail } = authElements();
  if (!signInBtn || !profileBtn || !profileMenu || !profileEmail) return;

  const user = currentSession?.user;
  if (user) {
    profileEmail.textContent = user.email || "Signed in";
    signInBtn.classList.add("hidden");
    profileBtn.classList.remove("hidden");
    profileBtn.classList.add("inline-flex");
  } else {
    signInBtn.classList.remove("hidden");
    profileBtn.classList.add("hidden");
    profileBtn.classList.remove("inline-flex");
    profileMenu.classList.add("hidden");
    profileBtn.setAttribute("aria-expanded", "false");
  }
}

function openProfileMenu() {
  const { profileMenu, profileBtn } = authElements();
  if (!profileMenu || !profileBtn) return;
  profileMenu.classList.remove("hidden");
  profileBtn.setAttribute("aria-expanded", "true");
}

function closeProfileMenu() {
  const { profileMenu, profileBtn } = authElements();
  if (!profileMenu || !profileBtn) return;
  profileMenu.classList.add("hidden");
  profileBtn.setAttribute("aria-expanded", "false");
}

function toggleProfileMenu() {
  const { profileMenu } = authElements();
  if (!profileMenu) return;
  if (profileMenu.classList.contains("hidden")) {
    openProfileMenu();
  } else {
    closeProfileMenu();
  }
}

function showAuthModal() {
  const { modal } = authElements();
  if (!modal) return;
  modal.classList.remove("hidden");
  modal.classList.add("flex");
  modal.setAttribute("aria-hidden", "false");
}

window.showAuthModal = showAuthModal;

function hideAuthModal() {
  const { modal } = authElements();
  if (!modal) return;
  modal.classList.add("hidden");
  modal.classList.remove("flex");
  modal.setAttribute("aria-hidden", "true");
}

window.hideAuthModal = hideAuthModal;

async function signInWithGoogle() {
  if (!supabaseClient) return;
  await supabaseClient.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: window.location.origin + window.location.pathname,
      queryParams: {
        access_type: "offline",
        prompt: "consent",
      },
    },
  });
}

async function signOutSupabase() {
  if (!supabaseClient) return;
  await supabaseClient.auth.signOut();
  currentSession = null;
  setAuthButtonState();
}

window.authRequireUser = async function authRequireUser() {
  if (currentSession?.access_token) {
    return true;
  }
  showAuthModal();
  return false;
};

window.getAuthToken = function getAuthToken() {
  return currentSession?.access_token || "";
};

async function initAuth() {
  const supabaseConfig = document.getElementById("supabaseConfig");
  const supabaseUrl = (supabaseConfig?.dataset?.url || "").trim();
  const supabaseAnonKey = (supabaseConfig?.dataset?.anonKey || "").trim();
  const {
    signInBtn,
    profileBtn,
    profileSignOutBtn,
    authNavArea,
    modalCloseBtn,
    googleSignInBtn,
  } = authElements();

  if (!supabaseUrl || !supabaseAnonKey || !window.supabase?.createClient) {
    if (signInBtn) {
      signInBtn.disabled = true;
      signInBtn.textContent = "Auth unavailable";
      signInBtn.title = "Set SUPABASE_URL and SUPABASE_ANON_KEY in .env";
    }
    return;
  }

  supabaseClient = window.supabase.createClient(supabaseUrl, supabaseAnonKey);

  const { data } = await supabaseClient.auth.getSession();
  currentSession = data.session;
  setAuthButtonState();

  if (signInBtn) {
    signInBtn.addEventListener("click", async () => {
      showAuthModal();
    });
  }

  if (profileBtn) {
    profileBtn.addEventListener("click", () => {
      toggleProfileMenu();
    });
  }

  if (profileSignOutBtn) {
    profileSignOutBtn.addEventListener("click", async () => {
      closeProfileMenu();
      await signOutSupabase();
    });
  }

  if (authNavArea) {
    document.addEventListener("click", (event) => {
      if (!authNavArea.contains(event.target)) {
        closeProfileMenu();
      }
    });
  }

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener("click", hideAuthModal);
  }

  if (googleSignInBtn) {
    googleSignInBtn.addEventListener("click", async () => {
      await signInWithGoogle();
    });
  }

  supabaseClient.auth.onAuthStateChange((_event, session) => {
    currentSession = session;
    setAuthButtonState();
    if (session?.user) {
      hideAuthModal();
      closeProfileMenu();
    }
  });
}

document.addEventListener("DOMContentLoaded", initAuth);
