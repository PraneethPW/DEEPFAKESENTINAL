import {Activity, Bot, ChartNoAxesCombined, FileScan, Fingerprint, History, Home, LogOut, ScanSearch, Settings, ShieldCheck} from 'lucide-react';
import {NavLink, Outlet} from 'react-router-dom';
import {useAuth} from '../lib/AuthContext';

const links = [
  ['/app', 'Overview', Home], ['/app/analyse', 'New Analysis', ScanSearch], ['/app/history', 'History', History],
  ['/app/evidence', 'Evidence', FileScan], ['/app/analyst', 'AI Analyst', Bot], ['/app/audit', 'Audit', Fingerprint], ['/app/settings', 'Settings', Settings],
] as const;

export function Shell() {
  const {user, logout} = useAuth();
  return <div className="app-shell"><aside>
    <NavLink to="/" className="app-brand"><span className="brand-mark"><ShieldCheck/></span><b>DEEPFAKE <i>SENTINEL</i></b></NavLink>
    <div className="side-status"><Activity/><span><small>FORENSIC ENGINE</small><b>AWAITING MEDIA</b></span></div>
    <nav>{links.map(([to, text, Icon]) => <NavLink key={to} end={to === '/app'} to={to} title={text}><Icon/><span>{text}</span></NavLink>)}</nav>
    <div className="side-footer"><div className="user-chip"><span>{user?.name.slice(0, 2).toUpperCase()}</span><div><b>{user?.name}</b><small>{user?.email}</small></div></div><button onClick={logout} aria-label="Sign out"><LogOut/></button></div>
  </aside><main className="app-main"><div className="command-bar"><span>FORENSIC INTELLIGENCE</span><div><i/> PRIVATE SESSION <ChartNoAxesCombined/></div></div><Outlet/></main>
  <nav className="mobile-dock">{links.slice(0, 5).map(([to, text, Icon]) => <NavLink key={to} end={to === '/app'} to={to} aria-label={text}><Icon/><small>{text === 'New Analysis' ? 'Analyse' : text}</small></NavLink>)}</nav>
  </div>;
}

