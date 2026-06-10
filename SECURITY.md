# Política de Segurança

## Modelo de segurança

A **Barra de Uso de IA** foi desenhada para tocar em credenciais com o **mínimo
de privilégio possível**:

- **Somente leitura.** O app apenas **lê** os tokens OAuth já gravados pelos CLIs
  oficiais (`claude login` / `codex login`). Ele **nunca escreve, renova ou apaga**
  esses arquivos.
- **Tokens ficam só em memória.** O conteúdo do token é usado apenas para a
  chamada HTTP de consulta de uso e **nunca é logado, persistido em disco, nem
  incluído em mensagens de erro/UI**.
- **Sem segredos no repositório.** Não há `.env`, chaves de API ou credenciais
  versionadas. O `.gitignore` bloqueia, por precaução, `.env*`, `*.credentials.json`,
  `auth.json`, `*.pem`, `*.key` e padrões correlatos.
- **OPENAI_API_KEY não é aceita.** A leitura de credenciais do Codex aceita
  apenas o token OAuth do CLI. Uma `OPENAI_API_KEY` eventualmente presente no
  `auth.json` é **deliberadamente ignorada** — é uma credencial de escopo mais
  amplo que não deve ser enviada como `Bearer` ao endpoint de uso.

## De onde vêm as credenciais

| Provider | Arquivo lido (read-only)                          |
|----------|---------------------------------------------------|
| Claude   | `%USERPROFILE%\.claude\.credentials.json`         |
| Codex    | `%USERPROFILE%\.codex\auth.json`                  |

Esses arquivos são gerados e mantidos pelos próprios CLIs. Este app não os cria
nem os modifica.

## Endpoints consultados

Os endpoints de uso **não são documentados oficialmente** e podem mudar sem
aviso:

- `https://api.anthropic.com/api/oauth/usage`
- `https://chatgpt.com/backend-api/wham/usage`

O parsing é defensivo: qualquer mudança de schema degrada para um estado de
erro visível na UI, sem quebrar o app nem expor dados.

## Como reportar uma vulnerabilidade

Se você encontrar um problema de segurança, **não abra uma issue pública**.
Em vez disso, abra um **Security Advisory** privado no GitHub (aba *Security* →
*Report a vulnerability*) ou entre em contato diretamente com o mantenedor.

Descreva o passo a passo de reprodução e o impacto. Faremos o possível para
responder rapidamente.
