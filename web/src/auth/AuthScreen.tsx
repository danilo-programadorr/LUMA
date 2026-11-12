import { useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { LumaBrandMark } from '@/components/luma/brand-mark';
import { TechBackground } from '@/components/luma/tech-background';
import { useAuth, safeRedirect } from './context';
export function AuthScreen() {
  const auth = useAuth(); const location = useLocation(); const [code,setCode] = useState('');
  if (auth.state === 'AUTHENTICATED') return <Navigate replace to={safeRedirect(new URLSearchParams(location.search).get('returnTo'))} />;
  const busy = ['INITIALIZING','AUTHENTICATING'].includes(auth.state);
  const message = auth.state === 'FORBIDDEN' ? 'Acesso não autorizado' : auth.state === 'SESSION_EXPIRED' ? 'Sessão expirada. Entre novamente para continuar.' : auth.state === 'ERROR' ? 'Não foi possível conectar. Verifique a configuração e a conexão.' : busy ? 'Verificando identidade…' : 'Acesso restrito ao proprietário.';
  return <main className="relative grid min-h-dvh place-items-center overflow-auto bg-void p-5"><TechBackground /><section className="hud-panel relative w-full max-w-md space-y-6 p-7 text-center"><LumaBrandMark className="mx-auto size-24" /><h1 className="text-2xl text-primary">LUMA Centro de Comando</h1><p role="status">{message}</p><button className="w-full rounded border border-primary bg-primary/10 p-3 text-primary focus-visible:outline focus-visible:outline-2" disabled={busy} onClick={() => void auth.login()}>Entrar com Google</button>{auth.state === 'FORBIDDEN' && <details className="text-left"><summary>Vincular proprietário com código local</summary><form className="mt-3 space-y-3" onSubmit={e => { e.preventDefault(); const value=code; setCode(''); void auth.bootstrap(value); }}><label htmlFor="bootstrap">Código de uso único</label><input id="bootstrap" type="password" autoComplete="off" value={code} onChange={e => setCode(e.target.value)} maxLength={256} className="w-full rounded border border-primary bg-void p-2" /><button className="rounded border border-primary p-2">Vincular proprietário</button></form></details>}{['FORBIDDEN','ERROR','SESSION_EXPIRED'].includes(auth.state) && <button onClick={() => void auth.logout()}>Sair</button>}</section></main>;
}
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const auth = useAuth(); const location = useLocation();
  if (auth.state !== 'AUTHENTICATED') return <Navigate replace to={'/login?returnTo='+encodeURIComponent(safeRedirect(location.pathname))} />;
  return children;
}
export function ReauthenticateButton() { const auth=useAuth(); return <button onClick={() => void auth.reauthenticate()}>Confirmar identidade novamente</button>; }
