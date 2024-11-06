"""
Módulo para gerenciamento de sessão HTTP.

Este módulo contém a configuração da sessão HTTP reutilizável
utilizada em toda a aplicação para fazer requisições à API da Twitch.

A sessão mantém cookies e conexões TCP persistentes, melhorando
a performance e reduzindo o overhead das requisições.

Attributes:
    session (requests.Session): Objeto de sessão do requests que será
        reutilizado em todas as requisições HTTP da aplicação.
"""

import requests

session = requests.Session()