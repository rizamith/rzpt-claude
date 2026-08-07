#!/usr/bin/env python3
"""Funde linhas duplicadas em dados/treinos.csv.

A mesma sessao pode entrar por tres caminhos, e todos sao legitimos:
  1. `.fit` individual partilhado para o Drive  -> tem FC a 1 Hz e densidade
  2. export completo da app (SPORT)             -> tem o instante exato, e completo
  3. entrada a mao a partir de screenshot       -> so o que se via no ecra

Duas linhas sao a mesma sessao se coincidirem em data, modalidade e duracao
(tolerancia de 1 minuto, porque as fontes arredondam de maneira diferente).

A fusao guarda o melhor de cada campo em vez de escolher uma linha e deitar as
outras fora: a origem mais rica manda, mas texto mais completo noutra fonte e
aproveitado, e o que so existe numa (rpe, dor) nunca se perde.

    python ferramentas/dedup.py           funde
    python ferramentas/dedup.py --seco    mostra o que faria
"""
import os, sys, csv, collections

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TREINOS = os.path.join(RAIZ, 'dados', 'treinos.csv')
COLS = ['data', 'modalidade', 'duracao_min', 'rpe', 'energia_1_5', 'resultado',
        'dor_zona', 'dor_0_10', 'origem', 'notas']


def qualidade(linha):
    """Maior e melhor. Decide qual origem manda numa fusao."""
    o = linha.get('origem') or ''
    if o.endswith('.fit'):
        return 3          # FC a 1 Hz e densidade calculada
    if o.startswith('zepp:'):
        return 2          # instante exato, fonte completa
    return 1              # manual


def chave(l):
    try:
        d = int(l['duracao_min'])
    except (ValueError, TypeError):
        d = -1
    return (l['data'], l['modalidade'], d)


def funde(grupo):
    grupo = sorted(grupo, key=qualidade, reverse=True)
    base = dict(grupo[0])
    for outra in grupo[1:]:
        for c in COLS:
            if c == 'origem':
                continue
            actual, nova = (base.get(c) or '').strip(), (outra.get(c) or '').strip()
            if not actual:
                base[c] = nova
            elif c in ('resultado', 'notas') and len(nova) > len(actual):
                base[c] = nova
    return base


def main():
    seco = '--seco' in sys.argv
    linhas = list(csv.DictReader(open(TREINOS, encoding='utf-8')))

    # tolerancia de 1 min: normaliza a duracao para a menor do grupo vizinho
    por_chave = collections.OrderedDict()
    for l in linhas:
        data, mod, dur = chave(l)
        alvo = None
        for (d2, m2, du2) in por_chave:
            if d2 == data and m2 == mod and abs(du2 - dur) <= 1:
                alvo = (d2, m2, du2)
                break
        por_chave.setdefault(alvo or (data, mod, dur), []).append(l)

    fundidas, removidas = [], 0
    for k, grupo in por_chave.items():
        if len(grupo) == 1:
            fundidas.append(grupo[0])
            continue
        removidas += len(grupo) - 1
        r = funde(grupo)
        fundidas.append(r)
        if seco:
            print('%s %-12s %3s min: %d fontes -> origem=%s' % (
                k[0], k[1], k[2], len(grupo), r['origem']))

    print('%d linhas -> %d (%d duplicados fundidos)' % (len(linhas), len(fundidas), removidas))
    if seco or not removidas:
        return
    fundidas.sort(key=lambda l: (l.get('data') or '', l.get('modalidade') or ''))
    with open(TREINOS, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction='ignore')
        w.writeheader()
        for l in fundidas:
            w.writerow({c: (l.get(c) or '') for c in COLS})


if __name__ == '__main__':
    main()
