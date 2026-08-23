import {Navigate, Route, Routes} from 'react-router-dom';
import {useAuth} from './lib/AuthContext';
import {Shell} from './components/Shell';
import {Loading} from './components/UI';
import {Landing} from './pages/Landing';
import {AuthPage} from './pages/AuthPage';
import {Dashboard} from './pages/Dashboard';
import {NewAnalysis} from './pages/NewAnalysis';
import {Processing} from './pages/Processing';
import {ResultWorkspace} from './pages/ResultWorkspace';
import {HistoryPage, EvidencePage, AuditPage, AnalystPage, SettingsPage} from './pages/LibraryPages';

function Protected() {
  const {user, loading} = useAuth();
  if (loading) return <Loading label="VERIFYING PRIVATE SESSION"/>;
  return user ? <Shell/> : <Navigate to="/login" replace/>;
}

export function App() {
  return <Routes>
    <Route path="/" element={<Landing/>}/><Route path="/login" element={<AuthPage/>}/><Route path="/register" element={<AuthPage register/>}/>
    <Route path="/app" element={<Protected/>}>
      <Route index element={<Dashboard/>}/><Route path="analyse" element={<NewAnalysis/>}/><Route path="analyses/:id/processing" element={<Processing/>}/><Route path="analyses/:id" element={<ResultWorkspace/>}/>
      <Route path="history" element={<HistoryPage/>}/><Route path="evidence" element={<EvidencePage/>}/><Route path="analyst" element={<AnalystPage/>}/><Route path="audit" element={<AuditPage/>}/><Route path="settings" element={<SettingsPage/>}/>
    </Route>
    <Route path="*" element={<Navigate to="/" replace/>}/>
  </Routes>;
}

