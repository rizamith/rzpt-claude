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

O export chega num `.zip` **cifrado com AES**, que o `unzip` do Git Bash não abre (erro 81).
Usar o 7-Zip:

```
"/c/Program Files/7-Zip/7z.exe" x -p<palavra-passe> -o<destino> <ficheiro.zip>
python ferramentas/zepp.py <destino>          resumo
python ferramentas/zepp.py <destino> --csv    linhas para dados/sono.csv e treinos.csv
```

**Armadilhas do formato, descobertas a 2026-08-07:**

- `SLEEP` está em **UTC**; `SLEEP_MINUTE` e `HEARTRATE_AUTO` estão em **hora local**.
  Misturar os dois desloca tudo uma hora.
- As datas em `SLEEP_MINUTE` vêm **deslocadas um dia**. Usar as horas, ignorar a data.
- `BODY` vem **vazio** — a balança Xiaomi não está na Zepp. Export separado noutra app.
- O export pode trazer **um único dia**. Escolher intervalo maior na app, se houver opção.
