#!/usr/bin/env python3
"""Importador do export completo da app Zepp para dados/*.csv.

O export chega num .zip cifrado com AES. O `unzip` do Git Bash nao o abre
(erro 81) — usar o 7-Zip. Depois:

    python ferramentas/zepp.py <pasta>              o que la esta, sem escrever
    python ferramentas/zepp.py <pasta> --importar   escreve em dados/*.csv

Escreve em: sono.csv, treinos.csv, corpo.csv, atividade.csv.
Idempotente: nunca duplica datas nem sessoes ja registadas.

Armadilhas do formato, descobertas a 2026-08-07:
  - SLEEP e SPORT usam UTC ("+0000"); SLEEP_MINUTE e HEARTRATE_AUTO usam local.
  - As datas em SLEEP_MINUTE vem deslocadas um dia. Usar as horas, ignorar a data.
  - SLEEP tem uma linha por dia do calendario, quase todas a zero. So contam as
    que tem sono > 0: o relogio nem sempre e usado a dormir.
  - BODY quase nao tem nada e os valores de composicao nao batem certo com a
    balanca Xiaomi (18.5% vs 27.7% de gordura no mesmo peso). Importado com
    fonte='zepp' para nao contaminar a serie da balanca.
  - O tamanho do export depende do intervalo escolhido na app. Escolher o maximo.
"""
import sys, os, csv, glob, collections

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = os.path.join(RAIZ, 'dados')

# Codigos de modalidade da Zepp, inferidos a 2026-08-07 pela duracao, distancia
# e velocidade medianas de cada grupo de sessoes.
TIPO_DESPORTO = {
    1: 'corrida', 6: 'caminhada', 8: 'corrida', 10: 'ciclismo',
    14: 'natacao', 15: 'natacao aguas abertas', 16: 'trail', 130: 'crossfit',
    # 224 sessoes de ~10 min a ~19 km/h e 1-5 km: sao os trajetos de trotinete,
    # que o relogio classifica como ciclismo. NAO sao treino - filtrar nas analises.
    9: 'trotinete',
    42: 'tipo42',   # ~199 min, ~21 km, abril/2026. Por confirmar: snowboard?
}
NAO_E_TREINO = {'trotinete'}

COLS = {
    'sono': ['data', 'deitar', 'acordar', 'cama_min', 'sono_min', 'profundo_min',
             'rem_min', 'leve_min', 'acordado_min', 'fc_min', 'score', 'fonte', 'notas'],
    'treinos': ['data', 'modalidade', 'duracao_min', 'rpe', 'energia_1_5', 'resultado',
                'dor_zona', 'dor_0_10', 'origem', 'notas'],
    'corpo': ['data', 'peso_kg', 'gordura_pct', 'gordura_kg', 'massa_magra_kg',
              'massa_muscular_kg', 'musculo_esq_kg', 'agua_pct', 'proteina_pct',
              'visceral', 'tmb_kcal', 'fc_repouso', 'fonte', 'notas'],
    'atividade': ['data', 'passos', 'distancia_m', 'kcal_atividade',
                  'fc_repouso', 'fc_media', 'fc_max', 'fonte'],
}


def ler(base, nome):
    f = glob.glob(os.path.join(base, nome, '*.csv'))
    return list(csv.DictReader(open(f[0], encoding='utf-8-sig'))) if f else []


def num(v, t=int, d=0):
    try:
        return t(v)
    except (TypeError, ValueError):
        return d


# ---------------------------------------------------------------- extracao

def sono_de(base):
    """Uma linha por noite com sono real. Ignora os dias a zero."""
    fc_dia = fc_por_dia(base)
    out = []
    for s in ler(base, 'SLEEP'):
        prof, leve = num(s['deepSleepTime']), num(s['shallowSleepTime'])
        rem, acordado = num(s.get('REMTime')), num(s['wakeTime'])
        total = prof + leve + rem
        if total <= 0:
            continue
        out.append({
            'data': s['date'], 'deitar': '', 'acordar': '',
            'cama_min': total + acordado, 'sono_min': total, 'profundo_min': prof,
            'rem_min': rem, 'leve_min': leve, 'acordado_min': acordado,
            'fc_min': fc_dia.get(s['date'], {}).get('min', ''), 'score': '',
            'fonte': 'balance', 'notas': 'Export Zepp'})
    return out


