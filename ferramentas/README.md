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
