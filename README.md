# Barra de Uso de IA (v1)

App de bandeja (system tray) para Windows que mostra o uso de **Claude** e
**Codex** lendo os tokens OAuth locais e consultando os endpoints de uso de
cada CLI.

> Inspirado no [akitaonrails/ai-usagebar](https://github.com/akitaonrails/ai-usagebar).
> Esta v1 cobre apenas Claude e Codex.

## Como rodar (dev)

```bat
python -m pip install -r requirements.txt
python main.py
```

O ícone aparece na bandeja; o tooltip e o menu mostram o uso de cada provider.
O app lê (somente leitura) `%USERPROFILE%\.claude\.credentials.json` e
`%USERPROFILE%\.codex\auth.json`. Se um token estiver ausente/expirado, a UI
orienta a rodar `claude login` / `codex login`.

## Testes

```bat
python -m unittest discover -s tests -v
```

(Os testes são `unittest` da stdlib — também rodam com `pytest` se preferir.)

## Build do .exe

```bat
build.bat
```

Gera um pacote portátil via PyInstaller (saída em `C:\tmp\BarraUsoIA_*`).

## Notas importantes

- **Endpoints não documentados:** `api.anthropic.com/api/oauth/usage` e
  `chatgpt.com/backend-api/wham/usage` podem mudar sem aviso. O parsing é
  tolerante; valide o schema real empiricamente antes de confiar nos números.
- **Segurança:** tokens nunca são logados nem persistidos; leitura é read-only.

## Fora da v1

Refresh automático de token, janela de detalhes/gráficos, histórico, alertas de
limite, suporte a GLM/OpenRouter/DeepSeek, múltiplas contas, instalador.
