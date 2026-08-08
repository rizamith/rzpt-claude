# ferramentas/

## `fit.py` — leitor de ficheiros .FIT da Zepp

Sem dependências externas. A Zepp exporta cada treino individualmente em FIT — por vezes com
extensão `.zip` enganadora, mas o conteúdo é FIT binário.

```
python ferramentas/fit.py <ficheiro.fit>              resumo
python ferramentas/fit.py <ficheiro.fit> --minutos    FC média por minuto
python ferramentas/fit.py <ficheiro.fit> --csv        linha pronta para dados/treinos.csv
```

**Porque importa:** o separador *Esforço* da app mostra índices proprietários (fadiga, condição
física, estado de treino) sem significado externo e que se contradizem com o volume real. O FIT
tem a série de frequência cardíaca crua a 1 Hz — é o que permite distinguir uma sessão densa de
uma sessão com muito tempo parado, e é a única forma de medir intensidade sem depender do RPE.

**Como exportar na app Zepp:** abrir o treino → menu de partilha → exportar/partilhar ficheiro
original. Um ficheiro por sessão.

## `zepp.py` — importador do export de dados da Zepp

O export chega num `.zip` **cifrado com AES**. Como abrir depende do ambiente:

**PC:** o `unzip` do Git Bash não abre (erro 81). Usar o 7-Zip:

```
"/c/Program Files/7-Zip/7z.exe" x -p<palavra-passe> -o<destino> <ficheiro.zip>
```

**Nuvem:** não há 7-Zip. Confirmado a funcionar com `pyzipper` (2026-08-08), que não vem
instalado por omissão:

```
pip install pyzipper
python -c "
import pyzipper
with pyzipper.AESZipFile('<ficheiro.zip>') as z:
    z.extractall('<destino>', pwd=b'<palavra-passe>')
"
```

Depois, em qualquer ambiente:

```
python ferramentas/zepp.py <destino>              resumo, sem escrever
python ferramentas/zepp.py <destino> --importar   escreve em dados/*.csv
```

**Armadilhas do formato, descobertas a 2026-08-07:**

- `SLEEP` está em **UTC**; `SLEEP_MINUTE` e `HEARTRATE_AUTO` estão em **hora local**.
  Misturar os dois desloca tudo uma hora.
- As datas em `SLEEP_MINUTE` vêm **deslocadas um dia**. Usar as horas, ignorar a data.
- `BODY` traz o peso e pouco mais (confirmado 2026-08-08: `weight`, `height`, `bmi` vêm
  preenchidos; `fatRate` e o resto costumam vir `null`). A composição, quando vem, **não bate
  com a balança Xiaomi** — o `zepp.py` importa-a com `fonte=zepp` para não contaminar a série
  da balança, mas um peso igual ao já registado no mesmo dia é redundante: confirmar antes de
  manter as duas linhas.
- O export pode trazer **um único dia** — não é preciso pedir sempre o histórico completo; um
  export pequeno, feito na hora, é uma forma válida de trazer o `.fit` de uma sessão quando o
  relógio não sincronizou sozinho para a Drive.

## `sincronizar.py` — Drive → `dados/treinos.csv`

**É este o comando do dia-a-dia.** Os outros dois são para inspeção manual.

```
python ferramentas/sincronizar.py           importa o que for novo
python ferramentas/sincronizar.py --seco    mostra o que faria, sem escrever
```

O Google Drive for Desktop monta a conta pessoal em `G:`, portanto `G:\My Drive\Zepp` é uma
pasta local normal — não é preciso API nem autenticação. O Ricardo partilha o treino da app
Zepp para essa pasta; o script lê, converte e escreve.

**Idempotente.** A coluna `origem` de `treinos.csv` guarda o nome do ficheiro de origem e o que
já entrou é ignorado. Correr as vezes que se quiser, sem risco de duplicar.

Além do resumo, calcula **quantos minutos da sessão tiveram FC ≥ 120** — a medida de densidade
que distingue 35 minutos de trabalho de 35 minutos com 12 parado. Usa um limiar absoluto e não
uma percentagem de FCmax de propósito: a FCmax real do Ricardo não é conhecida.

O que o script **não** consegue dar é o **RPE**. Fica sempre vazio, e é sempre preciso perguntar.

## `dedup.py` — funde a mesma sessão vinda de fontes diferentes

**Correr sempre depois de `zepp.py --importar`.** Uma sessão pode entrar pelo `.fit`, pelo
export completo e por registo manual; as três são legítimas e trazem campos diferentes.

Duas linhas são a mesma sessão se coincidirem em data, modalidade e duração (±1 min). A fusão
guarda o melhor de cada campo em vez de escolher uma linha e deitar as outras fora: manda a
origem mais rica (`.fit` > `zepp:` > manual), mas texto mais completo noutra fonte é aproveitado
e o que só existe numa — `rpe`, `dor` — nunca se perde.

## `zepp_api.py` — sono e atividade automáticos, sem export

**⚠️ API não oficial.** A Zepp não publica API para utilizadores; isto usa os mesmos endpoints
que a app. Funciona, mas parte quando eles mudarem algo — e nesse dia o `zepp.py` com export
manual continua a ser a rede de segurança.

Corre no **GitHub Actions** (`.github/workflows/sincronizar-zepp.yml`), todos os dias às 08h20
UTC, e faz commit do que trouxer. Não precisa de PC ligado.

```
ZEPP_EMAIL=... ZEPP_PASSWORD=... python ferramentas/zepp_api.py --dias 7
   ... --importar   escreve em dados/sono.csv e dados/atividade.csv
   ... --diag       diagnóstico verboso (nunca imprime a palavra-passe)
```

Autenticação em três passos: um `POST` que devolve um 303 cujo `Location` traz o código de
acesso (não se segue o redireccionamento), um segundo `POST` que troca esse código por
`app_token` + `user_id` + host regional, e finalmente `GET /v1/data/band_data.json`. As horas
vêm como instantes Unix e são convertidas para `Europe/Lisbon`, para bater com as linhas que já
existem nos CSV.

**As credenciais nunca vivem no repositório** — só em GitHub Secrets, `ZEPP_EMAIL` e
`ZEPP_PASSWORD`.

## `testar.py` — verificação do sistema todo

```
python ferramentas/testar.py           tudo menos rede, não escreve nada
python ferramentas/testar.py --rede    inclui os testes que tocam na Zepp
```

Verifica: módulos carregam · CSV bem formados (colunas e datas) · sem duplicados ·
pesos plausíveis · natação sempre com piscina · leitor de FIT contra ficheiros reais ·
credenciais presentes.

**Sem `--rede` não faz um único pedido à internet.** É deliberado: cada tentativa de
autenticação conta para o limite de pedidos da Zepp e o bloqueio dura dezenas de minutos.
Correr à vontade; só usar `--rede` quando se quer mesmo testar a API.

Apanhou logo à primeira uma linha de `natacao.csv` com vírgula não citada na nota, que partia
a contagem de colunas — é para isso que serve.

## Credenciais: `C:\dev\_secrets\zepp_secrets.json`

Fora de qualquer repositório git, na mesma pasta dos outros segredos do Ricardo.

```json
{ "email": "...", "password": "...", "app_token": "", "user_id": "", "obtido_em": "" }
```

Basta preencher `password`. O `app_token` e o `user_id` são escritos automaticamente por
`python ferramentas/zepp_api.py --token`, e é isso que depois se cola nos GitHub Secrets.
Os scripts preferem sempre o ambiente ao ficheiro, para o Actions funcionar sem alterações.
