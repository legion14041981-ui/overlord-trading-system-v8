"""
OVERLORD State Machine
Управление состояниями системы
"""

import logging
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SystemState(str, Enum):
    """ Возможные состояния системы """
    INITIALIZING = "initializing"
    IDLE = "idle"
    TRADING = "trading"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class StateMachine:
    """Машина состояний для Overlord."""
    
    def __init__(self):
        self.current_state = SystemState.INITIALIZING
        self.previous_state = None
        self.state_history: List[Dict] = []
        self.transition_count = 0
        
        # Разрешённые переходы
        self.allowed_transitions = {
            SystemState.INITIALIZING: [SystemState.IDLE, SystemState.ERROR],
            SystemState.IDLE: [SystemState.TRADING, SystemState.PAUSED, SystemState.SHUTDOWN],
            SystemState.TRADING: [SystemState.IDLE, SystemState.PAUSED, SystemState.ERROR],
            SystemState.PAUSED: [SystemState.IDLE, SystemState.TRADING, SystemState.SHUTDOWN],
            SystemState.ERROR: [SystemState.IDLE, SystemState.SHUTDOWN],
            SystemState.SHUTDOWN: []
        }
        
        self._record_transition(None, SystemState.INITIALIZING, "System initialized")
        logger.info(f"State Machine initialized: {self.current_state}")
    
    def transition_to(self, new_state: SystemState, reason: str = "") -> bool:
        """
        Перейти в новое состояние.
        
        Args:
            new_state: новое состояние
            reason: причина перехода
        
        Returns:
            True если переход успешен
        """
        if not self._is_valid_transition(new_state):
            logger.error(
                f"Invalid transition: {self.current_state} -> {new_state}. "
                f"Allowed: {self.allowed_transitions.get(self.current_state)}"
            )
            return False
        
        self.previous_state = self.current_state
        self.current_state = new_state
        self.transition_count += 1
        
        self._record_transition(self.previous_state, new_state, reason)
        
        logger.info(f"State transition: {self.previous_state} -> {new_state} ({reason})")
        return True
    
    def _is_valid_transition(self, new_state: SystemState) -> bool:
        """Проверить, разрешён ли переход."""
        return new_state in self.allowed_transitions.get(self.current_state, [])
    
    def _record_transition(self, from_state: Optional[SystemState], to_state: SystemState, reason: str):
        """Записать переход в историю."""
        self.state_history.append({
            'from': from_state.value if from_state else None,
            'to': to_state.value,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'transition_id': self.transition_count
        })
    
    def get_current_state(self) -> SystemState:
        """Получить текущее состояние."""
        return self.current_state
    
    def is_ready(self) -> bool:
        """Проверить, готова ли система."""
        return self.current_state in [SystemState.IDLE, SystemState.TRADING]
    
    def get_state_history(self, limit: int = 10) -> List[Dict]:
        """Получить историю переходов."""
        return self.state_history[-limit:]
    
    def get_health_status(self) -> Dict:
        """Получить статус здоровья."""
        return {
            'current_state': self.current_state.value,
            'previous_state': self.previous_state.value if self.previous_state else None,
            'is_ready': self.is_ready(),
            'transition_count': self.transition_count,
            'status': 'healthy' if self.current_state != SystemState.ERROR else 'error'
        }
