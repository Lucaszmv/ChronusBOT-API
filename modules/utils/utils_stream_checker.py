import requests
import logging
import urllib3

# Suprime avisos SSL
urllib3.disable_warnings()

logger = logging.getLogger(__name__)

def verificar_canal_online(canal_nome: str) -> bool:
    """
    Verifica se um canal está online na Twitch verificando a página do canal.
    
    Args:
        canal_nome (str): Nome do canal para verificar
        
    Returns:
        bool: True se o canal estiver online, False caso contrário
    """
    try:
        session = requests.Session()
        session.verify = False
        response = session.get(f'https://www.twitch.tv/{canal_nome}')
        return 'isLiveBroadcast' in response.text
    except Exception as e:
        logger.error(f"Erro ao verificar status do canal: {e}")
        return False 