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
- **`contexto`** — `prova` · `treino` (esforço cronometrado isolado) · `serie` (série de
  repetições) · `parcial` (tempo de passagem / split, ex. o "Lap" do swimrankings — **não é
  resultado individual**, não conta como recorde pessoal)
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

- **`modalidade`** — `crossfit` · `hyrox` · `natacao` · `natacao aguas abertas` · `corrida` ·
  `caminhada` · `ciclismo` · `forca` · `descanso` · `trotinete`
- ⚠️ **`trotinete` NÃO é treino.** O relógio classifica os trajetos de trotinete como ciclismo
  (tipo 9 da Zepp) — são ~200 deslocações de ~10 min a ~19 km/h. **Filtrar sempre nas análises
  de volume ou de carga**, senão os números ficam inflacionados.
- `tipoNN` são códigos da Zepp ainda por identificar. `tipo42` (≈199 min, ≈21 km, abril/2026)
  é provavelmente snowboard — por confirmar com o Ricardo.
- **`origem`** — de onde veio a linha. Vazio = manual. `<ficheiro>.fit` = importado pelo
  `sincronizar.py` (o mais rico: tem FC a 1 Hz e densidade). `zepp:<instante>` = export completo
  da app. Serve para não duplicar e para saber em que confiar.
- **`rpe`** — esforço percebido, 1–10. É o campo que distingue progressão real de estagnação:
  as mesmas cargas com RPE a descer é progresso; com RPE a subir é fadiga acumulada.
- **`resultado`** — score do WOD em texto livre (`21-15-9 em 8:42`, `4 rondas + 12`)
- **`dor_zona`** / **`dor_0_10`** — vazio quando não há dor. Registar mesmo quando é pouco:
  a série é que revela se o cotovelo está a melhorar ou a piorar.

## `nutricao.csv` — adesão alimentar diária

Ficheiro acrescentado em 2026-08-07. **Deliberadamente de baixo atrito:** contar tudo todos os
dias não se sustenta, e foi a prescrição excessiva dos relatórios importados que produziu o
ciclo restrição→compensação que estamos a corrigir. Uma linha com dois campos preenchidos vale
mais do que nenhuma linha.

`data, adesao_0_5, kcal, proteina_g, hidratos_g, alcool_un, fome_0_5, desvio`

- **`adesao_0_5`** — o campo que importa. Quão perto do plano ficou o dia. 5 = cumprido,
  0 = descarrilou. Subjetivo e é bom que seja: mede o que o Ricardo sente que controlou.
- **`alcool_un`** — unidades de álcool. **Registar sempre**, mesmo ao fim de semana quando está
  previsto. É a variável com maior efeito no peso à balança na manhã seguinte (retenção) e na
  FC noturna, e sem a coluna não se pode correlacionar.
- **`fome_0_5`** — fome ao longo do dia. É o indicador de alerta: fome a subir ao longo da
  semana antecipa o descontrolo de sexta-feira. Serve para ajustar **antes** de acontecer.
- **`kcal`, `proteina_g`, `hidratos_g`** — só quando ele contar. Vazio é aceitável e normal.
- **`desvio`** — texto livre do que saiu do plano e porquê. O "porquê" é o que interessa.

Ver as metas em `plano.md`. **Não transformar isto num diário alimentar** — se um dia só houver
`adesao_0_5` e `alcool_un`, está bem assim.

## `atividade.csv` — dia a dia, do Amazfit Balance

Série contínua desde 2020. É a base para consistência e para estimar gasto energético.

`data, passos, distancia_m, kcal_atividade, fc_repouso, fc_media, fc_max, fonte`

- **`fc_repouso`** — mínimo antes das 06:00, agregado das ~240 amostras diárias de
  `HEARTRATE_AUTO`. É um proxy melhor da FC de repouso real do que a leitura pontual da balança.
- **`kcal_atividade`** — estimativa do relógio, tendencialmente otimista. Usar para tendência,
  não como verdade absoluta.
- Importado com `python ferramentas/zepp.py <pasta> --importar`.

## `prontidao.csv` — carga e recuperação do Amazfit Balance

Ficheiro acrescentado em 2026-08-07. Dados do separador **Esforço** da app Zepp.

`data, carga_pct, fadiga, condicao_fisica, estado_treino, fonte, notas`

- **`carga_pct`** — anel de carga de treino, 0–100 %
- **`fadiga`** / **`condicao_fisica`** — índices proprietários da Zepp. Valores absolutos sem
  significado externo; **só a tendência interessa**.
- **`estado_treino`** — negativo = carga abaixo do necessário para manter a condição
  (destreino); positivo = a construir. **É o campo mais acionável do ficheiro.**
- Fadiga alta com `estado_treino` negativo não é fadiga de treino — é stress ou falta de sono.

## `sono.csv` — sono e recuperação

`data, deitar, acordar, cama_min, sono_min, profundo_min, rem_min, leve_min, acordado_min,
fc_min, score, fonte, notas`

- A `data` é a da **manhã em que se acordou**.
- **`fonte`** — `balance` (Amazfit) · `atleta` (declarado)
- `cama_min` (tempo na cama) e `sono_min` (sono real) são coisas diferentes — não confundir.
  A diferença entre as duas é latência de adormecimento, e é um sinal por si só.
- **`acordado_min`** — minutos acordado durante a noite, **não** número de despertares.
- **`fc_min`** — FC mínima noturna. É o melhor indicador de recuperação que o Balance dá:
  desce ao longo da noite numa noite boa; fica alta com álcool, stress ou sobretreino.
- Importar com `python ferramentas/zepp.py <pasta> --csv`.
