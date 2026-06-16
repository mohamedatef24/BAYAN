// Auth UI — gate, account menu, offline banner

function bindAuthUIEvents() {
  const guestBtn = document.getElementById('auth-guest-btn');
  const googleBtn = document.getElementById('auth-google-btn');
  const linkBtn = document.getElementById('auth-link-google-btn');
  const logoutBtn = document.getElementById('auth-logout-btn');
  const menuTrigger = document.getElementById('auth-menu-trigger');
  const menu = document.getElementById('auth-account-menu');
  const gateBackdrop = document.getElementById('auth-gate-backdrop');
  const mobileGuest = document.getElementById('auth-guest-btn-mobile');
  const mobileGoogle = document.getElementById('auth-google-btn-mobile');
  if (guestBtn) {
    guestBtn.addEventListener('click', async () => {
      guestBtn.disabled = true;
      const originalText = guestBtn.textContent;
      guestBtn.textContent = 'جاري الدخول...';

      const result = await signInAsGuest();
      guestBtn.disabled = false;
      hideAuthGate();
      showAuthOfflineBanner(false);

      if (!result.success && !result.offline) {
        alert('حدث خطأ أثناء الدخول كضيف. حاول مجددًا.');
        guestBtn.textContent = originalText;
      } else {
        if (typeof showPage === 'function') showPage('home');
      }
    });
  }

  if (mobileGuest) {
    mobileGuest.addEventListener('click', async () => {
      mobileGuest.disabled = true;
      const result = await signInAsGuest();
      mobileGuest.disabled = false;
      hideAuthGate();
      closeAuthGateSheet();
      showAuthOfflineBanner(false);
      if (result && (result.success || result.offline)) {
        if (typeof showPage === 'function') showPage('home');
      }
    });
  }

  if (googleBtn) {
    googleBtn.addEventListener('click', () => signInWithGoogle());
  }

  if (mobileGoogle) {
    mobileGoogle.addEventListener('click', () => {
      closeAuthGateSheet();
      signInWithGoogle();
    });
  }

  if (linkBtn) {
    linkBtn.addEventListener('click', () => {
      closeAuthMenu();
      linkGoogle();
    });
  }

  if (logoutBtn) {
    logoutBtn.addEventListener('click', async () => {
      closeAuthMenu();
      await signOut();
    });
  }

  const logoutMobile = document.getElementById('auth-logout-btn-mobile');
  const linkMobile = document.getElementById('auth-link-google-btn-mobile');
  if (logoutMobile) {
    logoutMobile.addEventListener('click', async () => {
      await signOut();
    });
  }
  if (linkMobile) {
    linkMobile.addEventListener('click', () => linkGoogle());
  }

  if (menuTrigger && menu) {
    menuTrigger.addEventListener('click', (e) => {
      e.stopPropagation();
      const open = menu.classList.toggle('is-open');
      menuTrigger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  if (gateBackdrop) {
    gateBackdrop.addEventListener('click', () => {
      /* Gate requires explicit choice — backdrop not dismissible */
    });
  }

  document.addEventListener('click', () => closeAuthMenu());

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeAuthMenu();
  });
}

function showAuthGate() {
  const gate = document.getElementById('auth-gate');
  if (!gate) return;
  gate.classList.add('is-open');
  gate.setAttribute('aria-hidden', 'false');
}

function hideAuthGate() {
  const gate = document.getElementById('auth-gate');
  if (!gate) return;
  gate.classList.remove('is-open');
  gate.setAttribute('aria-hidden', 'true');
}

function closeAuthGateSheet() {
  const sheet = document.getElementById('auth-gate-sheet');
  if (sheet) sheet.classList.remove('open');
}

function closeAuthMenu() {
  const menu = document.getElementById('auth-account-menu');
  const trigger = document.getElementById('auth-menu-trigger');
  if (menu) menu.classList.remove('is-open');
  if (trigger) trigger.setAttribute('aria-expanded', 'false');
}

function showAuthOfflineBanner(show) {
  const banner = document.getElementById('auth-offline-banner');
  if (!banner) return;
  if (show) {
    banner.classList.remove('is-hidden');
  } else {
    banner.classList.add('is-hidden');
  }
}

/**
 * Update account menu and nav auth state
 * @param {object|null} user
 */
function updateAuthUI(user) {
  const menuWrap = document.getElementById('auth-menu-wrap');
  const nameEl = document.getElementById('auth-display-name');
  const providerEl = document.getElementById('auth-provider-label');
  const avatarEl = document.getElementById('auth-avatar');
  const linkBtn = document.getElementById('auth-link-google-btn');
  const linkMobile = document.getElementById('auth-link-google-btn-mobile');
  const logoutMobile = document.getElementById('auth-logout-btn-mobile');
  const logoutBtn = document.getElementById('auth-logout-btn');
  const drawerName = document.getElementById('auth-drawer-name');
  const drawerProvider = document.getElementById('auth-drawer-provider');

  const offline = window.__bayanAuth && window.__bayanAuth.isOfflineMode;

  // Guest / offline mode — show menu so user can still sign in with Google
  if (!user || offline) {
    if (menuWrap) menuWrap.classList.remove('is-hidden');
    if (nameEl) nameEl.textContent = 'ضيف';
    if (providerEl) providerEl.textContent = 'ضيف';
    if (avatarEl) avatarEl.textContent = 'ض';
    if (drawerName) drawerName.textContent = 'ضيف';
    if (drawerProvider) drawerProvider.textContent = '';
    // Show Google sign-in option, hide logout
    if (linkBtn) linkBtn.classList.remove('is-hidden');
    if (linkMobile) linkMobile.classList.remove('is-hidden');
    if (logoutBtn) logoutBtn.classList.add('is-hidden');
    if (logoutMobile) logoutMobile.classList.add('is-hidden');
    return;
  }

  if (menuWrap) menuWrap.classList.remove('is-hidden');

  const displayName = getDisplayName(user);
  const provider = getAuthProvider(user);
  const providerLabel = provider === 'google' ? 'Google' : 'ضيف';
  const avatarUrl = getAvatarUrl(user);

  if (nameEl) nameEl.textContent = displayName;
  if (providerEl) providerEl.textContent = providerLabel;
  if (drawerName) drawerName.textContent = displayName;
  if (drawerProvider) drawerProvider.textContent = providerLabel;

  if (avatarEl) {
    if (avatarUrl && /^https?:\/\//i.test(avatarUrl)) {
      avatarEl.textContent = '';
      const img = document.createElement('img');
      img.src = avatarUrl;
      img.alt = '';
      img.className = 'auth-avatar-img';
      img.referrerPolicy = 'no-referrer';
      avatarEl.appendChild(img);
    } else {
      avatarEl.textContent = isGuestUser(user) ? 'ض' : displayName.charAt(0).toUpperCase();
    }
  }

  // Show Google link only for guests, show logout for everyone
  if (linkBtn) linkBtn.classList.toggle('is-hidden', !isGuestUser(user));
  if (linkMobile) linkMobile.classList.toggle('is-hidden', !isGuestUser(user));
  if (logoutBtn) logoutBtn.classList.remove('is-hidden');
  if (logoutMobile) logoutMobile.classList.remove('is-hidden');
}
