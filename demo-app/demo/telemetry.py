"""Bounded, best-effort delivery with stable event IDs across retries."""
import asyncio
import logging

import httpx


class Telemetry:
    def __init__(self, url, key, *, transport=None, capacity=128, timeout=1.0):
        self.queue = asyncio.Queue(maxsize=capacity)
        self.client = httpx.AsyncClient(transport=transport, timeout=timeout, follow_redirects=False)
        self.url, self.key, self.timeout = url, key, timeout
        self.accepting = True
        self.delivered = self.dropped = self.retries = 0
        self.task = None

    def start(self):
        self.task = asyncio.create_task(self.run())

    def emit(self, event):
        if not self.accepting:
            self.dropped += 1
            return
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            self.dropped += 1

    def stats(self):
        return {'queued': self.queue.qsize(), 'delivered': self.delivered,
                'dropped': self.dropped, 'retries': self.retries}

    async def deliver(self, event):
        for attempt in range(3):
            delay = 0.1 * (2 ** attempt)
            try:
                # A wall-clock bound also covers a stalled transport/pool.
                async with asyncio.timeout(self.timeout):
                    response = await self.client.post(self.url, json=event,
                        headers={'Authorization': f'Bearer {self.key}'})
                if response.status_code in (200, 201):
                    return True
                if response.status_code != 429 and response.status_code < 500:
                    return False
                if response.status_code == 429:
                    try:
                        delay = max(delay, float(response.headers.get('Retry-After', '1')))
                    except ValueError:
                        return False
                    # Do not hold the worker indefinitely or retry before the limit ends.
                    if not 0 <= delay <= 1:
                        return False
            except (httpx.HTTPError, TimeoutError):
                pass
            if attempt < 2:
                self.retries += 1
                await asyncio.sleep(delay)
        return False

    async def run(self):
        while True:
            event = await self.queue.get()
            try:
                if await self.deliver(event):
                    self.delivered += 1
                else:
                    self.dropped += 1
            except asyncio.CancelledError:
                self.dropped += 1
                raise
            except Exception:
                self.dropped += 1
                logging.getLogger(__name__).warning('Demo telemetry delivery failed; event dropped.')
            finally:
                self.queue.task_done()

    async def close(self, grace=5.0):
        self.accepting = False
        try:
            await asyncio.wait_for(self.queue.join(), timeout=grace)
        except TimeoutError:
            pass
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        while not self.queue.empty():
            self.queue.get_nowait()
            self.queue.task_done()
            self.dropped += 1
        await self.client.aclose()
