"""
Generic progress model and tracker.

Modules report progress through ProgressTracker.
ProgressTracker publishes ProgressUpdatedEvent via the Event Bus.
The UI subscribes to events — it never polls threads.
"""
