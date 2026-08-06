# dados/ — séries temporais

**Regra de ouro: os números vivem aqui. A narrativa vive em `registos/`.**

CSV e não tabelas markdown por três razões: acrescentar uma linha é seguro (não há risco de
corromper o passado), o diff do git é uma linha, e uma análise de tendência lê **um** ficheiro
em vez de duzentos.

Todos os ficheiros são **append-only**: acrescenta-se ao fim, nunca se reescreve o passado.
Corrigir uma linha antiga exige autorização explícita do Ricardo (ver `CLAUDE.md`).

Campos vazios ficam vazios — nunca se inventa nem se interpola.

---

## `corpo.csv` — peso e composição corporal

Uma linha por medição, idealmente diária. Sempre nas mesmas condições: manhã, em jejum,
depois de urinar, antes de beber.

`data, peso_kg, gordura_pct, gordura_kg, massa_magra_kg, massa_muscular_kg, musculo_esq_kg,
agua_pct, proteina_pct, visceral, tmb_kcal, fc_repouso, fonte, notas`

- **`fonte`** — `balanca` (medido) · `atleta` (declarado) · `relatorio` (extraído dos `.docx`
  importados, fiabilidade baixa) · `derivado` (calculado a partir de outro valor)
- O critério de sucesso é `massa_magra_kg` estável enquanto `peso_kg` desce. Ver `plano.md`.

## `natacao.csv` — tempos de prova e de treino

O mesmo formato serve uma prova e uma série de treino. Uma prova é `reps = 1`.

`data, prova, piscina_m, contexto, reps, intervalo, melhor, melhor_s, media_s, pontos_fina,
local, notas`

- **`piscina_m`** — `25` ou `50`. **Nunca comparar tempos entre piscinas diferentes.**
- **`contexto`** — `prova` · `treino` (esforço cronometrado isolado) · `serie` (série de repetições)
- **`melhor`** — como se lê (`26.18`, `1:17.29`). **`melhor_s`** — o mesmo em segundos decimais
  (`26.18`, `77.29`). A coluna em segundos é a que permite calcular tendências.
- **`media_s`** — média da série, em segundos. Vazio numa prova.
- Exemplo de série: `2026-09-22,50 Livres,25,serie,8,1:00,28.4,28.4,29.7,,Povoa,`

## `forca.csv` — cargas de treino e PRs

`data, exercicio, series, reps, carga_kg, rpe, contexto, notas`

- **`contexto`** — `treino` · `pr` (recorde pessoal)
- Nome do exercício sempre igual entre registos, senão a série parte-se. Usar os nomes já
  presentes no ficheiro antes de inventar variantes.

## `treinos.csv` — uma linha por sessão

O resumo de nível superior. Serve para medir consistência, carga semanal e dor ao longo do tempo.

`data, modalidade, duracao_min, rpe, energia_1_5, resultado, dor_zona, dor_0_10, notas`

- **`modalidade`** — `crossfit` · `hyrox` · `natacao` · `forca` · `descanso`
- **`rpe`** — esforço percebido, 1–10. É o campo que distingue progressão real de estagnação:
  as mesmas cargas com RPE a descer é progresso; com RPE a subir é fadiga acumulada.
- **`resultado`** — score do WOD em texto livre (`21-15-9 em 8:42`, `4 rondas + 12`)
- **`dor_zona`** / **`dor_0_10`** — vazio quando não há dor. Registar mesmo quando é pouco:
  a série é que revela se o cotovelo está a melhorar ou a piorar.

## `sono.csv` — sono e recuperação

`data, deitar, acordar, cama_min, sono_min, profundo_min, rem_min, leve_min, despertares,
fc_min, score, fonte, notas`

- A `data` é a da **manhã em que se acordou**.
- **`fonte`** — `balance` (Amazfit) · `atleta` (declarado)
- `cama_min` (tempo na cama) e `sono_min` (sono real) são coisas diferentes — não confundir.
