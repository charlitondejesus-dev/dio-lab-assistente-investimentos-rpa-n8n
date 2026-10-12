"""
RPA de extracao de clientes.

Le a tabela de clientes publicada no GitHub Pages (web scraping com
BeautifulSoup), normaliza os campos e envia o resultado ao webhook do n8n.

Uso local:    python rpa/rpa_clientes.py
Uso no Colab: abrir rpa/rpa_clientes.ipynb e executar as celulas.
"""
import re
import sys
import requests
from bs4 import BeautifulSoup

# Ajuste as duas URLs abaixo antes de executar.
URL_SITE = "https://charlitondejesus-dev.github.io/dio-lab-assistente-investimentos-rpa-n8n/"
# Em teste: .../webhook-test/clientes   |   Em producao: .../webhook/clientes
URL_WEBHOOK = "https://rpa-investimentos-cjs.app.n8n.cloud/webhook-test/clientes"

TIMEOUT = 120  # a geracao dos e-mails pela LLM pode demorar


def saldo_para_float(texto: str) -> float:
    """Converte 'R$ 12.500,00' em 12500.0."""
    limpo = re.sub(r"[^\d,]", "", texto).replace(",", ".")
    return float(limpo) if limpo else 0.0


def extrair_clientes(url: str) -> list[dict]:
    resposta = requests.get(url, timeout=30)
    resposta.raise_for_status()
    resposta.encoding = "utf-8"
    sopa = BeautifulSoup(resposta.text, "html.parser")

    tabela = sopa.find("table", id="tabela-clientes") or sopa.find("table")
    if tabela is None:
        raise ValueError("Tabela de clientes nao encontrada na pagina.")

    clientes = []
    for linha in tabela.find("tbody").find_all("tr"):
        celulas = [c.get_text(strip=True) for c in linha.find_all("td")]
        if len(celulas) < 4:
            continue
        nome, email, saldo, perfil = celulas[:4]
        clientes.append({
            "nome": nome,
            "email": email,
            "saldo": saldo_para_float(saldo),
            "perfil": perfil,
        })
    return clientes


def enviar_ao_webhook(clientes: list[dict], url: str) -> dict:
    resposta = requests.post(url, json={"clientes": clientes}, timeout=TIMEOUT)
    resposta.raise_for_status()
    return resposta.json()


def main() -> int:
    try:
        clientes = extrair_clientes(URL_SITE)
        print(f"{len(clientes)} clientes extraidos.")
        retorno = enviar_ao_webhook(clientes, URL_WEBHOOK)
        print("Resposta do n8n:")
        print(retorno)
        return 0
    except requests.RequestException as erro:
        print(f"Falha de comunicacao: {erro}")
    except ValueError as erro:
        print(f"Falha de leitura dos dados: {erro}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
