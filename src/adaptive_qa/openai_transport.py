"""Internal fixed-origin HTTPS primitive; not registered for runtime execution.

The caller must own process isolation and charge reservation. This primitive
does not provide a billing guarantee or retry. Normal AI sessions remain offline.
"""

import http.client
import json
import ssl
from time import monotonic

from adaptive_qa.ai_models import AiBudget
from adaptive_qa.ai_validation import decode_ai_advice
from adaptive_qa.openai_contract import OpenAiConfiguration, build_openai_request, extract_openai_text


class OpenAiTransportError(Exception):
    """Safe provider transport error without headers, keys, or response bodies."""


def _perform_openai_request(configuration, reduced, logical_names, budget, *,
                             remote_enabled=False, reserved_cost_microusd=0):
    """Internal socket-bounded call; callers must impose a hard process deadline."""
    if not isinstance(configuration, OpenAiConfiguration) or not isinstance(budget, AiBudget):
        raise ValueError('Typed provider configuration and budget are required.')
    # A positive reservation is required even when a future account offers free
    # credits. The caller, not provider response text, owns this trusted amount.
    if (remote_enabled is not True or type(reserved_cost_microusd) is not int
            or not 0 < reserved_cost_microusd <= budget.max_cost_microusd):
        raise OpenAiTransportError('Remote AI execution is disabled or lacks cost admission.')
    connection = None
    try:
        payload = build_openai_request(configuration, reduced, logical_names, budget)
        body = json.dumps(payload, ensure_ascii=True, allow_nan=False).encode('utf-8')
        if len(body) > 262144:
            raise ValueError()
        key = configuration.api_key.resolve().value
        if (not key.isascii() or not 1 <= len(key) <= 4096
                or any(ord(character) <= 32 or ord(character) == 127 for character in key)):
            raise ValueError()
        deadline = monotonic() + budget.timeout_seconds
        # http.client does not consult environment proxy URLs and never follows
        # redirects. Host, port and path are constants, never page/model input.
        connection = http.client.HTTPSConnection('api.openai.com', 443,
            timeout=budget.timeout_seconds, context=ssl.create_default_context())
        connection.connect()

        def set_remaining_timeout():
            remaining = deadline - monotonic()
            if remaining <= 0 or connection.sock is None:
                raise TimeoutError()
            connection.sock.settimeout(remaining)

        set_remaining_timeout()
        connection.request('POST', '/v1/responses', body=body, headers={
            'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json',
            'Accept': 'application/json', 'Accept-Encoding': 'identity'})
        set_remaining_timeout()
        response = connection.getresponse()
        if response.status != 200:
            # Refuse redirects/rate limits/auth errors without reading/debugging
            # their potentially sensitive bodies or attempting automatic retries.
            raise ValueError()
        media = response.getheader('Content-Type', '').split(';', 1)[0].strip().casefold()
        encoding = response.getheader('Content-Encoding', 'identity').strip().casefold()
        if media != 'application/json' or encoding != 'identity':
            raise ValueError()
        set_remaining_timeout()
        raw = response.read(262145)
        if len(raw) > 262144 or monotonic() >= deadline:
            raise ValueError()
        text = extract_openai_text(raw, budget)
        return decode_ai_advice(text, reduced, logical_names, budget)
    except (OSError, ValueError, UnicodeError, http.client.HTTPException):
        raise OpenAiTransportError('Remote AI transport or validated response processing failed.') from None
    finally:
        if connection is not None:
            connection.close()
