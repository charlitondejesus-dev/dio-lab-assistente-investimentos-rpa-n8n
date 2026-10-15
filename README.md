# Assistente de Investimentos com RPA, n8n e IA Generativa

Projeto final do curso "Criando um Processo de RPA com N8N e Python" (DIO).

O fluxo extrai clientes de uma pagina web com Python, envia os dados ao n8n por webhook, cruza cada cliente com um catalogo de produtos de investimento e gera mensagens personalizadas. Na versao completa, uma LLM redige e-mails diferentes para cada cliente e o Gmail faz o envio.

## Arquitetura

```
Python (BeautifulSoup)  ->  Webhook n8n  ->  Buscar CSV  ->  Normalizar CSV
                                 |                                |
                                 +----------->  Merge  <---------+
                                                  |
                                          Gerar mensagens
                                                  |
                                          Validar e-mail (regex)
                                   verdadeiro /            \ falso
                          Gerar e-mail (LLM)              Registrar invalido
                          Normalizar e-mail LLM                |
                              Enviar Gmail                     |
                                   \                          /
                                    Merge resultados -> Resumo -> Responder Webhook
```

## Estrutura do repositorio

| Caminho | Funcao |
|---|---|
| `index.html` | Pagina de clientes, publicada no GitHub Pages (fonte do scraping) |
| `investimentos.csv` | Catalogo de produtos por perfil, minimo de aplicacao e rentabilidade |
| `rpa/rpa_clientes.py` | Script de RPA (execucao local) |
| `rpa/rpa_clientes.ipynb` | Mesmo script como notebook para o Google Colab |
| `n8n/workflow_mvp.json` | Workflow exportado com mensagens estaticas |
| `n8n/workflow_completo.json` | Workflow exportado com LLM, validacao de e-mail e Gmail |
| `docs/roteiro_video.txt` | Roteiro para gravar a demonstracao |

## Como executar

1. Faca o fork do repositorio e ative o GitHub Pages (Settings, Pages, branch `main`, pasta raiz).
2. Substitua `charlitondejesus-dev` e `dio-lab-assistente-investimentos-rpa-n8n` pela sua URL do Pages em `rpa/rpa_clientes.py` e na URL do no "Buscar CSV" dos workflows.
3. No n8n, importe `workflow_mvp.json` (Workflows, Import from file) e clique em "Listen for test event" no no Webhook.
4. Copie a Test URL do webhook para a variavel `URL_WEBHOOK` do script e execute no Colab (ou `python rpa/rpa_clientes.py`).
5. Para a versao completa, importe `workflow_completo.json`, crie a credencial do Gemini (Header Auth com o nome x-goog-api-key) e a do Gmail e repita o passo 4. Em producao, ative o workflow e use a Production URL (`/webhook/clientes`).

## Decisoes tecnicas

**Webhook como ponto de entrada.** O n8n recebe os dados via POST em `/clientes`. O modo de resposta "Respond to Webhook" mantem a chamada aberta ate o fim do fluxo, entao o script Python recebe o resumo da execucao.

**Normalizacao do saldo no Python.** O valor aparece na pagina como "R$ 12.500,00". A conversao para numero acontece no script, para que o n8n receba dados limpos e a comparacao com o minimo do produto seja confiavel.

**CSV tratado em um no de codigo.** O HTTP Request devolve o CSV como texto. Um no Code transforma cada linha em um item com campos tipados (`minimo` e `rentabilidade` numericos), formato que o restante do fluxo consome.

**No Merge no modo append.** Reune os dados do webhook e os produtos em um unico ponto. Foi mantido mesmo com apenas duas fontes porque novas fontes de dados entram sem alterar o restante do fluxo.

**Regra de correspondencia.** Cada cliente recebe o produto do seu perfil com maior rentabilidade entre os que o saldo permite contratar. Se o saldo estiver abaixo do minimo de todos, a mensagem informa o valor necessario em vez de sugerir um produto inviavel.

**Variedade nas mensagens.** A versao estatica alterna tres modelos de texto entre os clientes. A versao com IA recebe tambem um estilo (amigavel, objetivo ou consultivo) por cliente, alem de temperatura 0.9, o que reduz a repeticao.

**Escolha do provedor de IA.** O fluxo usa a API do Gemini (modelo gemini-3.6-flash) por meio de um no HTTP Request, porque o Google AI Studio oferece camada gratuita e a chamada nao depende de um no especifico de um provedor. Como o modelo e apenas uma URL e um corpo JSON, trocar por outro provedor exige alterar so esse no e o no de normalizacao. Na camada gratuita o conteudo enviado pode ser usado pelo provedor para melhorar produtos, por isso o projeto usa apenas dados ficticios de clientes. O limite de requisicoes por minuto da camada gratuita e respeitado enviando um cliente por vez, com intervalo de 15 segundos entre as chamadas (opcao Batching do no HTTP Request), alem de novas tentativas automaticas.

**Cuidados com a LLM.** O prompt proibe prometer ganhos e exige o aviso de que rentabilidade passada nao garante resultados futuros. A resposta e solicitada em JSON (`assunto` e `corpo_html`). Se a LLM devolver algo fora do formato ou ficar indisponivel (erro 503 ou limite de requisicoes), o no de chamada segue o fluxo mesmo com erro e o no de normalizacao usa a mensagem estatica como contingencia, entao nenhum cliente fica sem e-mail. O campo origem_texto indica se o texto veio da LLM ou da contingencia. O no refaz a chamada automaticamente em caso de falha de rede ou de limite de requisicoes.

**Validacao antes do envio.** Um no If aplica expressao regular ao e-mail. Enderecos invalidos nao consomem chamadas da LLM nem do Gmail e seguem por um ramo proprio, que alimenta a lista `emails_invalidos` no retorno. Esse ramo pode ser estendido, por exemplo, para contato por telefone.

**Falha de envio nao interrompe o lote.** O no do Gmail esta configurado para continuar em caso de erro, e o resumo final contabiliza enviados, falhas e invalidos.

**Dados limpos antes da IA.** A ordem do fluxo (extrair, normalizar, cruzar, validar e so depois gerar texto) segue a ideia de que a qualidade da saida da LLM depende da qualidade dos dados de entrada.

## Testes realizados

- Script Python: extracao dos 6 clientes e envio do JSON a um webhook simulado, com saldos convertidos corretamente.
- Logica de cruzamento e geracao de mensagens: executada com os dados de exemplo, cobrindo saldo suficiente, saldo abaixo do minimo e e-mail invalido.
- Workflow completo no n8n: execucao ponta a ponta com o script do Colab, a API do Gemini e o Gmail. Os e-mails gerados chegaram na caixa de entrada de teste, com textos diferentes entre os clientes, e o cliente com e-mail invalido foi separado pelo ramo falso do no If.
- Falhas transitorias do provedor de IA (erro 503 e limite de requisicoes) apareceram durante os testes e foram tratadas com envio em lotes de um item, tentativas automaticas e mensagem de contingencia.

## Limitacoes e proximos passos

- Os e-mails da pagina de exemplo sao ficticios. Nos testes, o destinatario do no Gmail foi trocado por um endereco proprio. Para envio real, usar o campo de e-mail do cliente (`{{ $json.to }}`).
- O n8n gratuito e o Colab podem exceder o tempo com muitos clientes. Para lotes grandes, usar o no Loop Over Items.
- Evolucoes possiveis: ramo de WhatsApp para e-mails invalidos, agendamento diario com Schedule Trigger e registro dos envios em planilha.
