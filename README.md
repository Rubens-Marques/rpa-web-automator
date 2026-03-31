# rpa-web-automator

> Toolkit RPA para automação de processos web com Selenium — formulários, extração de dados, relatórios.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python)
![Selenium](https://img.shields.io/badge/Selenium-4.27-43B02A?style=flat&logo=selenium)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

## Sobre

Base reutilizável para automações RPA web. Substitui processos manuais repetitivos em sistemas que não têm API — portais de fornecedores, sistemas legados, painéis web, formulários.

**Problema resolvido:** Processos que exigem acesso manual a sistemas web todos os dias podem ser automatizados com scripts configuráveis.

## Features

- `WebAutomator` — base class com métodos comuns (navegar, clicar, preencher, esperar)
- Screenshot automático em caso de erro
- Suporte a headless (sem abrir janela)
- `FormFiller` — automação de preenchimento de formulários
- Exemplos prontos para adaptar

## Instalação

```bash
git clone https://github.com/Rubens-Marques/rpa-web-automator
cd rpa-web-automator
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Chrome é instalado automaticamente via `webdriver-manager`.

## Como usar

```python
from src.rpa.base import WebAutomator

with WebAutomator(headless=True) as bot:
    bot.go("https://sistema.empresa.com/login")
    bot.type_into("#usuario", "seu_usuario")
    bot.type_into("#senha", "sua_senha")
    bot.click("#btn-entrar")
```

```bash
python examples/example_google_search.py
```

## Testes

```bash
pytest tests/ -v
```

## Licença

MIT © Rubens Marques
