# Plano: Barra de Uso de IAs (Claude + Codex) para Windows

## Contexto

O usuário quer um app de bandeja do sistema (system tray) para Windows, inspirado no
[akitaonrails/ai-usagebar](https://github.com/akitaonrails/ai-usagebar) (Rust, Waybar/Linux,
mostra uso de Claude, Codex, GLM, OpenRouter, DeepSeek lendo tokens OAuth locais e
chamando endpoints não documentados).

Para esta v1, o escopo é **somente Claude e Codex**. O projeto já existe em
`G:\Meu Drive\Scripts\Projeto_Barra_Uso_IA`, atualmente um repo git novo (branch `main`,
1 commit) contendo apenas o scaffold do fluxo de revisão Claude/Codex
(`AGENTS.md`, `CLAUDE.md`, `.ai/`, `scripts/`, `docs/`) — sem código de app ainda.

O Codex CLI foi consultado para o planejamento (arquitetura, riscos, stack, MVP) e suas
recomendações foram incorporadas abaixo. As decisões de stack/escopo já foram confirmadas
com o usuário:

- **Stack:** Python + PyQt6, reaproveitando o padrão de tray já usado e validado em
  `G:\Meu Drive\Scripts\APPsPomodoro\pomodoro\ui\tray.py` (PyQt6 6.11, `QSystemTrayIcon`,
  `QMenu`, build via PyInstaller — ver `build.bat` e `requirements.txt` do Pomodoro).
- **UI v1:** ícone na bandeja + tooltip com resumo de uso + menu de contexto simples
  (sem janela de detalhes).
- **Auth v1:** somente leitura dos tokens OAuth locais (`~/.claude/.credentials.json` e
  `~/.codex/auth.json`, equivalentes a `%USERPROFILE%\.claude\...` e
  `%USERPROFILE%\.codex\...` no Windows). Sem refresh automático de token — se expirado/
  inválido, mostrar erro e orientar a rodar `claude login` / `codex login` novamente.

## Arquitetura / Estrutura de pastas

Dentro de `G:\Meu Drive\Scripts\Projeto_Barra_Uso_IA`, seguindo o padrão de organização do
Pomodoro (pastas `core/`, `ui/`, `assets/`, `main.py` na raiz, `requirements.txt`,
`build.bat`):

```
Projeto_Barra_Uso_IA/
  main.py                      # ponto de entrada: cria QApplication + SystemTray
  requirements.txt
  build.bat                    # PyInstaller, baseado no build.bat do Pomodoro
  assets/
    icon.png                   # ícone da bandeja (placeholder inicial)
  core/
    config.py                  # constantes: caminhos de credenciais, URLs, intervalo de refresh
    credentials.py             # leitura read-only de .claude/.credentials.json e .codex/auth.json
    providers/
      base.py                  # Protocol/ABC: UsageProvider.fetch() -> UsageSnapshot
      claude_provider.py        # chama api.anthropic.com/api/oauth/usage
      codex_provider.py         # chama chatgpt.com/backend-api/wham/usage
    models.py                  # dataclasses: UsageSnapshot, AuthState, UsageState
    refresh_scheduler.py        # QTimer periódico + "atualizar agora"
  ui/
    tray.py                    # SystemTray(QSystemTrayIcon) — ícone, menu, tooltip
    formatters.py               # formata UsageSnapshot -> texto do tooltip/menu
  tests/
    test_credentials.py         # leitura/ausência/arquivo inválido (com fixtures, sem tokens reais)
    test_providers.py           # parsing de payloads de uso (mock HTTP)
    test_formatters.py
```

(Os diretórios `.ai/`, `.claude/`, `AGENTS.md`, `CLAUDE.md`, `docs/`, `scripts/` do
scaffold de revisão permanecem como estão — não fazem parte do app.)

## Componentes principais

