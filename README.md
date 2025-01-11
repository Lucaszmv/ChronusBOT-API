# ChronusBOT-API
Bot para processamento de streams da Twitch, com suporte a detecção de anúncios e gerenciamento de playlists M3U8.

## 🚀 Funcionalidades
- Geração de fingerprints de navegador
- Gerenciamento de tokens de acesso
- Processamento de playlists M3U8
- Detecção e rastreamento de anúncios
- Simulação de download de segmentos
- Sistema de buffer adaptativo
- Suporte a múltiplas qualidades de stream

## 📋 Pré-requisitos
- Python 3.8 ou superior
- Poetry para gerenciamento de dependências

## 🔧 Instalação
1. Clone o repositório: 
    bash
    git clone https://github.com/Lucaszmv/ChronusBOT-API.git
    cd ChronusBOT-API

2. Instale as dependências:
    poetry install
   
## 🎮 Uso
1. Ative o ambiente virtual:
    poetry shell

2. Execute o bot:
    python main.py

## 📊 Funcionalidades Principais
- **Detecção de Anúncios**: Identifica e processa automaticamente pods de anúncios
- **Buffer Adaptativo**: Ajusta o buffer baseado na velocidade da stream
- **Multi-qualidade**: Suporte a diferentes qualidades de stream
- **Logging**: Sistema completo de logs para monitoramento

## 🛠️ Construído com
- [Python](https://www.python.org/) - Linguagem de programação
- [Poetry](https://python-poetry.org/) - Gerenciamento de dependências
- [Requests](https://requests.readthedocs.io/) - Requisições HTTP
- [Colorama](https://pypi.org/project/colorama/) - Cores no terminal

## 📄 Licença
Este projeto está sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes

## ✒️ Autor
* **Lucas** - *Desenvolvimento* - [Lucaszmv](https://github.com/Lucaszmv)

## 📝 Notas
- Este bot é apenas para fins educacionais
- Não nos responsabilizamos pelo uso indevido desta ferramenta
- Respeite os termos de serviço da Twitch