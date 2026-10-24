import {useEffect, useState} from 'react';

type Request = <T>(path: string, method?: string, body?: unknown) => Promise<T>;
type JobStatus = {status: string};
const active = (job: JobStatus) => ['queued', 'running', 'cancel_requested'].includes(job.status);

export function useLocalJobHistory<T extends JobStatus>(base: string, request: Request) {
  const [jobs, setJobs] = useState<T[]>([]), [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(true), [error, setError] = useState(false);
  const [revision, setRevision] = useState(0), polling = jobs.some(active);
  useEffect(() => {
    let alive = true, timer: ReturnType<typeof setTimeout> | undefined;
    setReady(false); setLoading(true);
    async function refresh() {
      try {
        const data = await request<{jobs: T[]}>(base + '/jobs');
        if (!alive) return;
        setJobs(data.jobs); setReady(true); setLoading(false); setError(false);
        if (data.jobs.some(active)) timer = setTimeout(refresh, 1500);
      } catch {
        if (alive) {setReady(false); setLoading(false); setError(true);}
      }
    }
    void refresh();
    return () => {alive = false; if (timer) clearTimeout(timer);};
  }, [base, polling, revision]);
  function refreshHistory() {
    setReady(false); setLoading(true); setRevision(value => value + 1);
  }
  return {jobs, setJobs, historyReady: ready, historyLoading: loading, historyError: error, refreshHistory, polling};
}
