import requests

def verificar_canal_online(canal_nome: str) -> bool:
    """
    Verifica se um canal está online na Twitch verificando a página do canal.
    
    Args:
        canal_nome (str): Nome do canal para verificar
        
    Returns:
        bool: True se o canal estiver online, False caso contrário
    """
    try:
        response = requests.get(f'https://www.twitch.tv/{canal_nome}')
        return 'isLiveBroadcast' in response.text
    except Exception as e:
        print(f"Erro ao verificar status do canal: {e}")
        return False 