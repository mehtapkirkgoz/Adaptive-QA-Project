import {useEffect, useState} from 'react';
type Job={job_id:string;scope:string;scenario?:string;status:string;result:{status:string}|null};
type Review={contract_fingerprint:string;document_url:string};
type Props={projectId?:string;request:<T>(path:string,method?:string,body?:unknown)=>Promise<T>;
  hasUnsavedChanges:boolean;onProjectCreated:(id:string)=>void};
const names:Record<string,string>={accepted_login:'Correct username and password',
  rejected_login:'Wrong password is rejected',login_then_logout:'Login, logout and protected-page access'};
const running=(job:Job)=>['queued','running','cancel_requested'].includes(job.status);
export function DemoLoginPanel({projectId,request,hasUnsavedChanges,onProjectCreated}:Props){
  const [scenario,setScenario]=useState('accepted_login'),[consent,setConsent]=useState(false);
  const [review,setReview]=useState<Review|null>(null),[jobs,setJobs]=useState<Job[]>([]);
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const base=projectId?`/api/projects/${projectId}/interactive`:null,polling=jobs.some(running);
  useEffect(()=>{setReview(null);setConsent(false);setJobs([]);},[projectId]);
  useEffect(()=>{if(hasUnsavedChanges){setReview(null);setConsent(false);}},[hasUnsavedChanges]);
  useEffect(()=>{if(!base)return;let alive=true,timer:ReturnType<typeof setTimeout>|undefined;
    async function refresh(){try{const data=await request<{jobs:Job[]}>(`${base}/jobs`);
      if(!alive)return;const own=data.jobs.filter(job=>job.scope==='authorized_login_demo');setJobs(own);
      if(own.some(running))timer=setTimeout(refresh,1000);
    }catch{if(alive)setError('Could not refresh demo progress. Reloading will not start another test.');}}
    void refresh();return()=>{alive=false;clearTimeout(timer);};},[base,polling]);
  function reset(){setReview(null);setError('');}
  async function inspect(){setBusy(true);setError('');try{
    if(!projectId){const project=await request<{project_id:string}>('/api/projects','POST',{name:'Local demo review'});
      onProjectCreated(project.project_id);return;}
    setReview(await request<Review>(`${base}/demo-login/review`,'POST',{scenario,authorized_demo:consent}));
    }catch{setError('Could not review the demo. Reopen your local session and save or discard pending settings.');}
    finally{setBusy(false);}}
  async function start(){if(!review||!base)return;setBusy(true);setError('');try{
    const job=await request<Job>(`${base}/demo-login/jobs`,'POST',
      {scenario,authorized_demo:consent,confirmed_contract_fingerprint:review.contract_fingerprint});
    setJobs(previous=>[job,...previous].slice(0,20));setReview(null);setConsent(false);
    }catch{setReview(null);setError('The test was not confirmed. Review it again; no automatic retry will occur.');}
    finally{setBusy(false);}}
  async function cancel(job:Job){setBusy(true);setError('');try{
    const next=await request<Job>(`${base}/jobs/${job.job_id}/cancel`,'POST',{});
    setJobs(previous=>previous.map(item=>item.job_id===next.job_id?next:item));
    }catch{setError('Could not stop the demo. Refresh its status before taking another action.');}
    finally{setBusy(false);}}
  return <section className="card site-check-results demo-login-panel" aria-label="Public login demo">
    <h2>Try a real login test</h2><p>Use The Internet’s public test account to check sign-in and sign-out. This runs separately from your saved website and keeps its settings unchanged.</p>
    <label>Demo scenario<select aria-label="Demo scenario" value={scenario} disabled={busy||polling} onChange={event=>{setScenario(event.target.value);reset();}}>
      {Object.entries(names).map(([value,name])=><option key={value} value={value}>{name}</option>)}</select></label>
    <label className="demo-login-consent"><input type="checkbox" checked={consent} disabled={busy||polling||hasUnsavedChanges}
      onChange={event=>{setConsent(event.target.checked);reset();}}/>Allow one sign-in attempt on this public demo using its published test account.</label>
    {hasUnsavedChanges&&<p>Save or discard pending Test options before reviewing this demo.</p>}
    <button disabled={!consent||busy||polling||hasUnsavedChanges} onClick={()=>void inspect()}>{projectId?'Review demo test':'Set up local demo history'}</button>
    {review&&<div role="status"><p>{names[scenario]} — {review.document_url}. One sign-in attempt; isolated session; no automatic retry.</p>
      <button disabled={!consent||busy||polling||hasUnsavedChanges} onClick={()=>void start()}>Run demo test</button></div>}
    {error&&<p role="alert">{error}</p>}
    {jobs.length>0&&<div aria-label="Demo test results">{jobs.map(job=><article key={job.job_id}>
      <strong>{names[job.scenario??'']??'Demo login'}</strong><p>{running(job)?(job.status==='cancel_requested'?'Stopping…':'Demo test in progress…'):
        job.result?.status==='passed'?'Passed':job.result?.status==='failed'?'Failed':job.status==='cancelled'||job.result?.status==='cancelled'?'Stopped':'Not evaluated'}</p>
      {job.result?.status==='passed'&&<p>The expected response, destination and visible page state were verified.</p>}
      {job.result?.status==='error'&&<p>The isolated session could not be verified. This is a technical outcome, not a failed website assertion.</p>}
      {running(job)&&<button disabled={busy||job.status==='cancel_requested'} onClick={()=>void cancel(job)}>Stop demo test</button>}
    </article>)}</div>}
  </section>;
}
