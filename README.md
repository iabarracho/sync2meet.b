# Sync2meet

Automatiza reuniões: **Agenda → Gravação → Transcrição → Ata → Aprovação → Distribuição**.

## Arrancar (Windows)

1. **1-INSTALAR.cmd** — primeira vez
2. **ARRANCAR.cmd** — só tu no PC
3. **ARRANCAR-REDE.cmd** — partilhar com colegas na mesma rede
4. **parar-tudo.cmd** — parar

- Só tu: http://127.0.0.1:3000
- Empresa (mesma WiFi/rede): `http://TEU-IP:3000` (o script mostra o IP)

## Configurar

Tudo em **`backend/.env`** (criado automaticamente na instalação).

Abre o ficheiro e configura:

```env
OPENAI_API_KEY=...          # só para gerar ata/agenda (GPT-4o-mini)
FASTER_WHISPER_MODEL=base     # transcrição local (sem API)
FASTER_WHISPER_DEVICE=cpu
```

Reinicia: `parar-tudo.cmd` → `ARRANCAR.cmd`

Na primeira transcrição, o faster-whisper descarrega o modelo (precisa de internet uma vez).

Confirma em `/api/health`: `"openai": true` (só indica chave GPT configurada)

### Email e Slack (opcional)

No mesmo `backend/.env`:

```env
SMTP_HOST=...
SMTP_USER=...
SMTP_PASSWORD=...

SLACK_BOT_TOKEN=...
```

Sem estes valores, enviar email ou Slack devolve erro — não simula envio.

## Google Meet

1. Grava com extensão Chrome → download MP4/WEBM
2. Na reunião: **Carregar gravação** → **Transcrever** → **Gerar ata**

## Estrutura

```text
sync2meet/
├── backend/          # API + .env
├── frontend/         # App Next.js
├── ARRANCAR.cmd
└── 1-INSTALAR.cmd
```

## Git

Repositório só nesta pasta (`sync2meet/`). **Nunca** commitar:

- `backend/.env`
- `backend/sync2meet.db`
- `backend/storage/`
- `node_modules/`, `.venv/`, `.next/`
