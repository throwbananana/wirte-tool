"""
Tkinter utility functions for safe widget operations.

Provides helper functions for common Tkinter patterns that need
safety checks, especially for async callback scenarios.
"""

import tkinter as tk
from typing import Callable, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


def safe_after(
    widget: tk.Widget,
    delay_ms: int,
    callback: Callable,
    job_tracker: Optional[Dict[str, str]] = None,
    job_id: Optional[str] = None
) -> Optional[str]:
    """
    Schedule an after() callback with widget existence check.

    This function ensures the callback only executes if the widget
    still exists, preventing TclError exceptions when widgets are
    destroyed while callbacks are pending.

    Args:
        widget: The tkinter widget to schedule the callback on
        delay_ms: Delay in milliseconds before executing callback
        callback: Function to call (no arguments)
        job_tracker: Optional dict to track job IDs for cancellation
        job_id: Key for job_tracker (required if job_tracker provided)

    Returns:
        The after() job ID, or None if widget doesn't exist

    Example:
        # Simple usage
        safe_after(self, 100, lambda: self.update_status("Done"))

        # With job tracking for cancellation
        self._jobs = {}
        safe_after(self, 500, self.do_work, self._jobs, "work_job")

        # Later, to cancel:
        cancel_after(self, self._jobs, "work_job")
    """
    if not widget.winfo_exists():
        return None

    def safe_callback():
        # Remove from tracker first
        if job_tracker is not None and job_id is not None:
            job_tracker.pop(job_id, None)

        # Check widget still exists before calling
        if widget.winfo_exists():
            try:
                callback()
            except tk.TclError as e:
                # Widget was destroyed during callback execution
                logger.debug(f"TclError in safe_after callback: {e}")
            except Exception as e:
                logger.error(f"Error in safe_after callback: {e}", exc_info=True)

    # Cancel existing job with same ID if tracking
    if job_tracker is not None and job_id is not None:
        if job_id in job_tracker:
            try:
                widget.after_cancel(job_tracker[job_id])
            except tk.TclError:
                pass
            job_tracker.pop(job_id, None)

    after_id = widget.after(delay_ms, safe_callback)

    if job_tracker is not None and job_id is not None:
        job_tracker[job_id] = after_id

    return after_id


def cancel_after(
    widget: tk.Widget,
    job_tracker: Dict[str, str],
    job_id: str
) -> bool:
    """
    Cancel a scheduled after() job.

    Args:
        widget: The tkinter widget the job was scheduled on
        job_tracker: Dict containing job IDs
        job_id: The job ID to cancel

    Returns:
        True if job was cancelled, False if not found
    """
    if job_id not in job_tracker:
        return False

    after_id = job_tracker.pop(job_id)
    try:
        widget.after_cancel(after_id)
        return True
    except tk.TclError:
        return False


def cancel_all_after(widget: tk.Widget, job_tracker: Dict[str, str]) -> int:
    """
    Cancel all scheduled after() jobs in a tracker.

    Args:
        widget: The tkinter widget the jobs were scheduled on
        job_tracker: Dict containing job IDs

    Returns:
        Number of jobs cancelled
    """
    count = 0
    for job_id in list(job_tracker.keys()):
        if cancel_after(widget, job_tracker, job_id):
            count += 1
    return count


def safe_destroy(widget: tk.Widget) -> bool:
    """
    Safely destroy a widget, checking existence first.

    Args:
        widget: The widget to destroy

    Returns:
        True if widget was destroyed, False if already destroyed
    """
    try:
        if widget.winfo_exists():
            widget.destroy()
            return True
    except tk.TclError:
        pass
    return False


def safe_configure(widget: tk.Widget, **kwargs) -> bool:
    """
    Safely configure a widget, checking existence first.

    Args:
        widget: The widget to configure
        **kwargs: Configuration options

    Returns:
        True if configured successfully, False otherwise
    """
    try:
        if widget.winfo_exists():
            widget.configure(**kwargs)
            return True
    except tk.TclError:
        pass
    return False


def safe_update_text(text_widget: tk.Text, content: str, readonly: bool = False) -> bool:
    """
    Safely update a Text widget's content.

    Args:
        text_widget: The Text widget to update
        content: New content to set
        readonly: If True, disable widget after update

    Returns:
        True if updated successfully, False otherwise
    """
    try:
        if not text_widget.winfo_exists():
            return False

        state = text_widget.cget('state')
        text_widget.configure(state='normal')
        text_widget.delete('1.0', 'end')
        text_widget.insert('1.0', content)

        if readonly:
            text_widget.configure(state='disabled')
        else:
            text_widget.configure(state=state)

        return True
    except tk.TclError:
        return False


class AfterJobTracker:
    """
    Helper class for tracking and managing after() jobs.

    Example:
        tracker = AfterJobTracker(self)
        tracker.schedule("update", 100, self.update_display)
        tracker.schedule("save", 5000, self.auto_save)

        # Cancel specific job
        tracker.cancel("update")

        # Cancel all on cleanup
        tracker.cancel_all()
    """

    def __init__(self, widget: tk.Widget):
        """
        Initialize the tracker.

        Args:
            widget: The widget to schedule jobs on
        """
        self.widget = widget
        self._jobs: Dict[str, str] = {}

    def schedule(self, job_id: str, delay_ms: int, callback: Callable) -> Optional[str]:
        """
        Schedule a job, cancelling any existing job with same ID.

        Args:
            job_id: Unique identifier for this job
            delay_ms: Delay in milliseconds
            callback: Function to call

        Returns:
            The after() job ID, or None if widget doesn't exist
        """
        return safe_after(self.widget, delay_ms, callback, self._jobs, job_id)

    def cancel(self, job_id: str) -> bool:
        """
        Cancel a specific job.

        Args:
            job_id: The job to cancel

        Returns:
            True if cancelled, False if not found
        """
        return cancel_after(self.widget, self._jobs, job_id)

    def cancel_all(self) -> int:
        """
        Cancel all tracked jobs.

        Returns:
            Number of jobs cancelled
        """
        return cancel_all_after(self.widget, self._jobs)

    def has_job(self, job_id: str) -> bool:
        """Check if a job is currently scheduled."""
        return job_id in self._jobs

    @property
    def job_count(self) -> int:
        """Number of currently scheduled jobs."""
        return len(self._jobs)