def treinos_de(base):
    out = []
    for s in ler(base, 'SPORT'):
        t = int(s['type'])
        mod = TIPO_DESPORTO.get(t, 'tipo%d' % t)
        mins = round(num(s['sportTime(s)'], float) / 60.0)
        dist = num(s['distance(m)'], float)
        kcal = num(s['calories(kcal)'], float)
        res = '%.0f kcal' % kcal
        if dist:
            res += ' / %.0f m' % dist
        nota = 'Export Zepp (tipo %d).' % t
        if mod in NAO_E_TREINO:
            nota += ' NAO E TREINO - deslocacao.'
        out.append({
            'data': s['startTime'][:10], 'modalidade': mod, 'duracao_min': str(mins),
            'rpe': '', 'energia_1_5': '', 'resultado': res, 'dor_zona': '', 'dor_0_10': '',
            'origem': 'zepp:%s' % s['startTime'][:19], 'notas': nota})
    return out


def corpo_de(base):
    out = []
    for b in ler(base, 'BODY'):
        peso = num(b['weight'], float)
        if not peso:
            continue
        gord = num(b.get('fatRate'), float)
        out.append({
            'data': b['time'][:10], 'peso_kg': '%.1f' % peso,
            'gordura_pct': ('%.1f' % gord) if gord else '', 'gordura_kg': '',
            'massa_magra_kg': '', 'massa_muscular_kg': '', 'musculo_esq_kg': '',
            'agua_pct': '', 'proteina_pct': '', 'visceral': '',
            'tmb_kcal': str(int(num(b.get('metabolism'), float))) or '',
            'fc_repouso': '', 'fonte': 'zepp',
            'notas': 'Export Zepp. Composicao NAO comparavel com a balanca Xiaomi'})
    return out


def fc_por_dia(base):
    d = collections.defaultdict(list)
    for r in ler(base, 'HEARTRATE_AUTO'):
        v = num(r.get('heartRate'))
        if v:
            d[r['date']].append((r['time'], v))
    out = {}
    for dia, vs in d.items():
        vals = [v for _, v in vs]
        noite = [v for t, v in vs if t < '06:00']
        out[dia] = {'min': min(noite) if noite else min(vals),
                    'media': round(sum(vals) / len(vals)), 'max': max(vals), 'n': len(vals)}
    return out


def atividade_de(base):
    fc = fc_por_dia(base)
    out = []
    for a in ler(base, 'ACTIVITY'):
        passos = num(a['steps'])
        if passos <= 0:
            continue
        f = fc.get(a['date'], {})
        out.append({
            'data': a['date'], 'passos': str(passos),
            'distancia_m': str(num(a['distance'])), 'kcal_atividade': str(num(a['calories'])),
            'fc_repouso': str(f.get('min', '')), 'fc_media': str(f.get('media', '')),
            'fc_max': str(f.get('max', '')), 'fonte': 'balance'})
    return out


# ---------------------------------------------------------------- escrita

def fundir(ficheiro, cols, novas, chave):
    """Acrescenta so o que ainda nao existe. Devolve (novas, ja_existentes)."""
    caminho = os.path.join(DADOS, ficheiro)
    antigas = []
    if os.path.exists(caminho):
        antigas = list(csv.DictReader(open(caminho, encoding='utf-8')))
    vistas = {chave(l) for l in antigas}
    acrescentar = [n for n in novas if chave(n) not in vistas]
    if not acrescentar:
        return 0, len(antigas)
    todas = antigas + acrescentar
    todas.sort(key=lambda l: (l.get('data') or '', l.get('modalidade') or '',
                              l.get('origem') or ''))
    with open(caminho, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for l in todas:
            w.writerow({c: (l.get(c) or '') for c in cols})
    return len(acrescentar), len(antigas)


def main():
    base = sys.argv[1]
    escrever = '--importar' in sys.argv

    blocos = [
        ('sono.csv', 'sono', sono_de(base), lambda l: l['data']),
        ('treinos.csv', 'treinos', treinos_de(base), lambda l: l.get('origem') or
            (l['data'], l['modalidade'], l['duracao_min'])),
        ('corpo.csv', 'corpo', corpo_de(base), lambda l: (l['data'], l.get('fonte'))),
        ('atividade.csv', 'atividade', atividade_de(base), lambda l: l['data']),
    ]

    for ficheiro, nome, linhas, chave in blocos:
        if not linhas:
            print('%-14s nada' % ficheiro)
            continue
        datas = sorted(l['data'] for l in linhas)
        if not escrever:
            print('%-14s %5d linhas  %s -> %s' % (ficheiro, len(linhas), datas[0], datas[-1]))
            continue
        n, antes = fundir(ficheiro, COLS[nome], linhas, chave)
        print('%-14s +%-5d (tinha %d)  %s -> %s' % (ficheiro, n, antes, datas[0], datas[-1]))

    if not escrever:
        print('\nSem --importar nada foi escrito.')


if __name__ == '__main__':
    main()
