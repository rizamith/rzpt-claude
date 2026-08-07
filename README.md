# rzpt-claude

Registo pessoal de treino e saúde do Ricardo, operado pelo Claude Code.

**Repositório privado.** Contém dados de saúde pessoais — nunca tornar público.

---

## Não há bots

Não há servidor, não há backend, não há processo a correr em lado nenhum. A "app" são três peças:

```text
   O Ricardo                    O Claude Code                   O GitHub
   ─────────                    ─────────────                   ────────
   foto da balança      ──→     lê, extrai, escreve      ──→    guarda o estado
   descreve o treino    ──→     pergunta o que falta     ──→    (fonte de verdade)
   partilha o .fit      ──→     corre os scripts         ──→
   para o Drive                 commit + push
```

O único automatismo é o **Google Drive**: a app Zepp sincroniza os treinos para a pasta `Zepp`
**sozinha**, sem o Ricardo fazer nada. Eu verifico essa pasta em **toda** a conversa. O resto
acontece quando falas comigo.

---

## O dia-a-dia

### De manhã, ao acordar

**Foto da balança.** É o único registo verdadeiramente diário, e o mais importante do plano.

Sempre nas mesmas condições: em jejum, depois de urinar, antes de beber. Dias diferentes medidos
de maneiras diferentes não formam série.

Se não houve treino nem nada a dizer, **basta isso**. Não é preciso escrever mais nada.

### Depois de treinar

**O treino entra sozinho.** A app Zepp sincroniza o `.fit` para o Drive e eu verifico a pasta
sempre que falamos — tempos, calorias, FC a 1 Hz e densidade da sessão vêm de lá.

Só falta uma coisa, e é a única que nenhum aparelho dá: **o RPE.** Um número de 1 a 10.
Sem ele não distingo uma sessão dura de uma sessão social.

Se o treino não ficou gravado no relógio, descreve por palavras — serve.

### Natação

O relógio não vai à água (é grande e atrapalha a braçada). Portanto **diz-me em texto**:

> nadei 2200 m em 50 min, séries de 100

Metros e tempo bastam. É a única fonte de volume de natação que existe, e é a que liga o peso
aos tempos.

### Alimentação

**Uma linha, não um diário alimentar.** O que interessa é a adesão, não a contabilidade:

> comi bem, 2 copos de vinho ao jantar, fome a meio da tarde

Daí saem os campos que importam: adesão (0–5), unidades de álcool e fome (0–5). Se contares
calorias ou proteína, tanto melhor; se não, fica vazio e não há problema.

O **álcool registra-se sempre**, mesmo quando está previsto no plano: é a variável com maior
efeito no peso da manhã seguinte e na FC noturna.

### Quando houver algo a dizer

Dor, sono mau, semana de stress, prova, lesão, medicação. Não é preciso relatório — uma frase.

---

## O que acontece do meu lado

Quando mandas qualquer coisa, por esta ordem:

1. `git pull`
2. `python ferramentas/sincronizar.py` — traz do Drive os `.fit` novos
3. Extraio os dados do que mandaste
4. **Se algo estiver ambíguo, pergunto antes de escrever.** Não invento valores
5. Escrevo os números em `dados/*.csv` e a narrativa em `registos/YYYY-MM-DD.md`
6. `commit` + `push`
7. Confirmo em duas ou três linhas o que ficou registado

---

## De vez em quando

### Export da Zepp — sono, FC e passos

Uma vez por mês chega; nesta fase inicial vale a pena mais vezes.

Na app: **Perfil → Definições → exportar dados**. Manda-me o `.zip` e a palavra-passe, e eu
importo. Um export traz o histórico **todo**, não só o período desde o anterior.

_A via automática por API não funciona: o endpoint de autenticação da Zepp está fechado a
terceiros. Ver `CLAUDE.md`._

### Análise

Quando quiseres — mensal faz sentido, ou antes de uma prova. Pede "análise" ou "revisão".

**No PC e em Opus**, não no telemóvel: é leitura de todo o histórico e comparação com o
[plano](plano.md). Eu aviso se estiveres no modelo errado.

---

## O que está e não está automatizado

| | Como entra | Automático? |
| --- | --- | --- |
| Treinos (CrossFit, corrida, caminhada) | Zepp sincroniza para o Drive | ✅ totalmente |
| Peso e composição corporal | Foto da balança | ❌ foto diária |
| Natação — volume | Texto no chat | ❌ nunca será |
| RPE, dor, energia | Texto no chat | ❌ nunca será |
| Sono, FC, passos | Export da Zepp | ❌ periódico |

As três últimas linhas não são falhas do sistema: são coisas que **só tu sabes**. Nenhuma
automatização as substitui.

---

## Onde falas comigo

| | Para quê |
| --- | --- |
| **Claude Code no Android** | O registo diário. Foto da balança, RPE, como correu |
| **Claude Code no PC** | Análises, mudanças ao plano, trabalho nos scripts |

Os dois escrevem no mesmo repositório do GitHub, que é o estado partilhado. Regra em qualquer
um: **`pull` no início, `push` no fim.**

---

## Estrutura

Detalhe completo em [CLAUDE.md](CLAUDE.md) e no contrato de colunas em
[dados/README.md](dados/README.md).

```text
perfil.md        quem é o atleta: objetivos, PRs, restrições
plano.md         o plano até julho 2027
clinico.md       cronologia clínica
suplementos.md   o que tomar e o que não

dados/           NÚMEROS — CSV, append-only
registos/        NARRATIVA — um .md por dia
ferramentas/     scripts, sem dependências externas
analises/        relatórios de análise
```

**A regra que manda em tudo:** números vão para `dados/*.csv`, narrativa vai para
`registos/`. Uma análise de tendência tem de ler um ficheiro, não duzentos.

## Notas

- **As fotos e os `.fit` são efémeros** — servem para extrair dados no momento e não entram no
  repositório. O que fica é o registo escrito.
- **O histórico não se reescreve** sem autorização explícita, nem nos `.md` nem nos `.csv`.
- **Credenciais nunca no repositório** — no PC vivem em `C:\dev\_secrets\`.
- `python ferramentas/testar.py` verifica o sistema todo sem tocar na rede.
