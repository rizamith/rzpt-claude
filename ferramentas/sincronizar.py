#!/usr/bin/env python3
"""Importa treinos .fit da Zepp para dados/treinos.csv.

Funciona em dois ambientes, porque a "app" corre nos dois:

  PC (Windows, Google Drive for Desktop montado)
      python ferramentas/sincronizar.py
      Le direto de G:\\My Drive\\Zepp. Nao precisa de rede nem de conector.

  Nuvem (Claude Code no Android/web, sandbox ligado ao GitHub)
      Nao ha disco do Drive. O agente descarrega cada ficheiro pelo conector
      Google Drive e alimenta-o aqui em base64:
      python ferramentas/sincronizar.py --b64 Zepp20260808071000.fit < ficheiro.b64

  Qualquer ambiente, pasta explicita
      python ferramentas/sincronizar.py --pasta <caminho>

  Ver sem escrever
      acrescentar --seco a qualquer um dos modos

Idempotente em todos os modos: a coluna `origem` de treinos.csv guarda o nome
do ficheiro de proveniencia e o que ja entrou e ignorado.
"""
import os, sys, csv, glob, base64, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fit as fitlib

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TREINOS = os.path.join(RAIZ, 'dados', 'treinos.csv')
ESTAGIO = os.path.join(RAIZ, 'import', 'Zepp')   # fora do git

# Pastas onde o Drive pode estar montado localmente. Nenhuma existir nao e erro:
# na nuvem nao existe nenhuma e usa-se --b64.
MONTAGENS = [r'G:\My Drive\Zepp', r'H:\My Drive\Zepp',
             os.path.expanduser('~/Google Drive/Zepp'), ESTAGIO]

COLS = ['data', 'modalidade', 'duracao_min', 'rpe', 'energia_1_5', 'resultado',
        'dor_zona', 'dor_0_10', 'origem', 'notas']

# FC a partir da qual se conta trabalho a serio. Limiar absoluto de proposito:
# a FCmax real do Ricardo nao e conhecida (220-idade e pouco fiavel; ja
# registou 157 numa sessao de CrossFit).
FC_TRABALHO = 120


def densidade(msgs):
    """(minutos com FC media >= FC_TRABALHO, minutos totais com FC)."""
    recs = [r for r in msgs.get(20, []) if r.get(3)]
    if not recs:
        return None, None
    t0 = recs[0][253]
    por_min = collections.OrderedDict()
    for r in recs:
        por_min.setdefault((r[253] - t0) // 60, []).append(r[3])
    medias = [sum(v) / len(v) for v in por_min.values()]
    return sum(1 for m in medias if m >= FC_TRABALHO), len(medias)


def existentes():
    if not os.path.exists(TREINOS):
        return [], set()
    linhas = list(csv.DictReader(open(TREINOS, encoding='utf-8')))
    return linhas, {l.get('origem') for l in linhas if l.get('origem')}


def linha_de(caminho):
    """Converte um .fit numa linha de treinos.csv. None se ilegivel."""
    nome = os.path.basename(caminho)
    msgs = fitlib.parse(caminho)
    r, _, _ = fitlib.resumo(msgs)
    ativos, total = densidade(msgs)
    res = '%s kcal / FC %s-%s media %s' % (r['kcal'], r['fc_min'], r['fc_max'], r['fc_media'])
    if r['distancia_m']:
        res += ' / %.0f m' % r['distancia_m']
    nota = 'Importado de %s.' % nome
    if ativos is not None:
        nota += ' %d de %d min com FC >= %d.' % (ativos, total, FC_TRABALHO)
    if r['efeito_aerobio']:
        nota += ' Efeito aerobio %.1f.' % r['efeito_aerobio']
    return {'data': str(r['inicio'].date()), 'modalidade': r['modalidade'],
            'duracao_min': str(round(r['duracao_min'])), 'rpe': '', 'energia_1_5': '',
            'resultado': res, 'dor_zona': '', 'dor_0_10': '',
            'origem': nome, 'notas': nota}


def gravar(linhas, novas):
    todas = linhas + novas
    todas.sort(key=lambda l: (l.get('data') or '', l.get('modalidade') or ''))
    with open(TREINOS, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction='ignore')
        w.writeheader()
        for l in todas:
            w.writerow({c: (l.get(c) or '') for c in COLS})


def processar(caminhos, seco):
    linhas, ja = existentes()
    novas = []
    for c in sorted(caminhos):
        nome = os.path.basename(c)
        if nome in ja:
            print('  = %s (ja importado)' % nome)
            continue
        try:
            n = linha_de(c)
        except Exception as e:
            print('  ! %s -> %s' % (nome, e))
            continue
        novas.append(n)
        print('  + %s -> %s %s, %s min' % (nome, n['data'], n['modalidade'], n['duracao_min']))
    if not novas:
        print('\nNada novo.')
        return 0
    if seco:
        print('\n--seco: %d linha(s) por escrever.' % len(novas))
        return 0
    gravar(linhas, novas)
    print('\n%d linha(s) em dados/treinos.csv. Falta o RPE - so o Ricardo o pode dar.' % len(novas))
    return len(novas)


def main():
    a = sys.argv[1:]
    seco = '--seco' in a

    if '--b64' in a:                       # nuvem: um ficheiro por chamada, via stdin
        nome = a[a.index('--b64') + 1]
        os.makedirs(ESTAGIO, exist_ok=True)
        destino = os.path.join(ESTAGIO, nome)
        dados = base64.b64decode(''.join(sys.stdin.read().split()))
        open(destino, 'wb').write(dados)
        print('Recebido %s (%d bytes)' % (nome, len(dados)))
        return processar([destino], seco)

    if '--pasta' in a:
        pastas = [a[a.index('--pasta') + 1]]
    else:
        pastas = [p for p in MONTAGENS if os.path.isdir(p)]
        if not pastas:
            print('Nenhuma pasta do Drive montada localmente.')
            print('Estamos na nuvem: usar o conector Google Drive e --b64. Ver CLAUDE.md.')
            return 0

    caminhos = []
    for p in pastas:
        print('Pasta: %s' % p)
        caminhos += glob.glob(os.path.join(p, '*.fit')) + glob.glob(os.path.join(p, '*.fit.zip'))
    return processar(caminhos, seco)


if __name__ == '__main__':
    main()
