"""
Reporting Module
Генерация отчётов
"""

import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class Reporter:
    """Генератор отчётов."""
    
    def __init__(self):
        self.reports = []
        logger.info("Reporter initialized")
    
    def generate_trade_report(self, trades: List[Dict]) -> Dict:
        """
        Сгенерировать отчёт по сделкам.
        
        Args:
            trades: список сделок
        
        Returns:
            отчёт
        """
        if not trades:
            return {'error': 'No trades to report'}
        
        winning = [t for t in trades if t.get('pnl', 0) > 0]
        losing = [t for t in trades if t.get('pnl', 0) < 0]
        
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_trades': len(trades),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': len(winning) / len(trades) if trades else 0,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / len(trades) if trades else 0
        }
        
        self.reports.append(report)
        logger.info(f"Trade report generated: {len(trades)} trades")
        
        return report
    
    def generate_system_report(self, system_data: Dict) -> Dict:
        """
        Сгенерировать системный отчёт.
        
        Args:
            system_data: данные системы
        
        Returns:
            отчёт
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'type': 'system_report',
            'data': system_data
        }
        
        self.reports.append(report)
        logger.info("System report generated")
        
        return report
    
    def get_recent_reports(self, limit: int = 10) -> List[Dict]:
        """Получить последние отчёты."""
        return self.reports[-limit:]