1. **`core/credentials.py`** — leitura read-only:
   - `read_claude_credentials()`: lê `%USERPROFILE%\.claude\.credentials.json`,
     extrai `access_token` (e `expires_at` se existir).
   - `read_codex_credentials()`: lê `%USERPROFILE%\.codex\auth.json`, extrai o
     token conforme o schema do Codex CLI.
   - Parsing **defensivo**: arquivo ausente/JSON inválido/campo faltando ->
     retorna `AuthState` (`missing` | `invalid_file` | `expired` | `ready`), nunca lança
     exceção para a UI. **Nunca loga o conteúdo do token.**

2. **`core/providers/claude_provider.py`** e **`codex_provider.py`** —
   implementam `UsageProvider.fetch(token) -> UsageSnapshot`:
   - Claude: `GET https://api.anthropic.com/api/oauth/usage` com
     `Authorization: Bearer <access_token>`.
   - Codex: `GET https://chatgpt.com/backend-api/wham/usage` com o token do
     `auth.json`.
   - Timeout curto (5–10s), tratamento de `401/403` -> `AuthState.expired`,
     erro de rede -> `UsageState.network_error`, payload inesperado ->
     `UsageState.parse_error` (a UI mostra "formato inesperado", não quebra).

3. **`core/models.py`** — `UsageSnapshot` (provider, usado, limite, percentual,
   reset, estado) e enums `AuthState` / `UsageState`, conforme sugestão do Codex.

4. **`core/refresh_scheduler.py`** — `QTimer` com intervalo configurável
   (default sugerido: 5–15 min) + método para "atualizar agora" (com debounce)
   chamado pelo menu da bandeja.

5. **`ui/tray.py`** — `SystemTray(QSystemTrayIcon)`, no mesmo estilo do
   `tray.py` do Pomodoro:
   - Tooltip com resumo: `Claude: usado/limite (%) · reset em Xh` e o
     equivalente para Codex (ou mensagem de erro/estado de auth).
   - Menu de contexto: status Claude, status Codex, "Atualizar agora", "Sair".
   - Cache do último snapshot válido para a UI não ficar vazia em falhas
     temporárias.

6. **Logging** — log simples (arquivo ou stdout) só com `provider`, `status
   HTTP/erro`, `timestamp`. Nunca headers/tokens/payload bruto de auth.

## MVP (v1) vs depois

**Incluído na v1:**
- Ícone de bandeja + tooltip + menu (status Claude/Codex, atualizar, sair).
- Leitura local read-only dos dois arquivos de credenciais.
- Chamada aos dois endpoints de uso, com tratamento de erro/expiração.
- Refresh periódico + manual.
- Testes unitários de credenciais (ausente/inválido/válido com fixture fake) e
  de parsing dos payloads de uso (com mocks).
- Empacotamento `.exe` via PyInstaller (`build.bat` adaptado do Pomodoro).

**Fora da v1 (registrar como ideia futura, não implementar agora):**
- Refresh automático de token OAuth.
- Janela de detalhes/gráficos, histórico (SQLite), notificações de limite.
- Suporte a GLM/OpenRouter/DeepSeek, múltiplas contas, auto-start, instalador `.msi`.

## Riscos conhecidos (do Codex)

- Endpoints `api.anthropic.com/api/oauth/usage` e
  `chatgpt.com/backend-api/wham/usage` são **não documentados** e podem mudar
  sem aviso — schema deve ser validado empiricamente antes de codar o parser
  final (com um exemplo de resposta real, sem expor tokens).
- Schema dos arquivos `.claude/.credentials.json` e `.codex/auth.json` também
  pode variar entre versões dos CLIs — parsing tolerante é obrigatório.
- Cuidado para nunca persistir/logar tokens.

## Verificação

- Rodar `python main.py` localmente e confirmar que o ícone aparece na
  bandeja, o tooltip mostra dados reais (lendo as credenciais já existentes
  no ambiente do usuário) e o menu funciona ("Atualizar agora", "Sair").
- Testar cenários de erro manualmente: renomear/mover temporariamente
  `.credentials.json`/`auth.json` para simular `missing`/`invalid_file` e
  conferir que a UI mostra o estado correto sem travar.
- Rodar `pytest` para os testes unitários de `credentials`, `providers` e
  `formatters`.
- Build final: rodar `build.bat` e verificar que o `.exe` gerado abre e exibe
  o ícone na bandeja.
