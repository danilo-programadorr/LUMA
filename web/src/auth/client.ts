import {registerAuthenticatedResearchDelivery} from '@/lib/google-display';
import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut, onIdTokenChanged, setPersistence, browserLocalPersistence, reauthenticateWithPopup, type User } from 'firebase/auth';
export interface Owner { internal_owner_id: string; provider: string; status: string; auth_time: number }
const publicApiCodes=new Set(['CODEX_WORKSPACE_CHANGED','CODEX_MAPPING_CHANGED','CODEX_BINARY_CHANGED','CODEX_DISABLED','CODEX_PREFLIGHT_REQUIRED','RECENT_AUTH_REQUIRED','PROPOSAL_CHANGED','HIGH_CONFIRMATION_REQUIRED','TEST_TOOL_DISABLED','RESEARCH_EGRESS_BLOCKED','UNSAFE_URL','PUBLIC_QUERY_REQUIRED','DEVICE_REVOKED','DEVICE_NOT_ACTIVE','DEVICE_OWNER_MISMATCH','DEVICE_CAPABILITY_MISMATCH','DEVICE_UNKNOWN','OWNER_BINDING_INACTIVE','ADMIN_CAPABILITY_DENIED','CAPABILITY_DENIED','PRINCIPAL_INACTIVE','FORBIDDEN','FORBIDDEN_SCOPE','PROJECT_SUSPENDED','TOOL_DISABLED','LUMA_STOPPED','LUMA_PAUSED','LUMA_LOCKED','RESEARCH_BUDGET_EXCEEDED','DEVICE_RATE_LIMITED','IDEMPOTENCY_CONFLICT','LIBRARY_CAPABILITY_REQUIRED','LIBRARY_SOURCE_UNAVAILABLE','LIBRARY_NO_SOURCES','LIBRARY_QUERY_EXPIRED','LIBRARY_SOURCE_ARCHIVED','LIBRARY_QUERY_LIMIT','LIBRARY_SCOPE','PRIVATE_LIBRARY_USE_KNOWLEDGE']);
export class ApiError extends Error {
  public readonly code?:string;
  constructor(public status: number, code?:unknown) {
    super(status === 0 ? 'NETWORK_UNAVAILABLE' : 'AUTH_REQUEST_FAILED');
    this.code=typeof code==='string'&&publicApiCodes.has(code)?code:undefined;
  }
}
export interface AuthClient { observe(fn: (user: boolean) => void): () => void; login(): Promise<void>; logout(): Promise<void>; token(force?: boolean): Promise<string>; reauthenticate(): Promise<void> }
export class GoogleAuthClient implements AuthClient {
  private auth; private user: User | null = null;
  constructor() {
    const projectId = import.meta.env.VITE_FIREBASE_PROJECT_ID;
    const apiKey = import.meta.env.VITE_FIREBASE_API_KEY;
    const authDomain = import.meta.env.VITE_FIREBASE_AUTH_DOMAIN;
    if (!projectId || !apiKey || !authDomain) throw new Error('AUTH_NOT_CONFIGURED');
    this.auth = getAuth(initializeApp({ projectId, apiKey, authDomain }));
  }
  observe(fn: (user: boolean) => void) { return onIdTokenChanged(this.auth, user => { this.user = user; fn(!!user); }); }
  async login() { await setPersistence(this.auth, browserLocalPersistence); await signInWithPopup(this.auth, new GoogleAuthProvider()); }
  async logout() { await signOut(this.auth); this.user = null; }
  async token(force = false) { if (!this.user) throw new ApiError(401); return this.user.getIdToken(force); }
  async reauthenticate() { if (!this.user) throw new ApiError(401); await reauthenticateWithPopup(this.user, new GoogleAuthProvider()); }
}
export class ControlPlaneClient {
  constructor(private auth: AuthClient, private base = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8770', private request: typeof fetch = (input, init) => fetch(input, init)) {
    const u = new URL(base);
    if (u.username || u.password || (u.protocol !== 'https:' && !(u.protocol === 'http:' && ['localhost','127.0.0.1'].includes(u.hostname)))) throw new Error('INVALID_API_URL');
  }
  async call<T>(path: string, body?: object): Promise<T> {
    if (!path.startsWith('/v1/') || path.includes('..') || path.includes('?') || path.includes('#')) throw new Error('INVALID_API_PATH');
    for (let attempt = 0; attempt < 2; attempt++) {
      let response: Response;
      const token = await this.auth.token(attempt === 1);
      try { response = await this.request(this.base + path, { method: body ? 'POST' : 'GET', headers: { Authorization: `Bearer ${token}`, 'Content-Type':'application/json', 'X-Correlation-ID': crypto.randomUUID() }, body: body ? JSON.stringify(body) : undefined, cache:'no-store', credentials:'omit', signal: AbortSignal.timeout(15000) }); }
      catch { throw new ApiError(0); }
      if (response.status === 401 && attempt === 0) continue;
      if (!response.ok) {
        let code:unknown;
        try { code=(await response.json())?.error?.code; } catch { /* An empty or invalid body still preserves HTTP status. */ }
        throw new ApiError(response.status,code);
      }
      const data=await response.json();registerAuthenticatedResearchDelivery(path,data);return data as T;
    }
    throw new ApiError(401);
  }
  displayUrl(path:string):string {
    if(!/^\/research-display\/[A-Za-z0-9_-]{43}$/.test(path))throw new Error('INVALID_DISPLAY_PATH');
    return this.base+path;
  }
  async health() {
    try { const r=await this.request(this.base+'/health',{cache:'no-store',credentials:'omit',signal:AbortSignal.timeout(15000)}); if(!r.ok)throw new Error(); const data=await r.json(); return {mode:data.mode,version:data.version,database_status:data.database_status}; } catch { throw new ApiError(0); }
  }
  me() { return this.call<Owner>('/v1/owner/me'); }
  bootstrap(code: string) { return this.call('/v1/owner/bootstrap', { code }); }
}
