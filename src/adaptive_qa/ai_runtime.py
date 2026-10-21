"""Bounded offline AI adapter and session admission; no remote model calls."""

from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Lock
from time import monotonic

from adaptive_qa.ai_models import AiAdvice, AiBudget
from adaptive_qa.ai_validation import decode_ai_advice, reduce_ai_input
from adaptive_qa.browser_process import _terminate_process_tree


@dataclass(frozen=True)
class OfflineAiProvider:
    """Scripted transport for boundary testing, not an intelligent model."""
    response: str = field(repr=False)
    delay_seconds: float = 0
    fail: bool = False

    def __post_init__(self):
        if not isinstance(self.response, str) or len(self.response.encode('utf-8')) > 32768:
            raise ValueError('Scripted response must be bounded UTF-8 text.')
        if (type(self.delay_seconds) not in (int, float) or not math.isfinite(self.delay_seconds)
                or not 0 <= self.delay_seconds <= 60 or type(self.fail) is not bool):
            raise ValueError('Scripted provider behavior must be bounded and typed.')


@dataclass(frozen=True)
class AiOutcome:
    status: str
    reason: str
    advice: AiAdvice | None = None


class AiSession:
    """Shared, thread-safe run budget; attempts consume slots even on failure."""
    def __init__(self, budget: AiBudget):
        if not isinstance(budget, AiBudget):
            raise ValueError('budget must be an AiBudget.')
        self.budget = budget
        self._requests = 0
        self._reserved_cost = 0
        self._deadline = monotonic() + budget.timeout_seconds
        self._lock = Lock()

    def _reserve(self, upper_cost):
        if type(upper_cost) is not int or upper_cost < 0:
            raise ValueError('Reserved AI cost must be a nonnegative integer.')
        with self._lock:
            if (self._requests >= self.budget.max_requests or monotonic() >= self._deadline
                    or self._reserved_cost + upper_cost > self.budget.max_cost_microusd):
                return False
            self._requests += 1
            self._reserved_cost += upper_cost
            return True

    def suggest(self, page, logical_names, provider: OfflineAiProvider | None):
        if provider is None:
            return AiOutcome('unavailable', 'AI provider is disabled; deterministic behavior remains available.')
        if not isinstance(provider, OfflineAiProvider):
            raise ValueError('Only the registered offline provider is currently supported.')
        if (not isinstance(logical_names, tuple) or len(logical_names) > 50
                or any(not isinstance(name, str) for name in logical_names)
                or len(set(logical_names)) != len(logical_names)):
            raise ValueError('Logical names must be a bounded unique tuple.')
        try:
            reduced = reduce_ai_input(page, self.budget)
        except ValueError:
            return AiOutcome('rejected', 'AI input did not satisfy the reduction budget.')
        # Offline transport is guaranteed free. Future remote adapters must
        # supply a trusted worst-case charge before admission, never model claims.
        if not self._reserve(0):
            return AiOutcome('budget_exhausted', 'AI session request, cost, or time budget is exhausted.')
        process = None
        try:
            with TemporaryDirectory(prefix='adaptive-qa-ai-') as temporary:
                source = Path(temporary) / 'private.json'
                destination = Path(temporary) / 'response.json'
                source.write_text(json.dumps({'response': provider.response,
                    'delay': provider.delay_seconds, 'fail': provider.fail}), encoding='utf-8')
                options = {'start_new_session': True} if os.name != 'nt' else {
                    'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
                process = subprocess.Popen([sys.executable, '-m', 'adaptive_qa.ai_runtime',
                    str(source), str(destination)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
                try:
                    process.wait(timeout=max(0.001, self._deadline - monotonic()))
                except subprocess.TimeoutExpired:
                    _terminate_process_tree(process)
                    return AiOutcome('timeout', 'AI session exceeded its total time budget.')
                if monotonic() >= self._deadline:
                    return AiOutcome('timeout', 'AI session exceeded its total time budget.')
                if process.returncode != 0:
                    return AiOutcome('unavailable', 'AI provider failed; deterministic behavior remains available.')
                if destination.stat().st_size > self.budget.max_output_bytes:
                    return AiOutcome('rejected', 'AI response exceeded the output budget.')
                response = destination.read_text(encoding='utf-8')
                advice = decode_ai_advice(response, reduced, logical_names, self.budget)
                return AiOutcome('accepted', 'Validated advisory response; execution remains unauthorized.', advice)
        except (OSError, ValueError, UnicodeError):
            return AiOutcome('rejected', 'AI transport or response validation failed safely.')
        finally:
            if process is not None and process.poll() is None:
                _terminate_process_tree(process)


def main():
    """Private scripted child. No network, credentials, or arbitrary plugins."""
    import time
    source, destination = map(Path, sys.argv[1:])
    if source.stat().st_size > 262144:
        raise ValueError('Private scripted input exceeds the transport limit.')
    raw = json.loads(source.read_text(encoding='utf-8'))
    provider = OfflineAiProvider(raw['response'], raw['delay'], raw['fail'])
    time.sleep(provider.delay_seconds)
    if provider.fail:
        raise RuntimeError('Scripted failure.')
    destination.write_text(provider.response, encoding='utf-8')


if __name__ == '__main__':
    main()
