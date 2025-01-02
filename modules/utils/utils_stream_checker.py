import requests
import logging
from modules.core.core_fingerprint import CLIENT_ID

logger = logging.getLogger(__name__)

def verificar_canal_online(canal_nome: str) -> bool:
    """
    Verifica se um canal está online usando a API da Twitch.
    """
    try:
        url = f"https://gql.twitch.tv/gql"
        
        # Query GQL para verificar status do canal
        query = {
            "operationName": "StreamMetadata",
            "query": """
            query StreamMetadata($channelLogin: String!) {
                user(login: $channelLogin) {
                    stream {
                        id
                    }
                }
            }
            """,
            "variables": {
                "channelLogin": canal_nome
            }
        }
        
        headers = {
            'Client-Id': CLIENT_ID,
            'Content-Type': 'application/json',
        }
        
        response = requests.post(url, headers=headers, json=query)
        data = response.json()
        
        # Se stream não for None, o canal está online
        return data.get('data', {}).get('user', {}).get('stream') is not None
        
    except Exception as e:
        logger.error(f"Erro ao verificar status do canal: {e}")
        # Em caso de erro, assumimos que o canal está online para tentar conexão
        return True