"""
Dashboard API Module
API для дашбордов
"""

import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class DashboardAPI:
    """
API для дашбордов.
    """
    
    def __init__(self):
        self.widgets = {}
        logger.info("DashboardAPI initialized")
    
    def register_widget(self, widget_id: str, widget_data: Dict):
        """
        Зарегистрировать виджет.
        
        Args:
            widget_id: ID виджета
            widget_data: данные виджета
        """
        self.widgets[widget_id] = {
            **widget_data,
            'registered_at': datetime.now().isoformat()
        }
        logger.info(f"Widget registered: {widget_id}")
    
    def get_widget(self, widget_id: str) -> Dict:
        """Получить данные виджета."""
        return self.widgets.get(widget_id, {})
    
    def get_dashboard_data(self) -> Dict:
        """Получить данные всего дашборда."""
        return {
            'timestamp': datetime.now().isoformat(),
            'widgets': self.widgets,
            'widget_count': len(self.widgets)
        }
