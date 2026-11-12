import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { AuthContext, type AuthState } from './context';
import { ApiError, ControlPlaneClient, GoogleAuthClient, type AuthClient, type Owner } from './client';
let singleton: AuthClient | null = null;
function officialClient() { if (!singleton) singleton = new GoogleAuthClient(); return singleton; }
export function AuthProvider({ children, testClient }: { children: ReactNode; testClient?: AuthClient }) {
  if (testClient && import.meta.env.MODE !== 'test') throw new Error('TEST_ADAPTER_DENIED');
  const [state,setState] = useState<AuthState>('INITIALIZING');
  const [health,setHealth] = useState('UNKNOWN');
  const [owner,setOwner] = useState<Owner | null>(null);
  const generation = useRef(0);
  const refreshInFlight = useRef(false);
  const client = useMemo(() => { try { return testClient || officialClient(); } catch { return null; } }, [testClient]);
  const api = useMemo(() => client ? new ControlPlaneClient(client) : null, [client]);
  const refresh = useCallback(async () => {
    refreshInFlight.current = true;
    try {
    const run = ++generation.current;
    if (!api) { setState('ERROR'); return; }
    try { const result = await api.me(); if (run !== generation.current) return; setOwner(result); setState('AUTHENTICATED'); void api.health().then(h => { if(run===generation.current)setHealth(h.database_status === 'AVAILABLE' ? 'AVAILABLE' : 'UNAVAILABLE'); }).catch(() => { if(run===generation.current)setHealth('UNAVAILABLE'); }); }
    catch (e) { if (run !== generation.current) return; setOwner(null); const status = e instanceof ApiError ? e.status : 0; setState(status === 403 ? 'FORBIDDEN' : status === 401 ? 'SESSION_EXPIRED' : 'ERROR'); if (status === 401) { try { await client?.logout(); } catch { /* Keep local session expired even when SDK sign-out fails. */ } setState('SESSION_EXPIRED'); } }
    } finally { refreshInFlight.current = false; }
  }, [api,client]);
  useEffect(() => {
    if (!client) { setState('SIGNED_OUT'); return; }
    return client.observe(signed => { if (signed) { if (!refreshInFlight.current) void refresh(); } else { generation.current++; setOwner(null); setState('SIGNED_OUT'); } });
  }, [client,refresh]);
  const login = async () => { setState('AUTHENTICATING'); try { if (!client) throw new Error(); await client.login(); } catch { setState('ERROR'); } };
  const logout = async () => { generation.current++; setOwner(null); setState('SIGNED_OUT'); try { await client?.logout(); } catch { setState('ERROR'); } };
  const bootstrap = async (code: string) => { try { if (!api) throw new Error(); await api.bootstrap(code); await refresh(); } catch { setState('FORBIDDEN'); } };
  const reauthenticate = async () => { try { await client?.reauthenticate(); await refresh(); } catch { setState('ERROR'); } };
  return <AuthContext.Provider value={{ deviceApi:api || undefined,state,owner,health,login,logout,bootstrap,refresh,reauthenticate }}>{children}</AuthContext.Provider>;
}
