import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

interface AuthState {
  isAuthenticated: boolean;
  user: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<string | null>(() => {
    return sessionStorage.getItem("ow_user");
  });

  const login = useCallback(async (username: string, _password: string): Promise<boolean> => {
    // Demo auth for now — will integrate with backend POST /auth/login
    if (username.trim().length > 0) {
      setUser(username);
      sessionStorage.setItem("ow_user", username);
      return true;
    }
    return false;
  }, []);

  const register = useCallback(async (email: string, password: string, name: string): Promise<void> => {
    // Demo registration for now — will integrate with backend POST /auth/signup
    if (!email || !password || !name) {
      throw new Error("All fields are required");
    }
    // In real implementation, this would call POST /auth/signup
    setUser(name);
    sessionStorage.setItem("ow_user", name);
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    sessionStorage.removeItem("ow_user");
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated: !!user, user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
