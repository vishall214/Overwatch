import { API } from "../api/config";

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export async function signup(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(API.auth.signup, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new Error(payload.detail || "Signup failed");
  }

  return res.json();
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(API.auth.login, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new Error(payload.detail || "Login failed");
  }

  return res.json();
}
