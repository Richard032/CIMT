"""Save a redacted, reviewable record of each AI request."""

import base64
import json
from copy import deepcopy
from datetime import datetime, timezone

from evidence import atomic


class RequestJournal:
    """Record request contents and links to the masked images actually supplied."""

    def __init__(self, result, evidence, redactor, publish):
        self.result = result
        self.evidence = evidence
        self.redactor = redactor
        self.publish = publish

    def begin(self, body, kind):
        records = self.result.setdefault('aiRequests', [])
        number = len(records)
        payload = deepcopy(body)
        images = []
        sections = {}
        for message in payload.get('input', []):
            content = message.get('content')
            if not isinstance(content, list):
                continue
            for part in content:
                if part.get('type') == 'input_image':
                    url = part.pop('image_url', '')
                    if isinstance(url, str) and url.startswith('data:image/png;base64,'):
                        data = base64.b64decode(url.split(',', 1)[1], validate=True)
                        path = self.evidence.save_image(f'ai-request-{number:04d}-image-{len(images):02d}.png', data)
                        part['imageEvidence'] = path
                        images.append(path)
                    else:
                        part['imageEvidence'] = 'Unavailable: unsupported image source'
                elif part.get('type') == 'input_text' and isinstance(part.get('text'), str):
                    try:
                        value = json.loads(part['text'])
                    except ValueError:
                        continue
                    if isinstance(value, dict):
                        part['text'] = value
                        for key, item in value.items():
                            sections[key] = len(json.dumps(item, ensure_ascii=False).encode('utf-8'))
        payload = self.redactor.object(payload)
        path = self.evidence.folder / f'ai-request-{number:04d}.json'
        relative = str(path.relative_to(self.evidence.report))
        atomic(path, payload)
        record = dict(id=number, step=len(self.result.get('steps', [])), kind=kind,
            status='prepared', requestPath=relative, images=images, sectionBytes=sections,
            timestamp=datetime.now(timezone.utc).isoformat(timespec='milliseconds'))
        records.append(record)
        self.publish()
        return record

    def finish(self, record, status, usage=None):
        record['status'] = status
        if isinstance(usage, dict):
            for source, target in [('input_tokens', 'inputTokens'), ('output_tokens', 'outputTokens')]:
                if type(usage.get(source)) is int and usage[source] >= 0:
                    record[target] = usage[source]
            details = usage.get('input_tokens_details')
            if isinstance(details, dict) and type(details.get('cached_tokens')) is int and details['cached_tokens'] >= 0:
                record['cachedInputTokens'] = details['cached_tokens']
        self.publish()
