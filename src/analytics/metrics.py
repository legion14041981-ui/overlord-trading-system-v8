"""
Metrics Collection Module
Сбор метрик и KPI
"""

import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Коллектор метрик."""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        
        logger.info("MetricsCollector initialized")
    
    def record_metric(self, name: str, value: float, tags: Dict = None):
        """
        Записать метрику.
        
        Args:
            name: имя метрики
            value: значение
            tags: дополнительные теги
        """
        self.metrics[name].append({
            'value': value,
            'timestamp': datetime.now().isoformat(),
            'tags': tags or {}
        })
    
    def increment_counter(self, name: str, amount: int = 1):
        """Увеличить счётчик."""
        self.counters[name] += amount
    
    def set_gauge(self, name: str, value: float):
        """Установить значение gauge."""
        self.gauges[name] = value
    
    def get_metric_summary(self, name: str, window_minutes: int = 60) -> Dict:
        """
        Получить сводку по метрике.
        
        Args:
            name: имя метрики
            window_minutes: временное окно в минутах
        
        Returns:
            сводка статистики
        """
        if name not in self.metrics:
            return {'error': 'Metric not found'}
        
        # Фильтрация по временному окну
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        recent_metrics = [
            m for m in self.metrics[name]
            if datetime.fromisoformat(m['timestamp']) > cutoff
        ]
        
        if not recent_metrics:
            return {'count': 0}
        
        values = [m['value'] for m in recent_metrics]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'latest': values[-1]
        }
    
    def get_all_metrics(self) -> Dict:
        """Получить все метрики."""
        return {
            'metrics': dict(self.metrics),
            'counters': dict(self.counters),
            'gauges': dict(self.gauges)
        }
