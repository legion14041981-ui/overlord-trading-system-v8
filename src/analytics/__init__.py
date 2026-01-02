"""Analytics Module for Portfolio Performance and Reporting.

Provides comprehensive portfolio analytics capabilities:
- Performance analysis and metrics calculation
- Report generation in multiple formats
- Real-time performance tracking
- Risk-adjusted return analysis
"""

from .performance_analyzer import PerformanceAnalyzer
from .metrics_calculator import MetricsCalculator
from .report_generator import ReportGenerator

__all__ = [
    "PerformanceAnalyzer",
    "MetricsCalculator",
    "ReportGenerator",
]
