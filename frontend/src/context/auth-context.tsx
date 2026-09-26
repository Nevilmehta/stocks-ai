"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api";
import type { User } from "@/types";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const currentUser = await api.get<User>("/api/auth/me");
      setUser(currentUser);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setUser(null);
      } else {
        throw error;
      }
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setIsLoading(false));
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const { user: loggedInUser } = await api.post<{ user: User }>("/api/auth/login", {
      email,
      password,
    });
    setUser(loggedInUser);
  }, []);

  const register = useCallback(async (email: string, password: string, displayName: string) => {
    const { user: registeredUser } = await api.post<{ user: User }>("/api/auth/register", {
      email,
      password,
      display_name: displayName,
    });
    setUser(registeredUser);
  }, []);

  const logout = useCallback(async () => {
    await api.post("/api/auth/logout");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
