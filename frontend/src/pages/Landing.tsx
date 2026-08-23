import {motion, useScroll, useTransform} from 'framer-motion';
import {ArrowDown, ArrowRight, BrainCircuit, CheckCircle2, Eye, FileVideo2, Fingerprint, Gauge, ScanFace, ShieldCheck, Sparkles, Workflow} from 'lucide-react';
import {Link} from 'react-router-dom';
import {HeroScene} from '../components/HeroScene';
import {Kicker} from '../components/UI';

const stages = ['INPUT', 'VALIDATE', 'SAMPLE', 'FACE', 'ViT', 'EVIDENCE', 'REVIEW'];
const features = [
  [ScanFace, 'Image screening', 'Face-aware crops plus honest full-frame fallback.'],
  [FileVideo2, 'Video frame analysis', 'Representative frames and deterministic robust aggregation.'],
  [BrainCircuit, 'Vision Transformer', 'A configurable detector produces the signal—not a language model.'],
  [Eye, 'Attention evidence', 'Real attention rollout reveals influential regions for inspection.'],
  [Gauge, 'Quality context', 'Blur, brightness, contrast, resolution, and face availability.'],
  [Fingerprint, 'Traceable review', 'Model output, human decisions, notes, and audit history remain distinct.'],
] as const;

