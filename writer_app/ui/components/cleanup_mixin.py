"""
Cleanup mixin for UI components that need lifecycle management.

This mixin provides tracking and cleanup for:
- EventBus subscriptions
- Manager listeners (ProjectManager, ThemeManager, etc.)
- Scheduled after() callbacks

Usage:
    class MyPanel(tk.Frame, CleanupMixin):
        def __init__(self, parent, project_manager, theme_manager):
            tk.Frame.__init__(self, parent)
            self._init_cleanup_tracking()

            # Use tracking methods instead of direct calls
            self._track_event_subscription(Events.SCENE_UPDATED, self._on_scene_updated)
            self._track_listener(theme_manager, self.apply_theme)

        def destroy(self):
            self.cleanup_subscriptions()
            super().destroy()
"""

import tkinter as tk
from typing import List, Tuple, Callable, Dict, Any, Optional
import logging

from writer_app.core.event_bus import get_event_bus

logger = logging.getLogger(__name__)


class CleanupMixin:
    """
    Mixin providing cleanup tracking for UI components.

    This is designed for Tkinter widgets (Frame, Canvas, etc.) that need
    to subscribe to events or add listeners but aren't full controllers.
    """

    def _init_cleanup_tracking(self) -> None:
        """
        Initialize cleanup tracking data structures.

        Must be called in __init__ after the widget is initialized.
        """
        self._event_subscriptions: List[Tuple[str, Callable]] = []
        self._listener_refs: List[Tuple[Any, Callable]] = []
        self._after_jobs: Dict[str, str] = {}
        self._cleanup_destroyed: bool = False

    def _track_event_subscription(self, event_type: str, handler: Callable) -> None:
        """
        Subscribe to EventBus event and track for cleanup.

        Args:
            event_type: The event type string (use Events constants)
            handler: The callback function
        """
        if not hasattr(self, '_event_subscriptions'):
            self._init_cleanup_tracking()

        bus = get_event_bus()
        bus.subscribe(event_type, handler)
        self._event_subscriptions.append((event_type, handler))

    def _track_listener(self, manager: Any, handler: Callable) -> None:
        """
        Add a listener to a manager and track for cleanup.

        Works with any manager that has add_listener/remove_listener methods.

        Args:
            manager: The manager object (ProjectManager, ThemeManager, etc.)
            handler: The callback function
        """
        if not hasattr(self, '_listener_refs'):
            self._init_cleanup_tracking()

        if manager and hasattr(manager, 'add_listener'):
            manager.add_listener(handler)
            self._listener_refs.append((manager, handler))

    def _safe_after(self, job_id: str, delay_ms: int, callback: Callable) -> Optional[str]:
        """
        Schedule an after() callback with widget existence check.

        Automatically cancels any existing job with the same job_id.

        Args:
            job_id: Unique identifier for this job
            delay_ms: Delay in milliseconds
            callback: Function to call

        Returns:
            The after() job ID, or None if widget doesn't exist
        """
        if not hasattr(self, '_after_jobs'):
            self._init_cleanup_tracking()

        if getattr(self, '_cleanup_destroyed', False):
            return None

        # Must be a widget with winfo_exists
        if not hasattr(self, 'winfo_exists') or not self.winfo_exists():
            return None

        # Cancel existing job with same ID
        self._cancel_after(job_id)

        def safe_callback():
            self._after_jobs.pop(job_id, None)
            if not getattr(self, '_cleanup_destroyed', False):
                if hasattr(self, 'winfo_exists') and self.winfo_exists():
                    try:
                        callback()
                    except tk.TclError:
                        pass

        after_id = self.after(delay_ms, safe_callback)
        self._after_jobs[job_id] = after_id
        return after_id

    def _cancel_after(self, job_id: str) -> bool:
        """
        Cancel a scheduled after() job.

        Args:
            job_id: The job identifier

        Returns:
            True if job was cancelled, False if not found
        """
        if not hasattr(self, '_after_jobs'):
            return False

        if job_id in self._after_jobs:
            after_id = self._after_jobs.pop(job_id)
            try:
                self.after_cancel(after_id)
            except (tk.TclError, AttributeError):
                pass
            return True
        return False

    def _cancel_all_after_jobs(self) -> int:
        """
        Cancel all pending after() jobs.

        Returns:
            Number of jobs cancelled
        """
        if not hasattr(self, '_after_jobs'):
            return 0

        count = 0
        for job_id in list(self._after_jobs.keys()):
            if self._cancel_after(job_id):
                count += 1
        return count

    def cleanup_subscriptions(self) -> None:
        """
        Clean up all tracked subscriptions and listeners.

        Should be called in the widget's destroy() method before super().destroy().

        Example:
            def destroy(self):
                self.cleanup_subscriptions()
                super().destroy()
        """
        self._cleanup_destroyed = True

        # Cancel all pending after() jobs
        cancelled_jobs = self._cancel_all_after_jobs()

        # Unsubscribe from EventBus
        event_count = 0
        if hasattr(self, '_event_subscriptions'):
            bus = get_event_bus()
            for event_type, handler in self._event_subscriptions:
                try:
                    bus.unsubscribe(event_type, handler)
                    event_count += 1
                except Exception as e:
                    logger.warning(f"Error unsubscribing from {event_type}: {e}")
            self._event_subscriptions.clear()

        # Remove listeners from managers
        listener_count = 0
        if hasattr(self, '_listener_refs'):
            for manager, handler in self._listener_refs:
                try:
                    if hasattr(manager, 'remove_listener'):
                        manager.remove_listener(handler)
                        listener_count += 1
                except Exception as e:
                    logger.warning(f"Error removing listener: {e}")
            self._listener_refs.clear()

        if cancelled_jobs > 0 or event_count > 0 or listener_count > 0:
            logger.debug(
                f"Cleanup: {cancelled_jobs} jobs, "
                f"{event_count} events, {listener_count} listeners"
            )

    @property
    def is_cleanup_destroyed(self) -> bool:
        """Check if cleanup has been performed."""
        return getattr(self, '_cleanup_destroyed', False)


class CleanupFrame(tk.Frame, CleanupMixin):
    """
    A Frame with built-in cleanup support.

    Example:
        class MyPanel(CleanupFrame):
            def __init__(self, parent, project_manager):
                super().__init__(parent)
                self.project_manager = project_manager

                # Track subscriptions
                self._track_event_subscription(Events.SCENE_UPDATED, self._on_scene)
                self._track_listener(project_manager, self._on_data_changed)

            def _on_scene(self, **kwargs):
                pass

            def _on_data_changed(self, event_type):
                pass
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._init_cleanup_tracking()

    def destroy(self):
        self.cleanup_subscriptions()
        super().destroy()


class CleanupToplevel(tk.Toplevel, CleanupMixin):
    """
    A Toplevel window with built-in cleanup support.

    Example:
        class MyDialog(CleanupToplevel):
            def __init__(self, parent, theme_manager):
                super().__init__(parent)
                self._track_listener(theme_manager, self.apply_theme)
    """

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._init_cleanup_tracking()

    def destroy(self):
        self.cleanup_subscriptions()
        super().destroy()


class CleanupCanvas(tk.Canvas, CleanupMixin):
    """
    A Canvas with built-in cleanup support.

    Useful for custom drawing components that need event subscriptions.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._init_cleanup_tracking()

    def destroy(self):
        self.cleanup_subscriptions()
        super().destroy()
