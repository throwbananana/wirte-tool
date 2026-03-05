import tkinter as tk
from tkinter import messagebox
import logging
from abc import ABC, abstractmethod
from typing import List, Tuple, Callable, Dict, Optional, Any

from writer_app.core.event_bus import get_event_bus


class BaseController(ABC):
    """Abstract base class for all UI controllers.

    Provides lifecycle management including:
    - Event subscription tracking and automatic cleanup
    - Listener registration tracking for ProjectManager and ThemeManager
    - Safe after() scheduling with widget existence checks
    - Centralized cleanup() method for resource release
    """

    def __init__(self, parent, project_manager, command_executor, theme_manager):
        self.parent = parent
        self.project_manager = project_manager
        self.command_executor = command_executor
        self.theme_manager = theme_manager
        self.view = None
        self.logger = logging.getLogger(self.__class__.__name__)

        # Lifecycle tracking
        self._destroyed: bool = False
        self._event_subscriptions: List[Tuple[str, Callable]] = []
        self._project_listeners: List[Callable] = []
        self._theme_listeners: List[Callable] = []
        self._after_jobs: Dict[str, str] = {}  # job_id -> after_id

    @abstractmethod
    def setup_ui(self):
        """Initialize the UI components."""
        pass

    @abstractmethod
    def refresh(self):
        """Refresh the UI with latest data."""
        pass

    def on_project_data_changed(self, event_type="all"):
        """Handle data change events. Default implementation calls refresh."""
        try:
            self.refresh()
        except Exception as e:
            self.handle_error(e, "Refreshing UI")

    def handle_error(self, error, context=""):
        """Centralized error handling."""
        msg = f"Error in {context}: {str(error)}" if context else f"Error: {str(error)}"
        self.logger.error(msg, exc_info=True)
        messagebox.showerror("Error", msg, parent=self.parent)

    # ========== Lifecycle Management Methods ==========

    def _subscribe_event(self, event_type: str, handler: Callable) -> None:
        """Subscribe to EventBus event and track for automatic cleanup.

        Args:
            event_type: The event type string (use Events constants)
            handler: The callback function
        """
        bus = get_event_bus()
        bus.subscribe(event_type, handler)
        self._event_subscriptions.append((event_type, handler))

    def _add_project_listener(self, handler: Callable) -> None:
        """Add ProjectManager listener and track for automatic cleanup.

        Args:
            handler: The callback function
        """
        if self.project_manager:
            self.project_manager.add_listener(handler)
            self._project_listeners.append(handler)

    def _add_theme_listener(self, handler: Callable) -> None:
        """Add ThemeManager listener and track for automatic cleanup.

        Args:
            handler: The callback function
        """
        if self.theme_manager:
            self.theme_manager.add_listener(handler)
            self._theme_listeners.append(handler)

    def _safe_after(self, job_id: str, delay_ms: int, callback: Callable) -> Optional[str]:
        """Schedule an after() callback with widget existence check.

        Automatically cancels any existing job with the same job_id.
        The callback will only execute if the widget still exists.

        Args:
            job_id: Unique identifier for this job (for cancellation)
            delay_ms: Delay in milliseconds
            callback: Function to call

        Returns:
            The after() job ID, or None if widget doesn't exist
        """
        if self._destroyed:
            return None

        # Get the widget to schedule on
        widget = self.view if self.view else self.parent
        if not widget or not widget.winfo_exists():
            return None

        # Cancel existing job with same ID
        self._cancel_after(job_id)

        def safe_callback():
            self._after_jobs.pop(job_id, None)
            if not self._destroyed and widget.winfo_exists():
                try:
                    callback()
                except tk.TclError:
                    pass  # Widget was destroyed during callback

        after_id = widget.after(delay_ms, safe_callback)
        self._after_jobs[job_id] = after_id
        return after_id

    def _cancel_after(self, job_id: str) -> bool:
        """Cancel a scheduled after() job.

        Args:
            job_id: The job identifier used in _safe_after()

        Returns:
            True if job was cancelled, False if not found
        """
        if job_id in self._after_jobs:
            after_id = self._after_jobs.pop(job_id)
            widget = self.view if self.view else self.parent
            if widget:
                try:
                    widget.after_cancel(after_id)
                except tk.TclError:
                    pass  # Widget already destroyed
            return True
        return False

    def _cancel_all_after_jobs(self) -> int:
        """Cancel all pending after() jobs.

        Returns:
            Number of jobs cancelled
        """
        count = 0
        for job_id in list(self._after_jobs.keys()):
            if self._cancel_after(job_id):
                count += 1
        return count

    def cleanup(self) -> None:
        """Clean up all tracked resources.

        This method should be called when the controller is being destroyed.
        Subclasses should override and call super().cleanup() to add custom cleanup.

        Cleanup order:
        1. Mark as destroyed to prevent new callbacks
        2. Cancel all pending after() jobs
        3. Unsubscribe from EventBus
        4. Remove ProjectManager listeners
        5. Remove ThemeManager listeners
        """
        self._destroyed = True

        # Cancel all pending after() jobs
        cancelled_jobs = self._cancel_all_after_jobs()
        if cancelled_jobs > 0:
            self.logger.debug(f"Cancelled {cancelled_jobs} pending after() jobs")

        # Unsubscribe from EventBus
        bus = get_event_bus()
        for event_type, handler in self._event_subscriptions:
            try:
                bus.unsubscribe(event_type, handler)
            except Exception as e:
                self.logger.warning(f"Error unsubscribing from {event_type}: {e}")
        event_count = len(self._event_subscriptions)
        self._event_subscriptions.clear()
        if event_count > 0:
            self.logger.debug(f"Unsubscribed from {event_count} events")

        # Remove ProjectManager listeners
        if self.project_manager:
            for handler in self._project_listeners:
                try:
                    self.project_manager.remove_listener(handler)
                except Exception as e:
                    self.logger.warning(f"Error removing project listener: {e}")
        listener_count = len(self._project_listeners)
        self._project_listeners.clear()

        # Remove ThemeManager listeners
        if self.theme_manager:
            for handler in self._theme_listeners:
                try:
                    self.theme_manager.remove_listener(handler)
                except Exception as e:
                    self.logger.warning(f"Error removing theme listener: {e}")
        theme_count = len(self._theme_listeners)
        self._theme_listeners.clear()

        if listener_count > 0 or theme_count > 0:
            self.logger.debug(f"Removed {listener_count} project + {theme_count} theme listeners")

    @property
    def is_destroyed(self) -> bool:
        """Check if this controller has been cleaned up."""
        return self._destroyed
