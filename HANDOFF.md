# Handoff — como este projeto nasceu (2026-08-06)

Notas de arranque, para não se perder o contexto da sessão em que isto foi montado.
Não é preciso ler para usar o projeto — para isso basta o [README.md](README.md).

## A decisão

A ideia inicial era um **bot de Telegram** que recebesse fotos e descrições de treino
(existe um protótipo em `c:\dev\rzcoach\telegram-bot\`, em Python). Foi abandonada quando
se percebeu que esse bot era só um wrapper do `claude -p` — ou seja, o cérebro era o Claude
Code de qualquer maneira.

Falar diretamente com o Claude Code sobre um repositório git resolve de graça tudo o que o
bot exigiria em código: escrita e commit nativos, troca de modelo com `/model`, nada de
processo sempre a correr no PC, nada de fotos acumuladas em disco.

**O trade-off aceite:** perde-se a ergonomia do Telegram (câmara em dois toques, no ginásio).
Serve bem para registar no fim do treino, sentado; menos bem para registar série a série.
O protótipo do bot ficou guardado como plano B, não foi apagado.

## A arquitetura

Duas coisas separadas, deliberadamente:

| | Onde |
| --- | --- |
| **Registo pessoal de treino** (este repo) | `c:\dev\rz\rzpt-claude` → github.com/rizamith/rzpt-claude (privado) |
| **App PT+nutrição para vender** (Expo + Supabase) | `c:\dev\rz\rzpt_app` |

São projetos sem código partilhado: este é uma ferramenta pessoal com dados em git, o outro
é um produto multi-utilizador com Supabase e RLS. O `rzpt_app` tem o seu próprio
`CONVERSATION_SUMMARY.md`.

O `CLAUDE.md` deste repo **é** o sistema — não há código. Está lá o comportamento do PT e o
perfil pessoal, versionado em git para haver histórico de como evoluiu.

## Escolhas que valem a pena não desfazer sem pensar

- **Perfil dentro do `CLAUDE.md`**, não em ficheiro à parte — garante que é sempre carregado
  em cada sessão.
- **Análises em Opus, registo em Sonnet.** O `CLAUDE.md` manda parar e pedir `/model opus`
  antes de qualquer análise, em vez de confiar na memória do utilizador.
- **Ambiguidade → perguntar, nunca assumir.** Um dígito mal lido numa foto de balança
  contamina todas as análises futuras.
- **Histórico não se reescreve** sem autorização explícita, mesmo que um valor pareça errado.
- **Fotos não entram no repo** — bloqueadas no `.gitignore`, e o registo escrito é o que fica.
- **Autenticação por Git Credential Manager** (já vinha com o Git), configurado só neste repo
  (`credential.helper = manager`, local). Não há PAT nem `gh` instalado, e não é preciso.

## Estado

- Estrutura criada, `CLAUDE.md` escrito, primeiro commit feito, remote ligado e push feito.
- O perfil ("o que sabes sobre mim") está todo a `_(a definir)_` — preenche-se na conversa.
- Ainda não existe nenhum registo real: `registos/` só tem o `_TEMPLATE.md`.

**Próximo passo:** primeiro registo a sério — descrever um treino ou enviar foto da balança,
e confirmar que o ciclo extrair → escrever → commit → push funciona ponta a ponta.