export function Landing() {
  const {scrollYProgress} = useScroll();
  const scannerY = useTransform(scrollYProgress, [0, .25], ['0%', '420%']);
  return <main className="landing">
    <nav className="landing-nav"><Link to="/" className="brand"><span><ShieldCheck/></span>DEEPFAKE <i>SENTINEL</i></Link><div><a href="#technology">Technology</a><a href="#workflow">Workflow</a><a href="#evidence">Evidence</a><Link to="/login">Sign in</Link><Link className="nav-cta" to="/register">Analyse media <ArrowRight/></Link></div></nav>
    <section className="hero">
      <motion.div className="hero-copy" initial={{opacity: 0, x: -30}} animate={{opacity: 1, x: 0}} transition={{duration: .65}}>
        <Kicker>AI SECURITY / VISUAL FORENSICS <b>● SYSTEM ONLINE</b></Kicker>
        <h1>DETECT<br/>MANIPULATION.<br/><em>SEE THE EVIDENCE.</em></h1>
        <p>Screen suspicious images and video with a Vision Transformer, inspect the model's visual evidence, and keep the final decision human.</p>
        <div className="hero-actions"><Link className="primary-button" to="/register">ENTER FORENSICS <ArrowRight/></Link><a className="ghost-button" href="#workflow">EXPLORE ENGINE <ArrowDown/></a></div>
        <div className="hero-rail"><span>PRIVATE MEDIA</span><span>REAL MODEL SIGNAL</span><span>HUMAN CONTROL</span></div>
      </motion.div>
      <motion.div className="hero-engine" initial={{opacity: 0, scale: .94}} animate={{opacity: 1, scale: 1}} transition={{delay: .15, duration: .8}}>
        <div className="illustrative">INTERACTIVE DEMO / ILLUSTRATIVE SIGNAL</div><HeroScene/>
        <motion.div className="scan-line" style={{top: scannerY}}/>
        <div className="face-brackets"><i/><i/><i/><i/></div>
        <div className="hud hud-a"><small>MODEL</small><b>ViT / ACTIVE</b><span>ATTENTION READY</span></div>
        <div className="hud hud-b"><small>INPUT</small><b>IMAGE / READY</b><span>QUALITY CHECK</span></div>
        <div className="hud hud-c"><small>DECISION</small><b>HUMAN / FINAL</b><span>AUDIT ENABLED</span></div>
      </motion.div>
    </section>

    <section className="landing-telemetry" id="technology"><header><div><Kicker>DEMO TELEMETRY / ARCHITECTURE VIEW</Kicker><h2>The media signal, made inspectable.</h2></div><span>ILLUSTRATIVE VALUES</span></header><div className="telemetry-grid">
      {[['VISUAL QUALITY','GOOD','82'],['FACE SIGNAL','ACQUIRED','96'],['MODEL OUTPUT','INCONCLUSIVE','52'],['EVIDENCE MAP','READY','74']].map(([title,value,score], index) => <article key={title}><small>ENG/0{index+1}</small><strong>{score}<sup>%</sup></strong><b>{title}</b><span>{value}</span><div className="bars">{[.25,.48,.36,.65,.51,.82,.72].map((height, i)=><i key={i} style={{height:`${height*100}%`}}/>)}</div></article>)}
    </div></section>

    <section className="pipeline" id="workflow"><Kicker>INPUT → MODEL SIGNAL → VISUAL EVIDENCE → HUMAN DECISION</Kicker><h2>One accountable path through the engine.</h2><div className="pipeline-track">{stages.map((stage,index)=><article key={stage}><span>{String(index+1).padStart(2,'0')}</span><i/><b>{stage}</b>{index < stages.length-1 && <em/>}</article>)}</div></section>

    <section className="evidence-story" id="evidence"><div><Kicker>EXPLAINABLE AI / ATTENTION ROLLOUT</Kicker><h2>A SCORE<br/><em>ISN'T ENOUGH.</em></h2><p>Highlighted regions show where the configured model concentrated its attention. They support inspection; they do not prove that an exact pixel was forged.</p><div className="responsibility"><ShieldCheck/><span><b>DECISION SUPPORT</b>Human verification remains required.</span></div></div><div className="evidence-triptych">
      {['ORIGINAL MEDIA','MODEL ATTENTION','EVIDENCE OVERLAY'].map((title,index)=><article key={title} className={`demo-face state-${index}`}><small>{title}</small><div className="portrait-grid"><ScanFace/><span/><i/></div><b>{index === 0 ? 'SOURCE' : index === 1 ? 'INFLUENCE' : 'REVIEW'}</b></article>)}
    </div></section>

    <section className="feature-section"><header><Kicker>FORENSIC CAPABILITIES / CONTROLLED PIPELINE</Kicker><h2>Built for review, not spectacle alone.</h2></header><div className="feature-bento">{features.map(([Icon,title,copy], index)=><motion.article key={title} whileHover={{y:-4}} className={index === 2 || index === 5 ? 'wide':''}><Icon/><small>SYS/{String(index+1).padStart(2,'0')}</small><h3>{title}</h3><p>{copy}</p><span><i/></span></motion.article>)}</div></section>

    <section className="human-section"><div className="decision-orbit"><div><Sparkles/><b>MODEL<br/>SIGNAL</b></div>{['CONFIRM AUTHENTIC','CONFIRM MANIPULATED','MARK INCONCLUSIVE','REVIEW FURTHER'].map((item,index)=><span key={item} style={{'--i': index} as React.CSSProperties}><CheckCircle2/>{item}</span>)}</div><div><Kicker>HUMAN-IN-THE-LOOP / AUDITABLE</Kicker><h2>AI FLAGS.<br/><em>HUMANS VERIFY.</em></h2><p>The original model output never changes. Review decisions are stored independently with notes, timestamps, and an audit trail.</p></div></section>
    <section className="final-cta"><Workflow/><Kicker>PRIVATE MEDIA / EXPLAINABLE SIGNAL / TRACEABLE REVIEW</Kicker><h2>TURN SUSPICIOUS MEDIA<br/><em>INTO REVIEWABLE EVIDENCE.</em></h2><Link className="primary-button" to="/register">START ANALYSIS <ArrowRight/></Link></section>
    <footer><span>DEEPFAKE SENTINEL / v1.0</span><p>Screening support—not a substitute for expert forensic verification.</p><Link to="/login">Enter command center</Link></footer>
  </main>;
}

