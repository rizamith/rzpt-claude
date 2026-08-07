#!/usr/bin/env python3
"""Sincroniza os .fit da pasta Zepp do Google Drive para dados/treinos.csv.

A pasta `G:\\My Drive\\Zepp` esta montada localmente pelo Google Drive for
Desktop, por isso nao e preciso API nenhuma: le-se do disco.

    python ferramentas/sincronizar.py            importa o que for novo
    python ferramentas/sincronizar.py --seco     mostra o que faria, sem escrever

Idempotente: a coluna `origem` de treinos.csv guarda o nome do ficheiro de
origem, e ficheiros ja importados sao ignorados. Correr as vezes que se quiser.
"""
import os, sys, csv, glob, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fit as fitlib

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TREINOS = os.path.join(RAIZ, 'dados', 'treinos.csv')
PASTAS = [r'G:\My Drive\Zepp', r'H:\My Drive\Zepp',
          os.path.join(RAIZ, 'import', 'Zepp')]

COLS = ['data', 'modalidade', 'duracao_min', 'rpe', 'energia_1_5', 'resultado',
        'dor_zona', 'dor_0_10', 'origem', 'notas']

# FC a partir da qual se considera trabalho a serio. Deliberadamente um valor
# absoluto e nao uma percentagem de FCmax: a FCmax real do Ricardo nao e
# conhecida (220-idade e pouco fiavel; ja registou 157 numa sessao de CrossFit).
FC_TRABALHO = 120


def pasta_zepp():
    for p in PASTAS:
        if os.path.isdir(p):
            return p
    return None


def densidade(msgs):
    """Minutos da sessao com FC media >= FC_TRABALHO."""
    recs = [r for r in msgs.get(20, []) if r.get(3)]
    if not recs:
        return None, None
    t0 = recs[0][253]
    por_min = collections.OrderedDict()
    for r in recs:
        por_min.setdefault((r[253] - t0) // 60, []).append(r[3])
    medias = [sum(v) / len(v) for v in por_min.values()]
    return sum(1 for m in medias if m >= FC_TRABALHO), len(medias)


def ler_existentes():
    if not os.path.exists(TREINOS):
        return [], set()
    linhas = list(csv.DictReader(open(TREINOS, encoding='utf-8')))
    return linhas, {l.get('origem') for l in linhas if l.get('origem')}


def main():
    seco = '--seco' in sys.argv
    pasta = pasta_zepp()
    if not pasta:
        raise SystemExit('Pasta Zepp nao encontrada. Procurei em:\n  ' + '\n  '.join(PASTAS))
    print('Pasta: %s' % pasta)

    linhas, ja_feitos = ler_existentes()
    ficheiros = sorted(glob.glob(os.path.join(pasta, '*.fit')) +
                       glob.glob(os.path.join(pasta, '*.fit.zip')))
    novas = []
    for f in ficheiros:
        nome = os.path.basename(f)
        if nome in ja_feitos:
            print('  = %s (ja importado)' % nome)
            continue
        try:
            msgs = fitlib.parse(f)
            r, _, _ = fitlib.resumo(msgs)
        except Exception as e:
            print('  ! %s -> erro: %s' % (nome, e))
            continue
        ativos, total = densidade(msgs)
        res = '%s kcal / FC %s-%s media %s' % (r['kcal'], r['fc_min'], r['fc_max'], r['fc_media'])
        if r['distancia_m']:
            res += ' / %.0f m' % r['distancia_m']
        nota = 'Importado de %s.' % nome
        if ativos is not None:
            nota += ' %d de %d min com FC >= %d.' % (ativos, total, FC_TRABALHO)
        if r['efeito_aerobio']:
            nota += ' Efeito aerobio %.1f.' % r['efeito_aerobio']
        novas.append({
            'data': str(r['inicio'].date()), 'modalidade': r['modalidade'],
            'duracao_min': str(round(r['duracao_min'])), 'rpe': '', 'energia_1_5': '',
            'resultado': res, 'dor_zona': '', 'dor_0_10': '',
            'origem': nome, 'notas': nota})
        print('  + %s -> %s %s, %d min' % (nome, r['inicio'].date(), r['modalidade'],
                                           round(r['duracao_min'])))

    if not novas:
        print('\nNada novo.')
        return
    if seco:
        print('\n--seco: %d linha(s) por escrever.' % len(novas))
        for n in novas:
            print('   ' + ','.join(n[c] for c in COLS))
        return

    todas = linhas + novas
    todas.sort(key=lambda l: (l.get('data') or '', l.get('modalidade') or ''))
    with open(TREINOS, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction='ignore')
        w.writeheader()
        for l in todas:
            w.writerow({c: (l.get(c) or '') for c in COLS})
    print('\n%d linha(s) acrescentada(s) a dados/treinos.csv.' % len(novas))
    print('Falta o RPE nessas linhas - so o Ricardo o pode dar.')


if __name__ == '__main__':
    main()
