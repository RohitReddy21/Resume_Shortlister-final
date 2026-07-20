const TOKEN_STORAGE_KEY = 'resumeparser.tokens';

function setCookie(name: string, value: string, days = 7) {
  if (typeof document === 'undefined') return;
  const expires = new Date(Date.now() + days * 24 * 60 * 60 * 1000).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

function deleteCookie(name: string) {
  if (typeof document === 'undefined') return;
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
}

export function getStoredTokens() {
  if (typeof window === 'undefined') return null;
  const raw = window.localStorage.getItem(TOKEN_STORAGE_KEY);
  return raw ? JSON.parse(raw) : null;
}

export function saveTokens(tokens: { access_token: string; refresh_token: string }) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens));
  setCookie('access_token', tokens.access_token);
  setCookie('refresh_token', tokens.refresh_token);
}

export function clearTokens() {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  deleteCookie('access_token');
  deleteCookie('refresh_token');
}

export function getAccessToken() {
  const tokens = getStoredTokens();
  return tokens?.access_token ?? null;
}
