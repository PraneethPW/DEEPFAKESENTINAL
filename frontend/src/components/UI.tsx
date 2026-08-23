import type {ReactNode} from 'react';
import {Activity, ShieldCheck} from 'lucide-react';
import {label} from '../lib/format';

export function Glass({children, className = ''}: {children: ReactNode; className?: string}) {return <section className={`glass ${className}`}>{children}</section>}
export function Kicker({children}: {children: ReactNode}) {return <p className="kicker">{children}</p>}
export function PageHeader({kicker, title, description, action}: {kicker: string; title: string; description?: string; action?: ReactNode}) {
  return <header className="page-header"><div><Kicker>{kicker}</Kicker><h1>{title}</h1>{description && <p>{description}</p>}</div>{action}</header>;
}
export function SignalBadge({value}: {value?: string}) {
  const kind = value === 'LIKELY_MANIPULATED' || value === 'FAILED' ? 'risk' : value === 'LIKELY_AUTHENTIC' || value === 'COMPLETED' ? 'safe' : 'warn';
  return <span className={`signal-badge ${kind}`}><i/>{label(value)}</span>;
}
export function EmptyState({title, copy, action}: {title: string; copy: string; action?: ReactNode}) {
  return <Glass className="empty-state"><div className="scanner-orb"><ShieldCheck/><i/></div><Kicker>ZERO IS A VALID STATE / NO SYNTHETIC DATA</Kicker><h2>{title}</h2><p>{copy}</p>{action}</Glass>;
}
export function Loading({label = 'ACQUIRING LIVE DATA'}: {label?: string}) {return <div className="loading-state"><div className="loading-frame"><Activity/><i/></div><span>{label}</span></div>}

