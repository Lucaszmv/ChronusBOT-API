import requests
import logging
import time
from modules.core.core_fingerprint import CLIENT_ID

logger = logging.getLogger(__name__)

def verificar_canal_online(canal_nome: str) -> tuple[bool, str]:
    """
    Verifica se um canal está online usando a API da Twitch.
    Faz até 3 tentativas antes de confirmar que o canal está offline.
    
    Args:
        canal_nome (str): Nome do canal para verificar
        
    Returns:
        tuple[bool, str]: (status_online, mensagem_erro)
    """
    max_tentativas = 3
    tentativa = 0
    
    while tentativa < max_tentativas:
        tentativa += 1
        try:
            url = f"https://gql.twitch.tv/gql"
            
            query = {
                "operationName": "StreamMetadata",
                "query": """
                query StreamMetadata($channelLogin: String!) {
                    user(login: $channelLogin) {
                        id
                        stream {
                            id
                            type
                            viewersCount
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
            
            response = requests.post(url, headers=headers, json=query, timeout=10)
            
            # Verifica erros HTTP
            if response.status_code == 404:
                if tentativa < max_tentativas:
                    time.sleep(2)
                    continue
                return False, f"Canal '{canal_nome}' não encontrado"
            elif response.status_code == 429:
                if tentativa < max_tentativas:
                    time.sleep(2)
                    continue
                return False, "Limite de requisições atingido"
            elif response.status_code != 200:
                if tentativa < max_tentativas:
                    time.sleep(2)
                    continue
                return False, f"Erro HTTP {response.status_code}"
                
            try:
                data = response.json()
            except ValueError:
                if tentativa < max_tentativas:
                    time.sleep(2)
                    continue
                return False, "Resposta inválida da API"
                
            # Verifica se o usuário existe
            user_data = data.get('data', {}).get('user')
            if user_data is None:
                if tentativa < max_tentativas:
                    time.sleep(2)
                    continue
                return False, f"Canal '{canal_nome}' não existe"
                
            # Verifica se está online
            stream_data = user_data.get('stream')
            if stream_data is None:
                if tentativa < max_tentativas:
                    time.sleep(2)
                    continue
                return False, f"Canal '{canal_nome}' está offline"
                
            return True, "Canal online"
            
        except requests.exceptions.Timeout:
            if tentativa < max_tentativas:
                time.sleep(2)
                continue
            return False, "Timeout ao verificar canal"
        except requests.exceptions.ConnectionError:
            if tentativa < max_tentativas:
                time.sleep(2)
                continue
            return False, "Erro de conexão ao verificar canal"
        except Exception as e:
            if tentativa < max_tentativas:
                time.sleep(2)
                continue
            logger.error(f"Erro ao verificar status do canal: {str(e)}")
            return False, f"Erro ao verificar canal: {str(e)}"
            
    return False, f"Canal '{canal_nome}' está offline"