import { createContext, useContext } from 'react';
import type { Owner, ControlPlaneClient } from './client';
export type AuthState = 'INITIALIZING' | 'SIGNED_OUT' | 'AUTHENTICATING' | 'AUTHENTICATED' | 'FORBIDDEN' | 'SESSION_EXPIRED' | 'ERROR';
export interface AuthValue { deviceApi?: ControlPlaneClient; state: AuthState; owner: Owner | null; health?: string; login(): Promise<void>; logout(): Promise<void>; bootstrap(code: string): Promise<void>; refresh(): Promise<void>; reauthenticate(): Promise<void> }
export const AuthContext = createContext<AuthValue | null>(null);
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error('AUTH_PROVIDER_REQUIRED'); return value; }
export const protectedPaths = ['/', '/dashboard','/core','/agents','/projects','/tasks','/calendar','/memory','/conversations','/knowledge','/tools','/workflows','/devices','/approvals','/settings'];
export function safeRedirect(path: string | null) { return path && (protectedPaths.includes(path) || /^\/(?:tasks|approvals)\/[a-f0-9]{32}$/.test(path)) ? path : '/'; }
