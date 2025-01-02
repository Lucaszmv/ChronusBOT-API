import json
import logging
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
import random

logger = logging.getLogger(__name__)

@dataclass
class TwitchAccount:
    username: str
    oauth_token: str
    in_use: bool = False

class AuthManager:
    def __init__(self):
        self.accounts: Dict[int, TwitchAccount] = {}
        self.accounts_file = Path("configs/accounts.txt")
        self.available_accounts: List[TwitchAccount] = []
        self.load_accounts()
        
    def load_accounts(self):
        """Carrega contas do arquivo de configuração."""
        try:
            if self.accounts_file.exists():
                with open(self.accounts_file, 'r') as f:
                    # Lê cada linha como um token
                    tokens = [line.strip() for line in f if line.strip()]
                    for token in tokens:
                        # Cria uma conta usando o token como oauth_token
                        # Username será extraído do token ou gerado aleatoriamente
                        account = TwitchAccount(
                            username=f"user_{len(self.available_accounts)+1}",  # Nome temporário
                            oauth_token=token
                        )
                        self.available_accounts.append(account)
                logger.info(f"Carregadas {len(self.available_accounts)} contas do accounts.txt")
        except Exception as e:
            logger.error(f"Erro ao carregar contas: {str(e)}")
            
    def get_account(self, bot_id: int) -> Optional[TwitchAccount]:
        """Obtém uma conta disponível para o bot."""
        try:
            if bot_id in self.accounts:
                return self.accounts[bot_id]
                
            available = [acc for acc in self.available_accounts if not acc.in_use]
            if not available:
                # Se não há contas, libera todas e tenta novamente
                for acc in self.available_accounts:
                    acc.in_use = False
                available = self.available_accounts
                
            if available:
                account = random.choice(available)
                account.in_use = True
                self.accounts[bot_id] = account
                return account
                
            logger.error(f"BOT {bot_id}: Não há contas disponíveis mesmo após reset")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao obter conta: {str(e)}")
            return None
        
    def release_account(self, bot_id: int):
        """Libera uma conta após uso."""
        if bot_id in self.accounts:
            self.accounts[bot_id].in_use = False

# Instância global
auth_manager = AuthManager()

def get_auth_manager():
    return auth_manager 