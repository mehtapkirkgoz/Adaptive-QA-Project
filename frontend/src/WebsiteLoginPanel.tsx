import {useEffect, useState} from 'react';
type Detection={status:string;candidate?:{document_url:string;identifier_kind:string}|null};
type Review={contract_fingerprint:string;document_url:string;identifier_kind:string};
type Row={case_id:string;status:string;reason_code:string};
type Job={job_id:string;check_id?:string;scope:string;status:string;result?:{status:string;attempted_submissions:number|null;cases?:Row[]}|null};
type Props={checkId:string;projectId:string;login?:Detection;disabled:boolean;request:<T>(path:string,method?:string,body?:unknown)=>Promise<T>};
const names:Record<string,string>={'LOGIN-FORM':'Login form and HTTPS destination','LOGIN-IDENTIFIER':'Identifier is marked required',
  'LOGIN-PASSWORD':'Password is marked required','LOGIN-ACCOUNT':'Test account signs in','LOGIN-LOGOUT':'Sign out and check protected access'};
const reasons:Record<string,string>={standard_form:'A unique standard HTML login form and same-origin HTTPS action were verified.',
  required_declared:'The field declares the native required constraint. No empty form was submitted.',
  required_missing:'No native required constraint was declared. Server-side empty-value handling was not tested.',
  authenticated_markers:'The isolated session held cookies, left the login page, removed the password form and exposed a same-origin logout link.',
  outcome_uncertain:'The response did not provide enough evidence of authentication. HTTP 200 alone is not a pass. No retry was made.',
  credentials_rejected:'The site returned the password form with an explicit authentication-error message for the supplied account. No other password was tried.',
  unsupported_form:'The live form changed or needs unsupported JavaScript, SSO, CAPTCHA, multiple steps or controls. Credentials were not submitted.',
  logout_verified:'After sign-out, both the returned page and the previously authenticated URL presented the login form.',
  logout_unverified:'Sign-out was requested, but loss of protected access could not be verified.',
  logout_unavailable:'No supported sign-out flow was available.',transport_error:'A network, TLS or response error prevented verification.'};
const active=(j:Job)=>['queued','running','cancel_requested'].includes(j.status);
export function WebsiteLoginPanel({checkId,projectId,login,disabled,request}:Props){
  const [review,setReview]=useState<Review|null>(null),[identifier,setIdentifier]=useState(''),[password,setPassword]=useState('');
  const [consent,setConsent]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[jobs,setJobs]=useState<Job[]>([]);
  const base=`/api/projects/${projectId}/interactive`,polling=jobs.some(active);
  useEffect(()=>{let alive=true,timer:ReturnType<typeof setTimeout>;async function refresh(){try{
    const data=await request<{jobs:Job[]}>(`${base}/jobs`);
    if(alive){const current=data.jobs.filter(j=>j.scope==='website_login'&&j.check_id===checkId);setJobs(current);if(current.some(active))timer=setTimeout(refresh,1000);}
  }catch{if(alive)setError('Could not load login history. Refreshing never retries a sign-in.');}}
    void refresh();return()=>{alive=false;clearTimeout(timer);};},[base,checkId,request,polling]);
  async function prepare(){setBusy(true);setError('');try{
    setReview(await request<Review>(`${base}/website-login/review`,'POST',{check_id:checkId}));
  }catch{setError('The inspected website or saved settings changed. Run a new website check before entering credentials.');}finally{setBusy(false);}}
  async function run(){if(!review)return;setBusy(true);setError('');
    const input={check_id:checkId,identifier,password,authorized:consent,confirmed_contract_fingerprint:review.contract_fingerprint};
    setPassword('');setIdentifier('');setConsent(false);setReview(null);
    try{const job=await request<Job>(`${base}/website-login/jobs`,'POST',input);setJobs(old=>[job,...old]);}
    catch{setError('The login test could not be started or confirmed. Check history before trying again; there is no automatic retry.');}
    finally{input.password='';input.identifier='';setBusy(false);}}
  async function stop(job:Job){setBusy(true);try{const next=await request<Job>(`${base}/jobs/${job.job_id}/cancel`,'POST',{});setJobs(old=>old.map(j=>j.job_id===next.job_id?next:j));}
    catch{setError('Could not request a stop. Refresh progress before taking another action.');}finally{setBusy(false);}}
  return <section className="card site-check-results" aria-label="Website login tests"><h2>Login tests</h2>
    {!login?<p>Run a new website check to inspect this site for a login form.</p>:login.status!=='found'?<p>{login.status==='ambiguous'
      ?'Several possible login forms were found. Open the exact login page and check that URL first.'
      :'No supported login form was found on the inspected pages. This does not prove the whole website has no login. You can check its exact login URL.'}</p>:<>
      <p>A possible {login.candidate?.identifier_kind==='email'?'email':'username'} and password login was found at {login.candidate?.document_url}.</p>
      <p>Use a disposable test account that already exists on this website. We do not read the website’s database or create an account.</p>
      {!review&&<button disabled={busy||polling||disabled} onClick={()=>void prepare()}>Add a test account</button>}
      {review&&<form autoComplete="off" onSubmit={event=>{event.preventDefault();void run();}}>
        <label htmlFor="website-login-identifier">{review.identifier_kind==='email'?'Test account email':'Test account username'}</label>
        <input id="website-login-identifier" type={review.identifier_kind==='email'?'email':'text'} maxLength={512} required autoComplete="off"
          value={identifier} disabled={busy||polling||disabled} onChange={e=>setIdentifier(e.target.value)}/>
        <label htmlFor="website-login-password">Test account password</label>
        <input id="website-login-password" type="password" maxLength={512} required autoComplete="new-password"
          value={password} disabled={busy||polling||disabled} onChange={e=>setPassword(e.target.value)}/>
        <p className="hint">Credentials are used for this run only and are not saved in project settings, reports or files. One sign-in attempt; no password guessing. Standard same-origin HTML forms only; CAPTCHA, MFA, SSO and JavaScript-only login are not supported.</p>
        <label><input type="checkbox" checked={consent} disabled={busy||polling||disabled} onChange={e=>setConsent(e.target.checked)}/>
          I am authorized to use this test account for one sign-in and, when supported, sign-out on this website.</label>
        <button type="submit" className="primary" disabled={!consent||!identifier||!password||busy||polling||disabled}>Run login tests</button>
        <button type="button" onClick={()=>{setPassword('');setIdentifier('');setConsent(false);setReview(null);}}>Discard account details</button>
      </form>}</>}
    {error&&<p role="alert">{error}</p>}
    {jobs.map(job=><article key={job.job_id}><h3>{active(job)?'Login test in progress…':job.status==='cancelled'?'Stopped':job.result?.status==='passed'?'Login checks passed':'Login check results'}</h3>
      {active(job)&&<button disabled={busy||job.status==='cancel_requested'} onClick={()=>void stop(job)}>Stop login test</button>}
      {!active(job)&&!job.result?.cases&&<p>A reliable complete result was not recorded ({job.result?.status??job.status}). No automatic retry was made.</p>}
      {job.result?.cases?.map(row=><div key={row.case_id}><strong>{names[row.case_id]} · {row.status==='not_run'?'Not evaluated':row.status}</strong><p>{reasons[row.reason_code]??'A reliable verdict was not available.'}</p></div>)}
    </article>)}
  </section>;
}
