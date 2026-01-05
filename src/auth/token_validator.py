"""
Token Validation Module
Валидация токенов и API ключей
"""

import logging
import re
from typing import Tuple, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TokenValidator:
    """Валидатор токенов."""
    
    # Regex паттерны для GitHub tokens
    GITHUB_PAT_PATTERN = r'^(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82}|gho_[a-zA-Z0-9]{36})$'
    
    # Regex для API keys
    API_KEY_PATTERN = r'^[a-zA-Z0-9_\-]{32,}$'
    
    def __init__(self):
        self.validation_cache = {}
        logger.info("TokenValidator initialized")
    
    def validate_github_token(self, token: str) -> Tuple[bool, Dict]:
        """
        Валидировать GitHub Personal Access Token.
        
        Returns:
            (is_valid, metadata)
        """
        metadata = {
            'token_type': 'github_pat',
            'format_valid': False,
            'length': len(token) if token else 0,
            'timestamp': datetime.now().isoformat()
        }
        
        if not token:
            return False, metadata
        
        # Проверка формата
        if re.match(self.GITHUB_PAT_PATTERN, token):
            metadata['format_valid'] = True
            
            if token.startswith('github_pat_'):
                metadata['token_version'] = 'fine_grained'
            elif token.startswith('ghp_'):
                metadata['token_version'] = 'classic'
            else:
                metadata['token_version'] = 'oauth'
            
            logger.info(f"GitHub token validated: {metadata['token_version']}")
            return True, metadata
        
        return False, metadata
    
    def validate_api_key(self, api_key: str, service: str = 'generic') -> Tuple[bool, Dict]:
        """
        Валидировать API key.
        
        Args:
            api_key: ключ API
            service: название сервиса
        
        Returns:
            (is_valid, metadata)
        """
        metadata = {
            'service': service,
            'format_valid': False,
            'length': len(api_key) if api_key else 0
        }
        
        if not api_key:
            return False, metadata
        
        if re.match(self.API_KEY_PATTERN, api_key):
            metadata['format_valid'] = True
            return True, metadata
        
        return False, metadata
    
    def validate_jwt(self, jwt_token: str) -> Tuple[bool, Dict]:
        """
        Валидировать JWT token.
        
        Returns:
            (is_valid, payload)
        """
        try:
            # Проверка формата JWT (header.payload.signature)
            parts = jwt_token.split('.')
            if len(parts) != 3:
                return False, {'error': 'Invalid JWT format'}
            
            # Здесь можно добавить полную валидацию JWT
            # используя PyJWT или python-jose
            
            return True, {'format': 'valid', 'parts': len(parts)}
            
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            return False, {'error': str(e)}
