import {createContext, useContext, useEffect, useMemo, useState} from 'react';
import type {ReactNode} from 'react';
import {api, tokenStore} from './api';
import type {User} from '../types';

type AuthValue = {user: User|null; loading: boolean; authenticate: (token: string, user: User) => void; logout: () => void};
const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({children}: {children: ReactNode}) {
  const [user, setUser] = useState<User|null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!tokenStore.get()) {setLoading(false); return;}
    api<User>('/auth/me').then(setUser).catch(() => tokenStore.clear()).finally(() => setLoading(false));
  }, []);
  const value = useMemo(() => ({
    user, loading,
    authenticate: (token: string, next: User) => {tokenStore.set(token); setUser(next);},
    logout: () => {tokenStore.clear(); setUser(null);},
  }), [user, loading]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}

