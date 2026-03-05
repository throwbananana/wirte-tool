"""
Genre-specific exporters package.

Contains specialized exporters for different project types.

Usage:
    from writer_app.core.exporters import PoetryImageExporter, SuspenseMarkdownExporter

    # Register with ExporterRegistry
    ExporterRegistry.register(PoetryImageExporter)
    ExporterRegistry.register(SuspenseMarkdownExporter)
"""

from .poetry_exporter import PoetryImageExporter
from .suspense_exporter import SuspenseMarkdownExporter


def register_genre_exporters():
    """Register all genre-specific exporters with the ExporterRegistry."""
    from writer_app.core.exporter import ExporterRegistry

    exporters = [
        PoetryImageExporter,
        SuspenseMarkdownExporter,
    ]

    for exporter in exporters:
        if exporter.key not in ExporterRegistry.list_keys():
            ExporterRegistry.register(exporter)


__all__ = [
    'PoetryImageExporter',
    'SuspenseMarkdownExporter',
    'register_genre_exporters',
]
