"""Explicit one-shot credentials held only for the newly admitted owned job."""
from threading import Lock, Thread

from adaptive_qa.interactive_queue import OwnedInteractiveQueue
from adaptive_qa.interactive_probe import InteractiveProbeResult
from adaptive_qa.models import TestStatus
from adaptive_qa.worker_lock import worker_lock


class WebsiteLoginService:
    def __init__(self,projects):
        self.queue=OwnedInteractiveQueue(projects)
        self.lock=Lock(); self.thread=None; self.current=None; self.closed=False

    def submit(self,actor,review,*,identifier,password,confirmed_fingerprint,authorized):
        for value in (identifier,password):
            if not isinstance(value,str) or not 1<=len(value)<=512 or any(ord(c)<32 or ord(c)==127 for c in value):
                raise ValueError('Enter bounded disposable test credentials.')
        with self.lock:
            if self.closed or self.thread and self.thread.is_alive(): raise ValueError('Wait for the current login test.')
            job=self.queue.submit_website_login(actor,review,confirmed_fingerprint=confirmed_fingerprint,authorized=authorized)
            self.current=(actor,review.project_id,job['job_id'])
            self.thread=Thread(target=self._work,args=(job['job_id'],identifier,password),daemon=True,name='adaptive-website-login')
            try: self.thread.start()
            except Exception:
                self.queue.cancel(*self.current)
                raise ValueError('The login worker could not start.') from None
            return job

    def _work(self,job_id,identifier,password):
        work=None
        try:
            with worker_lock(self.queue.projects.database):
                work=self.queue.claim_next(job_id=job_id)
                if work is None:
                    self.queue.cancel(*self.current)
                    return
                from adaptive_qa.website_login_process import run_login
                result=run_login(work.review,identifier,password,should_cancel=lambda:self.queue.cancellation_requested(work))
                self.queue.finish(work,result)
        except Exception:
            if work is not None:
                try: self.queue.finish(work,InteractiveProbeResult(TestStatus.ERROR,'Login worker could not complete.',None))
                except (ValueError,LookupError): pass
            elif self.current:
                try: self.queue.cancel(*self.current)
                except (ValueError,LookupError): pass
        finally:
            identifier=password=None

    def shutdown(self):
        with self.lock:
            self.closed=True
            if self.current and self.thread and self.thread.is_alive():
                try:self.queue.cancel(*self.current)
                except (ValueError,LookupError):pass
            thread=self.thread
        if thread:thread.join(timeout=15)
