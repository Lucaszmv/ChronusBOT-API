import random
import requests

def get_random_proxy():
    with open('proxy.txt', 'r') as f:
        proxies = f.read().splitlines()
    proxy = random.choice(proxies)
    
    if ':' in proxy:
        parts = proxy.split(':')
        if len(parts) == 2:
            return f"http://{proxy}"
        elif len(parts) == 4:
            return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    
    return None

def get_external_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json')
        return response.json()['ip']
    except Exception as e:
        print(f"Erro ao obter IP externo: {e}")
        return None