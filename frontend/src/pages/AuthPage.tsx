import {zodResolver} from '@hookform/resolvers/zod';
import {motion} from 'framer-motion';
import {ArrowLeft, ArrowRight, CheckCircle2, Eye, EyeOff, ScanFace, ShieldCheck} from 'lucide-react';
import {useState} from 'react';
import {useForm} from 'react-hook-form';
import {Link, Navigate, useNavigate} from 'react-router-dom';
import {z} from 'zod';
import {api} from '../lib/api';
import {useAuth} from '../lib/AuthContext';
import type {User} from '../types';
import {Kicker} from '../components/UI';

const schema = z.object({name: z.string().min(2).optional(), email: z.email(), password: z.string().min(8)});
type FormData = z.infer<typeof schema>;

export function AuthPage({register = false}: {register?: boolean}) {
  const {user, authenticate} = useAuth(); const navigate = useNavigate(); const [show,setShow] = useState(false); const [serverError,setServerError] = useState('');
  const {register: field, handleSubmit, formState: {errors, isSubmitting}} = useForm<FormData>({resolver: zodResolver(schema), defaultValues:{name:'',email:'',password:''}});
  if (user) return <Navigate to="/app" replace/>;
  const submit = handleSubmit(async (values) => {
    setServerError('');
    try {const result = await api<{access_token:string; user:User}>(`/auth/${register?'register':'login'}`, {method:'POST', body:JSON.stringify(register?values:{email:values.email,password:values.password})}); authenticate(result.access_token,result.user); navigate('/app');}
    catch(error){setServerError(error instanceof Error?error.message:'Authentication failed');}
  });
  return <main className="auth-page"><section className="auth-engine"><Link to="/" className="back-link"><ArrowLeft/> Back to Sentinel</Link><div className="auth-visual"><div className="auth-rings"><i/><i/><i/><ScanFace/></div><Kicker>PRIVATE FORENSIC WORKSPACE</Kicker><h1>Media enters.<br/><em>Evidence leaves.</em></h1><div className="auth-telemetry">{['INPUT VALIDATION / ACTIVE','ViT ENGINE / ON DEMAND','PRIVATE MEDIA / PROTECTED','HUMAN REVIEW / REQUIRED'].map(item=><span key={item}><CheckCircle2/>{item}</span>)}</div></div></section>
    <section className="auth-panel"><motion.div initial={{opacity:0,y:20}} animate={{opacity:1,y:0}} className="auth-card"><span className="auth-icon"><ShieldCheck/></span><Kicker>FORENSIC INTELLIGENCE / SECURE ACCESS</Kicker><h2>{register?'Create your workspace':'Enter command center'}</h2><p>{register?'Start an evidence-driven media review workspace.':'Your analyses, evidence, and decisions stay attached to your account.'}</p><form onSubmit={submit}>
      {register&&<label>Reviewer name<input {...field('name')} autoComplete="name" placeholder="Your name"/>{errors.name&&<small>{errors.name.message}</small>}</label>}
      <label>Email address<input {...field('email')} autoComplete="email" placeholder="reviewer@example.com"/>{errors.email&&<small>{errors.email.message}</small>}</label>
      <label>Password<div className="password-field"><input {...field('password')} type={show?'text':'password'} autoComplete={register?'new-password':'current-password'} placeholder="8+ characters"/><button type="button" onClick={()=>setShow(!show)} aria-label={show?'Hide password':'Show password'}>{show?<EyeOff/>:<Eye/>}</button></div>{errors.password&&<small>{errors.password.message}</small>}</label>
      {serverError&&<div className="form-error">{serverError}</div>}<button className="primary-button" disabled={isSubmitting}>{isSubmitting?'VERIFYING…':register?'CREATE WORKSPACE':'SIGN IN'}<ArrowRight/></button>
    </form><p className="auth-switch">{register?'Already registered?':'New to Sentinel?'} <Link to={register?'/login':'/register'}>{register?'Sign in':'Create an account'}</Link></p><small className="auth-disclosure">Model predictions support human verification and are not proof of authenticity.</small></motion.div></section></main>;
}

