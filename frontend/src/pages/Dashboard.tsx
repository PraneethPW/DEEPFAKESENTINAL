import {useQuery} from '@tanstack/react-query';
import {Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis} from 'recharts';
import {ArrowRight, CheckCircle2, FileImage, FileVideo2, ScanSearch, ShieldAlert, Sparkles, TriangleAlert} from 'lucide-react';
import {Link} from 'react-router-dom';
import {api} from '../lib/api';
import {dateTime, label, percent} from '../lib/format';
import {EmptyState, Glass, Loading, PageHeader, SignalBadge} from '../components/UI';

type DashboardData = {totals: Record<string,number>; classification_distribution:{name:string;value:number}[]; media_distribution:{name:string;value:number}[]; quality_distribution:{name:string;value:number}[]; review_distribution:{name:string;value:number}[]; activity:{date:string;value:number}[]; recent:any[]; audit:any[]};
const colors: Record<string,string> = {LIKELY_AUTHENTIC:'#34d399',INCONCLUSIVE:'#fbbf24',LIKELY_MANIPULATED:'#fb7185',IMAGE:'#a855f7',VIDEO:'#22d3ee',GOOD:'#34d399',LIMITED:'#fbbf24',POOR:'#fb7185'};

export function Dashboard() {
  const {data,isLoading,error} = useQuery({queryKey:['dashboard'], queryFn:()=>api<DashboardData>('/dashboard')});
  if(isLoading) return <Loading label="LOADING LIVE FORENSIC TELEMETRY"/>;
  if(error||!data) return <EmptyState title="Dashboard unavailable" copy="The live database could not be reached. No placeholder metrics were substituted."/>;
  const metrics = [
    ['TOTAL ANALYSES',data.totals.total,ScanSearch],['IMAGE ANALYSES',data.totals.images,FileImage],['VIDEO ANALYSES',data.totals.videos,FileVideo2],
    ['LIKELY MANIPULATED',data.totals.likely_manipulated,ShieldAlert],['INCONCLUSIVE',data.totals.inconclusive,TriangleAlert],['HUMAN REVIEWED',data.totals.human_reviewed,CheckCircle2],
  ] as const;
  return <div className="page dashboard-page"><PageHeader kicker="FORENSIC INTELLIGENCE / LIVE DATABASE" title="Media Review Command Center" description="Every metric below is derived from your persisted analysis records." action={<Link to="/app/analyse" className="primary-button">NEW ANALYSIS <ArrowRight/></Link>}/>
    <div className="metric-grid">{metrics.map(([name,value,Icon],index)=><Glass key={name} className="metric-card"><Icon/><small>SYS/{String(index+1).padStart(2,'0')}</small><strong>{value}</strong><span>{name}</span><i/></Glass>)}</div>
    {!data.totals.total ? <EmptyState title="No media analysed" copy="Submit an image or video to start an evidence-driven authenticity review." action={<Link to="/app/analyse" className="primary-button">START FIRST ANALYSIS <ArrowRight/></Link>}/> : <>
      <div className="dashboard-charts"><Glass className="chart-card donut-card"><div className="module-head"><span>MODEL/CLASSIFICATION</span><b>REAL RECORDS</b></div><h2>Classification distribution</h2><ResponsiveContainer width="100%" height={240}><PieChart><Pie data={data.classification_distribution} dataKey="value" nameKey="name" innerRadius={65} outerRadius={91} paddingAngle={4}>{data.classification_distribution.map(item=><Cell key={item.name} fill={colors[item.name]}/>)}</Pie><Tooltip contentStyle={{background:'#0d0618',border:'1px solid #6d28d9'}} formatter={(value,name)=>[value,label(String(name))]}/></PieChart></ResponsiveContainer><div className="chart-legend">{data.classification_distribution.map(item=><span key={item.name}><i style={{background:colors[item.name]}}/>{label(item.name)}<b>{item.value}</b></span>)}</div></Glass>
        <Glass className="chart-card trend-card"><div className="module-head"><span>ACTIVITY/14D</span><b>DATABASE</b></div><h2>Analysis activity</h2><ResponsiveContainer width="100%" height={250}><AreaChart data={data.activity}><defs><linearGradient id="activityFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#a855f7" stopOpacity={.72}/><stop offset="1" stopColor="#a855f7" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#ffffff0a" vertical={false}/><XAxis dataKey="date" tickFormatter={value=>value.slice(5)} stroke="#665671" tickLine={false}/><YAxis allowDecimals={false} stroke="#665671" tickLine={false}/><Tooltip contentStyle={{background:'#0d0618',border:'1px solid #6d28d9'}}/><Area type="monotone" dataKey="value" stroke="#c084fc" strokeWidth={2} fill="url(#activityFill)"/></AreaChart></ResponsiveContainer></Glass>
        <Glass className="chart-card mini-distributions"><div className="module-head"><span>SIGNAL/DISTRIBUTIONS</span><b>LIVE</b></div><h2>Media & quality</h2>{[...data.media_distribution,...data.quality_distribution].map(item=><div className="distribution-row" key={item.name}><span><i style={{background:colors[item.name]}}/>{label(item.name)}</span><b>{item.value}</b><em style={{width:`${data.totals.total?item.value/data.totals.total*100:0}%`,background:colors[item.name]}}/></div>)}</Glass>
      </div>
      <Glass className="recent-table"><div className="module-head"><span>RECENT/ANALYSES</span><Link to="/app/history">VIEW HISTORY <ArrowRight/></Link></div><div className="table-head"><span>MEDIA</span><span>MODEL SIGNAL</span><span>PROBABILITY</span><span>QUALITY</span><span>TIME</span></div>{data.recent.map(item=><Link className="table-row" key={item.id} to={`/app/analyses/${item.id}`}><span className="media-cell">{item.media_type==='IMAGE'?<FileImage/>:<FileVideo2/>}<b>{item.filename}</b></span><span><SignalBadge value={item.classification||item.status}/></span><strong>{percent(item.fake_probability)}</strong><span>{label(item.quality_status)}</span><small>{dateTime(item.created_at)}</small></Link>)}</Glass>
    </>}
    <div className="system-rail"><span><i/><b>DATABASE</b>CONNECTED</span><span><i/><b>MODEL</b>ON DEMAND</span><span><i/><b>RAW MEDIA</b>PRIVATE</span><span><Sparkles/><b>AI EXPLANATION</b>GROUNDED</span></div>
  </div>;
}

