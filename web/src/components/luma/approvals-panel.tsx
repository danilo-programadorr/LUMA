import {useEffect,useState} from 'react';
import {ArrowRight,ShieldQuestion} from 'lucide-react';
import {useAuth} from '@/auth/context';
import {cn} from '@/lib/utils';
import {Panel,PanelHeader,PanelLink} from '@/components/luma/panel';
import {ToneChip} from '@/components/luma/status-indicator';
interface ApprovalsPanelProps {className?:string;variant?:'rail'|'full';showCardCorners?:boolean}
export const ApprovalsPanel=({className,variant='full'}:ApprovalsPanelProps)=>{
 const {deviceApi:api,state}=useAuth();const [count,setCount]=useState<number|null>(null);
 useEffect(()=>{let alive=true;let inFlight=false;setCount(null);if(!api||state!=='AUTHENTICATED')return;const refresh=()=>{if(inFlight)return;inFlight=true;void api.call<{pending:number}>('/v1/remote-approvals/summary').then(result=>{if(alive)setCount(typeof result.pending==='number'?result.pending:null);}).catch(()=>{if(alive)setCount(null);}).finally(()=>{inFlight=false;});};refresh();const timer=setInterval(refresh,5000);return()=>{alive=false;clearInterval(timer);};},[api,state]);
 return <Panel corners={variant==='full'} className={cn('animate-fade-up',className)}><PanelHeader icon={ShieldQuestion} tone="amber" title="Aprovações Pendentes" hint="Propostas aguardando decisão do proprietário" meta={<ToneChip tone="amber">{count===null?'Indisponível':`${count} pendentes`}</ToneChip>} action={<PanelLink to="/approvals">Ver todas<ArrowRight className="size-3"/></PanelLink>}/><div className="p-4 text-sm text-muted-foreground">{count===null?'Não foi possível consultar aprovações.':count?'Abra as aprovações para revisar risco, escopo e dispositivo.':'Nenhuma aprovação pendente.'}</div></Panel>;
};
