"""One explicit managed demo job per runtime; never consume pre-existing queue work."""
from threading import Lock, Thread

from adaptive_qa.interactive_queue import OwnedInteractiveQueue, process_owned_interactive_once


class _DemoQueue(OwnedInteractiveQueue):
    def claim_next(self):
        return super().claim_next(job_id=self.only_id)


class DemoLoginService:
    def __init__(self, projects):
        self.queue = _DemoQueue(projects)
        self.lock, self.thread = Lock(), None
        self.current = None
        self.closed = False

    def submit(self, actor, review, *, confirmed_fingerprint):
        with self.lock:
            if self.closed or (self.thread is not None and self.thread.is_alive()):
                raise ValueError('Wait for the current demo scenario to finish.')
            job = self.queue.submit_demo(actor, review, confirmed_fingerprint=confirmed_fingerprint)
            self.queue.only_id = job['job_id']
            self.current = (actor, review.project_id, job['job_id'])
            self.thread = Thread(target=self._work, daemon=True)
            try:self.thread.start()
            except Exception:
                self.queue.cancel(*self.current)
                raise ValueError('The demo worker could not start.') from None
            return job

    def _work(self):
        try:process_owned_interactive_once(self.queue)
        except Exception:
            # No retry or polling of unrelated pending work after a failed start.
            if self.current:
                try:self.queue.cancel(*self.current)
                except (ValueError, LookupError):pass

    def shutdown(self):
        with self.lock:
            self.closed = True
            if self.current and self.thread is not None and self.thread.is_alive():
                try:self.queue.cancel(*self.current)
                except (ValueError, LookupError):pass
            thread = self.thread
        if thread is not None:thread.join(timeout=15)
