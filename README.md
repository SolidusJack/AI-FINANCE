# AI-FINANCE

Aplicação web para registro e acompanhamento de gastos, com API REST em FastAPI, persistência em MySQL e interface simples em português com suporte a lançamento manual e por voz.

![Python](https://img.shields.io/badge/Python-61.8%25-3776AB?logo=python&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-22.9%25-F7DF1E?logo=javascript&logoColor=black)
![HTML](https://img.shields.io/badge/HTML-15.3%25-E34F26?logo=html5&logoColor=white)
![Status](https://img.shields.io/badge/status-em%20desenvolvimento-blue)

## Sumário

- [Visão geral](#visão-geral)
- [Recursos atuais](#recursos-atuais)
- [Arquitetura e estrutura](#arquitetura-e-estrutura)
- [Pré-requisitos](#pré-requisitos)
- [Instalação e configuração local](#instalação-e-configuração-local)
- [Executando o projeto](#executando-o-projeto)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [API (endpoints confirmados)](#api-endpoints-confirmados)
- [Segurança](#segurança)
- [Desenvolvimento e contribuição](#desenvolvimento-e-contribuição)
- [Licença](#licença)
- [Aviso importante](#aviso-importante)

## Visão geral

O **AI-FINANCE** centraliza registros financeiros do dia a dia em uma única interface web.  
O backend expõe endpoints para CRUD de transações e totalização por categoria. Também há um endpoint que recebe áudio, transcreve com IA e extrai uma transação válida para salvar no banco.

## Recursos atuais

- Cadastro manual de gastos (título, valor, categoria e data).
- Cadastro por voz com envio de áudio para `/api/voice-transaction`.
- Listagem de transações e consulta de totais por categoria.
- Validação de categorias em português no backend.
- Proteção dos endpoints de transações por header `x-api-key`.
- Frontend servido pelo próprio backend em `GET /`.

## Arquitetura e estrutura

```text
AI-FINANCE/
├── backend/
│   ├── app.py              # API FastAPI e rotas principais
│   ├── database.py         # Conexão SQLAlchemy e sessão
│   ├── models.py           # Modelo Transaction
│   ├── schemas.py          # Schemas/validações Pydantic
│   ├── settings.py         # Carregamento de variáveis de ambiente
│   └── migrations/
│       └── 001_add_transaction_title.sql
├── frontend/
│   ├── index.html          # Interface principal
│   └── static/
│       ├── app.js          # Lógica do frontend e chamadas da API
│       └── styles.css      # Estilos da interface
├── .env.example
└── requirement.txt
```

## Pré-requisitos

- Python 3.10+ (recomendado)
- MySQL 8+ (ou compatível com a URL configurada)
- `pip` para instalar dependências

## Instalação e configuração local

1. **Clone o repositório**

   ```bash
   git clone https://github.com/SolidusJack/AI-FINANCE.git
   cd AI-FINANCE
   ```

2. **Crie e ative um ambiente virtual**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   > No Windows (PowerShell): `.\.venv\Scripts\Activate.ps1`

3. **Instale as dependências**

   ```bash
   pip install -r requirement.txt
   ```

4. **Crie o arquivo de ambiente**

   ```bash
   cp .env.example .env
   ```

5. **Configure o banco MySQL e as variáveis no `.env`**

   Exemplo de `URL_DATABASE`:

   ```env
   URL_DATABASE=mysql+pymysql://<usuario>:<senha>@localhost:3306/ai_finance
   ```

6. **Crie o banco no MySQL** (se ainda não existir):

   ```sql
   CREATE DATABASE ai_finance CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

> Observação: o backend executa `Base.metadata.create_all(...)` ao iniciar e cria a tabela `transactions` se necessário.

## Executando o projeto

1. **Inicie o backend (API + frontend estático)**

   ```bash
   uvicorn backend.app:app --reload
   ```

2. **Acesse no navegador**

- Frontend: `http://127.0.0.1:8000/`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

## Variáveis de ambiente

As variáveis abaixo são lidas a partir do arquivo `.env`:

| Variável | Obrigatória | Descrição |
| --- | --- | --- |
| `URL_DATABASE` | Sim | URL de conexão SQLAlchemy com o MySQL. |
| `OPENROUTER_API_KEY` | Sim (voz) | Chave da OpenRouter para extração estruturada da transação via IA. |
| `GROQ_API_KEY` | Sim (voz) | Chave da Groq para transcrição de áudio. |
| `OPENROUTER_MODEL` | Não | Modelo usado na extração da transação (há valor padrão no código). |
| `API_KEY` | Sim | Chave exigida no header `x-api-key` para endpoints protegidos. |

## API (endpoints confirmados)

### Sem autenticação

- `GET /` → serve `frontend/index.html`
- `GET /health` → status da API

### Com `x-api-key`

- `GET /transactions` → lista transações (`skip`, `limit`)
- `GET /transactions/totals` → total geral e total por categoria
- `GET /transactions/{transaction_id}` → detalha transação
- `POST /transactions` → cria transação manual
- `PUT /transactions/{transaction_id}` → atualiza transação
- `DELETE /transactions/{transaction_id}` → exclui transação
- `POST /api/voice-transaction` → cria transação via áudio (`multipart/form-data`, campo `file`)

### Exemplos rápidos (cURL)

```bash
# Criar transação manual
curl -X POST "http://127.0.0.1:8000/transactions" \
  -H "Content-Type: application/json" \
  -H "x-api-key: SUA_API_KEY" \
  -d '{"title":"Almoço","amount":42.50,"category":"Alimentação"}'
```

```bash
# Listar transações
curl "http://127.0.0.1:8000/transactions?skip=0&limit=20" \
  -H "x-api-key: SUA_API_KEY"
```

```bash
# Totais por categoria
curl "http://127.0.0.1:8000/transactions/totals" \
  -H "x-api-key: SUA_API_KEY"
```

## Segurança

- **Nunca** commite chaves de API, senhas ou arquivos `.env`.
- Mantenha credenciais apenas em variáveis de ambiente locais/seguras.
- Use chaves distintas para desenvolvimento e produção.
- Revogue e rotacione chaves em caso de exposição.

## Desenvolvimento e contribuição

1. Crie uma branch para sua alteração.
2. Faça mudanças pequenas e objetivas.
3. Valide localmente a execução da API (`uvicorn backend.app:app --reload`).
4. Abra um Pull Request descrevendo o que foi alterado.

## Licença

Até o momento, **não há um arquivo de licença definido** no repositório.  
Se necessário, adicione uma licença (ex.: MIT) antes de distribuição formal.

## Aviso importante

As informações financeiras geradas com apoio de IA têm caráter informativo e **não substituem** orientação profissional de contabilidade, planejamento financeiro ou investimentos.
