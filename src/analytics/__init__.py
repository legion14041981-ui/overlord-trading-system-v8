"""
Analytics Module for Portfolio Performance and Reporting.

Provides comprehensive portfolio analytics capabilities:
- Performance analysis and metrics calculation
- Report generation in multiple formats
- Real-time performance tracking
- Risk-adjusted return analysis
"""

from .metrics import MetricsCollector
from .reporter import ReportGenerator
from .dashboards import DashboardAPI

__all__ = [
    "MetricsCollector",
    "ReportGenerator",
    "DashboardAPI",
]

__version__ = "1.0.0"
