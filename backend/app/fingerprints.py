"""Versioned, conservative grouping of already-scrubbed exception evidence."""
import hashlib
import json
import re

VERSION = 'exc-v1'
PYTHON = re.compile(r'^\s*File "([^"]+)", line \d+, in (.+?)\s*$')
COMPACT = re.compile(r'^\s*(.+?):\d+(?::\d+)?(?: in |\s+in\s+)(.+?)\s*$')
LOCATION = re.compile(r'^\s*(?:\w[\w.]*\s+at\s+)?(.+?):\d+(?::\d+)?\s*$')
UUID = re.compile(r'(?i)[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}')


def fingerprint(exception_type, stack_trace):
    """Use the innermost application frame; never infer type from a message.

    Python tracebacks and the demo's compact frames run outermost to innermost.
    Unrecognized stacks use their complete normalized text to avoid merging
    unrelated locations. Without a stack, there is insufficient grouping evidence.
    """
    kind = (exception_type or '').strip()
    stack = (stack_trace or '').strip().replace('\\', '/')
    if not kind or not stack:
        return None
    frames = []
    for line in stack.splitlines():
        match = PYTHON.match(line) or COMPACT.match(line) or LOCATION.match(line)
        if match:
            path = match[1]
            # Retain module directories: equal basenames need not be equal code.
            path = UUID.sub('<uuid>', path)
            function = match[2].strip() if len(match.groups()) > 1 else ''
            frames.append((path, function))
    application = [frame for frame in frames if not any(part in '/' + frame[0]
                   for part in ('/site-packages/', '/dist-packages/', '/lib/python', '/Lib/'))]
    location = (application or frames)[-1] if frames else ['raw', '\n'.join(line.strip() for line in stack.splitlines() if line.strip())]
    canonical = json.dumps([VERSION, kind, location], ensure_ascii=True, separators=(',', ':'))
    return VERSION + ':' + hashlib.sha256(canonical.encode()).hexdigest()
