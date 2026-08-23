import {useQuery} from '@tanstack/react-query';
import {AnimatePresence, motion} from 'framer-motion';
import {Check, CircleDashed, FileSearch, ShieldAlert} from 'lucide-react';
import {useEffect} from 'react';
import {useLocation, useNavigate, useParams} from 'react-router-dom';
import {api} from '../lib/api';
import {PrivateImage} from '../components/PrivateImage';
import {Glass, Kicker, PageHeader} from '../components/UI';
import type {Analysis} from '../types';

const stages=['CREATED','VALIDATING','QUALITY_CHECK','EXTRACTING_FRAMES','DETECTING_FACES','MODEL_INFERENCE','GENERATING_EVIDENCE','AGGREGATING','COMPLETED'];
const display:Record<string,string>={CREATED:'MEDIA ACQUIRED',VALIDATING:'VALIDATION',QUALITY_CHECK:'QUALITY ANALYSIS',EXTRACTING_FRAMES:'FRAME EXTRACTION',DETECTING_FACES:'FACE DETECTION',MODEL_INFERENCE:'ViT INFERENCE',GENERATING_EVIDENCE:'ATTENTION MAP',AGGREGATING:'SIGNAL AGGREGATION',COMPLETED:'RESULT READY'};

export function Processing(){const {id}=useParams();const navigate=useNavigate();const location=useLocation();const {data}=useQuery({queryKey:['analysis',id],queryFn:()=>api<Analysis>(`/analyses/${id}`),refetchInterval:query=>['COMPLETED','FAILED'].includes(query.state.data?.status||'')?false:1000});
  useEffect(()=>{if(data?.status==='COMPLETED'){const timer=setTimeout(()=>navigate(`/app/analyses/${id}`,{replace:true}),900);return()=>clearTimeout(timer)}},[data?.status,id,navigate]);
  const active=Math.max(0,stages.indexOf(data?.status||'CREATED'));const events=data?.events||[];
  return <div className="page processing-page"><PageHeader kicker="ANALYSIS PIPELINE / PERSISTED EVENTS" title="Extracting forensic signal" description="Every active stage below reflects backend processing—not an estimated percentage."/>
    {location.state?.duplicate&&<div className="duplicate-alert"><FileSearch/>Previously analysed media detected. A new run is continuing with the current model configuration.</div>}
    <div className="processing-layout"><Glass className="pipeline-visual"><div className="processing-media">{data?.has_preview?<PrivateImage path={`/analyses/${id}/assets/preview`} alt="Private media being analysed"/>:<div className="media-placeholder"><CircleDashed/><span>DECODING PRIVATE MEDIA</span></div>}<div className="processing-scan"/><div className="patch-overlay">{Array.from({length:36},(_,i)=><i key={i}/>)}</div></div><Kicker>MODEL SIGNAL REMAINS HIDDEN UNTIL INFERENCE COMPLETES</Kicker><h2>{data?.status==='FAILED'?'ANALYSIS INTERRUPTED':display[data?.status||'CREATED']||data?.status}</h2>{data?.status==='FAILED'&&<div className="model-failure"><ShieldAlert/><span><b>MODEL OFFLINE / ANALYSIS FAILED</b>{data.failure_reason}</span></div>}</Glass>
      <Glass className="stage-list"><div className="module-head"><span>PIPELINE/STAGES</span><b>LIVE</b></div>{stages.filter(stage=>data?.media_type==='IMAGE'?stage!=='EXTRACTING_FRAMES'&&stage!=='AGGREGATING':true).map((stage,index)=>{const position=stages.indexOf(stage);const state=position<active?'done':position===active?'active':'waiting';return <div className={`stage ${state}`} key={stage}><span>{state==='done'?<Check/>:<i/>}</span><div><small>STAGE/{String(index+1).padStart(2,'0')}</small><b>{display[stage]}</b><em>{state==='done'?'Signal persisted':state==='active'?'Processing current media':'Awaiting upstream stage'}</em></div></div>})}</Glass>
      <Glass className="event-stream"><div className="module-head"><span>EVENT/STREAM</span><b>PERSISTED</b></div><AnimatePresence initial={false}>{events.slice(-8).reverse().map(event=><motion.div key={event.id} initial={{opacity:0,y:-8}} animate={{opacity:1,y:0}}><i/><span><b>{event.stage}</b>{event.message}</span><small>{new Date(event.created_at).toLocaleTimeString()}</small></motion.div>)}</AnimatePresence>{!events.length&&<p>No processing event has been persisted yet.</p>}</Glass>
    </div></div>}

