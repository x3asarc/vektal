"""
Server-Sent Events (SSE) infrastructure for real-time updates.

Provides:
- format_sse: Format messages according to SSE specification
- MessageAnnouncer: Thread-safe broadcaster for SSE events
- job_announcer: Global instance for job progress updates

Pattern from: https://maxhalford.github.io/blog/flask-sse-no-deps/
"""
import queue
from typing import Generator


def format_sse(data: str, event: str | None = None, id: str | None = None, retry: int | None = None) -> str:
    """
    Format a message according to SSE specification.

    Args:
        data: JSON string to send
        event: Event type (e.g., "job_123")
        id: Message ID for client reconnection
        retry: Retry interval in milliseconds

    Returns:
        Formatted SSE message (data: ...\n\n)

    Example:
        >>> format_sse(data='{"status": "running"}', event="job_123")
        'event: job_123\\ndata: {"status": "running"}\\n\\n'
    """
    msg = ""
    if id:
        msg += f"id: {id}\n"
    if event:
        msg += f"event: {event}\n"
    if retry:
        msg += f"retry: {retry}\n"
    msg += f"data: {data}\n\n"
    return msg


class MessageAnnouncer:
    """
    Thread-safe SSE broadcaster for job progress updates.

    Pattern from: https://maxhalford.github.io/blog/flask-sse-no-deps/

    Usage:
        announcer = MessageAnnouncer()

        # In route handler:
        def stream():
            messages = announcer.listen()
            while True:
                msg = messages.get()
                yield msg

        # In background job:
        announcer.announce(job_id, json.dumps({"status": "running", ...}))
    """

    def __init__(self):
        self.listeners: list[queue.Queue] = []

    def listen(self) -> queue.Queue:
        """
        Subscribe a new client to updates.

        Returns:
            Queue that will receive messages
        """
        q = queue.Queue(maxsize=5)  # Prevent memory exhaustion
        self.listeners.append(q)
        return q

    def announce(self, job_id: int, data: str, event_type: str | None = None) -> None:
        """
        Broadcast message to all listeners for a specific job.

        Args:
            job_id: Job ID for event naming
            data: JSON string payload
            event_type: Optional event type override
        """
        event = event_type or f"job_{job_id}"
        msg = format_sse(data=data, event=event)

        # Iterate in reverse to safely remove dead listeners
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except queue.Full:
                # Client too slow, remove them
                del self.listeners[i]

    def remove_listener(self, q: queue.Queue) -> None:
        """Remove a listener queue (on client disconnect)."""
        try:
            self.listeners.remove(q)
        except ValueError:
            pass  # Already removed


# Global announcer for job progress updates
job_announcer = MessageAnnouncer()


__all__ = ['format_sse', 'MessageAnnouncer', 'job_announcer']
