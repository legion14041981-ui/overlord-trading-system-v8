"""
GRAIL Agent — Security & Token Validation Module
Агент безопасности для Overlord Trading System v8
"""

import hashlib
import hmac
import logging
import time
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
import secrets

logger = logging.getLogger(__name__)


class GrailAgent:
    """
    Agile security agent для валидации и управления токенами.
    
    Возможности:
    - Валидация GitHub PAT токенов
    - Генерация session токенов
    - Проверка разрешений
    - Blacklist управление
    """
    
    VERSION = "1.0.0"
    
    def __init__(self, secret_key: str = None):
        """
        Инициализация Grail Agent.
        
        Args:
            secret_key: секретный ключ для подписи токенов
        """
        self.secret_key = secret_key or self._generate_secret()
        self.token_blacklist = set()
        self.active_tokens = {}
        self.validation_cache = {}
        
        logger.info(f"Grail Agent v{self.VERSION} initialized")
    
    def _generate_secret(self) -> str:
        """Генерировать случайный секретный ключ."""
        return secrets.token_urlsafe(32)
    
    def validate_github_token(self, token: str) -> Tuple[bool, Dict[str, str]]:
        """
        Валидировать GitHub PAT токен по его структуре.
        
        Args:
            token: GitHub Personal Access Token
            
        Returns:
            (is_valid, metadata_dict)
        """
        metadata = {
            'token_format': 'unknown',
            'is_github_pat': False,
            'risk_score': 'unknown',
            'validated_at': datetime.now().isoformat()
        }
        
        if not token or not isinstance(token, str):
            return False, metadata
        
        # GitHub PAT форматы:
        # Classic: ghp_XXXXXXXXXXXXXX...
        # Fine-grained: github_pat_XXXXX...
        # OAuth: gho_XXXXXXXXXXXXXX...
        
        if token.startswith(('ghp_', 'github_pat_', 'gho_')):
            metadata['is_github_pat'] = True
            metadata['token_format'] = 'valid_github_format'
            
            if token.startswith('github_pat_'):
                metadata['token_type'] = 'fine_grained'
            elif token.startswith('ghp_'):
                metadata['token_type'] = 'classic'
            else:
                metadata['token_type'] = 'oauth'
        else:
            metadata['is_github_pat'] = False
            return False, metadata
        
        # Проверка на длину
        if len(token) < 30:
            metadata['risk_score'] = 'high'
            return False, metadata
        
        metadata['risk_score'] = 'low'
        logger.info(f"Token validated: format={metadata['token_format']}, type={metadata.get('token_type')}")
        return True, metadata
    
    def generate_session_token(
        self,
        user_id: str,
        ttl_seconds: int = 3600,
        scopes: list = None
    ) -> str:
        """
        Сгенерировать безопасный session токен.
        
        Args:
            user_id: ID пользователя
            ttl_seconds: время жизни в секундах
            scopes: список разрешений
            
        Returns:
            signed token string
        """
        timestamp = int(time.time())
        payload = f"{user_id}:{timestamp}:{ttl_seconds}"
        signature = hmac.new(
            self.secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        token = f"grail_{payload}_{signature}"
        self.active_tokens[token] = {
            'user_id': user_id,
            'created': datetime.now(),
            'expires': datetime.now() + timedelta(seconds=ttl_seconds),
            'scopes': scopes or []
        }
        
        logger.info(f"Session token generated for user {user_id}, ttl={ttl_seconds}s")
        return token
    
    def verify_session_token(self, token: str) -> Tuple[bool, Optional[str]]:
        """
        Проверить validity session токена.
        
        Returns:
            (is_valid, user_id)
        """
        if not token.startswith('grail_'):
            return False, None
        
        if token in self.token_blacklist:
            logger.warning("Token is blacklisted")
            return False, None
        
        if token in self.active_tokens:
            token_data = self.active_tokens[token]
            if datetime.now() < token_data['expires']:
                return True, token_data['user_id']
            else:
                # Токен истёк
                del self.active_tokens[token]
                logger.info("Token expired and removed")
                return False, None
        
        return False, None
    
    def check_permissions(
        self,
        user_id: str,
        required_permissions: list
    ) -> bool:
        """
        Проверить наличие необходимых разрешений у пользователя.
        
        Args:
            user_id: ID пользователя
            required_permissions: список необходимых прав
            
        Returns:
            True если все права присутствуют
        """
        # Это заглушка — подключить к реальной системе разрешений
        logger.debug(f"Checking permissions for {user_id}: {required_permissions}")
        return True
    
    def blacklist_token(self, token: str) -> None:
        """Добавить токен в чёрный список (например, при logout)."""
        self.token_blacklist.add(token)
        if token in self.active_tokens:
            del self.active_tokens[token]
        logger.info("Token blacklisted")
    
    def get_health_status(self) -> Dict:
        """Получить статус здоровья Grail Agent."""
        return {
            'version': self.VERSION,
            'active_tokens': len(self.active_tokens),
            'blacklisted_tokens': len(self.token_blacklist),
            'status': 'healthy'
        }


# Singleton для глобального доступа
_grail_agent = None


def get_grail_agent(secret_key: str = None) -> GrailAgent:
    """Получить или создать singleton GrailAgent."""
    global _grail_agent
    if _grail_agent is None:
        _grail_agent = GrailAgent(secret_key)
    return _grail_agent


if __name__ == '__main__':
    # Локальное тестирование
    agent = GrailAgent()
    
    # Тест GitHub token
    test_token = "github_pat_11BY654DI0ggVYdMSzYhjE_example"
    valid, meta = agent.validate_github_token(test_token)
    print(f"GitHub Token Valid: {valid}")
    print(f"Metadata: {meta}")
    
    # Тест session token
    session = agent.generate_session_token("user123", ttl_seconds=60)
    print(f"Session Token: {session}")
    
    valid_session, user = agent.verify_session_token(session)
    print(f"Session Valid: {valid_session}, User: {user}")
    
    print(f"Health: {agent.get_health_status()}")
