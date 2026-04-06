const TOKEN_KEY = "token";
const USER_EMAIL_KEY = "ow_user_email";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUserEmail(): string | null {
  return localStorage.getItem(USER_EMAIL_KEY);
}

export function setAuthSession(token: string, email: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_EMAIL_KEY, email);
}

export function clearAuthSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_EMAIL_KEY);
}

export function getAuthHeaders(): HeadersInit {
  const token = getToken();
  if (!token) {
    return {};
  }
  return { Authorization: `Bearer ${token}` };
}
