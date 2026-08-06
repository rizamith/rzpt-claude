# rzpt-claude

Registo pessoal de treino e saúde, operado pelo Claude Code.

**Repositório privado.** Contém dados de saúde pessoais — nunca tornar público.

## Como usar

Abre uma sessão de Claude Code com este repositório e fala normalmente:

- **Registar** — descreve o treino ou envia uma foto (balança, prato, ecrã da máquina).
  O Claude extrai os dados, escreve em `registos/YYYY-MM-DD.md` e faz commit + push.
- **Analisar** — pede uma "análise" ou "revisão". Muda para Opus (`/model opus`) primeiro;
  o Claude avisa-te se te esqueceres.

As instruções completas de comportamento estão no [CLAUDE.md](CLAUDE.md), que é carregado
automaticamente em cada sessão. É também lá que vive o perfil ("o que sabes sobre mim") —
versionado em git, com histórico.

## Estrutura

```
CLAUDE.md            instruções do PT + perfil pessoal
registos/
├── _TEMPLATE.md     estrutura de referência de um registo
└── YYYY-MM-DD.md    um ficheiro por dia
```

## Notas

- As fotos não são guardadas — só o registo escrito extraído delas.
- O histórico não é reescrito: registos antigos só se alteram com autorização explícita.
