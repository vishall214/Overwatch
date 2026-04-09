import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import {
  clearAuthSession,
  getStoredUserEmail,
  getToken,
  onAuthInvalidated,
  setAuthSession,
} from "../api/auth";
import { login as loginRequest, signup as signupRequest } from "../services/authService";

interface AuthState {
  isAuthenticated: boolean;
  user: string | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => getToken());
  const [user, setUser] = useState<string | null>(() => getStoredUserEmail());

  useEffect(() => {
    return onAuthInvalidated(() => {
      setToken(null);
      setUser(null);
    });
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<void> => {
    const res = await loginRequest(email, password);
    setAuthSession(res.access_token, email);
    setToken(res.access_token);
    setUser(email);
  }, []);

  const register = useCallback(async (email: string, password: string): Promise<void> => {
    const res = await signupRequest(email, password);
    setAuthSession(res.access_token, email);
    setToken(res.access_token);
    setUser(email);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    clearAuthSession();
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: !!token,
        token,
        user,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
