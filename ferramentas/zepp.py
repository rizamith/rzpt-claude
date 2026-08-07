#!/usr/bin/env python3
"""Importador do export de dados da app Zepp.

O export vem num .zip protegido por palavra-passe (7-Zip resolve; o `unzip` do
Git Bash nao suporta a cifra AES que a Zepp usa). Extrair primeiro, depois:

    python ferramentas/zepp.py <pasta_extraida>            resumo do que la esta
    python ferramentas/zepp.py <pasta_extraida> --csv      linhas para dados/*.csv

Ficheiros lidos: SLEEP, SLEEP_MINUTE, HEARTRATE_AUTO, ACTIVITY, SPORT, BODY, USER.

Notas sobre o formato, descobertas a 2026-08-07:
  - SLEEP usa UTC ("+0000"); SLEEP_MINUTE e HEARTRATE_AUTO usam hora local.
  - As datas em SLEEP_MINUTE vem deslocadas um dia. Usar as horas, ignorar a data.
  - BODY vem vazio: a balanca Xiaomi nao esta na Zepp, esta noutra app.
  - O export pode trazer so um dia. Escolher intervalo maior na app se possivel.
"""
import sys, os, csv, glob, collections

TIPO_DESPORTO = {1: 'corrida', 6: 'caminhada', 8: 'natacao', 9: 'ciclismo',
                 10: 'natacao', 130: 'crossfit', 16: 'trail'}


def _ler(base, nome):
    f = glob.glob(os.path.join(base, nome, '*.csv'))
    if not f:
        return []
    return list(csv.DictReader(open(f[0], encoding='utf-8-sig')))


def analisa(base):
    r = {}
    sono = _ler(base, 'SLEEP')
    smin = _ler(base, 'SLEEP_MINUTE')
    hr = [(x['time'], int(x['heartRate'])) for x in _ler(base, 'HEARTRATE_AUTO')
          if x.get('heartRate')]

    if sono:
        s = sono[0]
        prof = int(s['deepSleepTime'] or 0)
        leve = int(s['shallowSleepTime'] or 0)
        rem = int(s['REMTime'] or 0)
        acordado = int(s['wakeTime'] or 0)
        r['sono'] = {
            'data': s['date'], 'profundo': prof, 'leve': leve, 'rem': rem,
            'acordado_min': acordado, 'total': prof + leve + rem,
            'cama': prof + leve + rem + acordado,
            # horas locais vem do SLEEP_MINUTE; SLEEP esta em UTC
            'deitar': smin[0]['time'] if smin else '',
            'acordar': smin[-1]['time'] if smin else '',
        }
        if smin:
            r['sono']['blocos'] = _blocos(smin)

    if hr:
        acordar = r.get('sono', {}).get('acordar', '06:00')
        noite = [v for t, v in hr if t < acordar]
        dia = [v for t, v in hr if t >= acordar]
        r['fc'] = {'noite': noite, 'dia': dia, 'todas': hr}

    act = _ler(base, 'ACTIVITY')
    if act:
        r['atividade'] = act[0]

    r['desporto'] = []
    for s in _ler(base, 'SPORT'):
        seg = int(float(s['sportTime(s)']))
        r['desporto'].append({
            'tipo': TIPO_DESPORTO.get(int(s['type']), 'tipo=%s' % s['type']),
            'inicio': s['startTime'], 'min': round(seg / 60.0, 1),
            'dist_m': float(s['distance(m)']), 'kcal': float(s['calories(kcal)'])})

    r['vazios'] = [n for n in ('BODY', 'HEALTH_DATA', 'HEARTRATE') if not _ler(base, n)]
    u = _ler(base, 'USER')
    if u:
        r['user'] = u[0]
    return r


def _blocos(smin):
    out, prev, ini, n = [], None, None, 0
    for x in smin + [{'stage': None, 'time': ''}]:
        if x['stage'] != prev:
            if prev:
                out.append((ini, prev, n))
            prev, ini, n = x['stage'], x['time'], 1
        else:
            n += 1
    return out


def main():
    base = sys.argv[1]
    csv_modo = '--csv' in sys.argv
    r = analisa(base)

    if csv_modo:
        s = r.get('sono')
        if s:
            fcmin = min(r['fc']['noite']) if r.get('fc', {}).get('noite') else ''
            print('# dados/sono.csv')
            print('%s,%s,%s,%d,%d,%d,%d,%d,%s,%s,,balance,Importado do export Zepp' % (
                s['data'], s['deitar'], s['acordar'], s['cama'], s['total'],
                s['profundo'], s['rem'], s['leve'], s['acordado_min'], fcmin))
        if r['desporto']:
            print('# dados/treinos.csv')
            for d in r['desporto']:
                print('%s,%s,%d,,,%d kcal%s,,,Importado do export Zepp' % (
                    d['inicio'][:10], d['tipo'], round(d['min']), d['kcal'],
                    ' / %.0f m' % d['dist_m'] if d['dist_m'] else ''))
        return

    s = r.get('sono')
    if s:
        print('SONO  %s  %s -> %s' % (s['data'], s['deitar'], s['acordar']))
        print('  na cama       %d min (%dh%02d)' % (s['cama'], s['cama'] // 60, s['cama'] % 60))
        print('  a dormir      %d min (%dh%02d)' % (s['total'], s['total'] // 60, s['total'] % 60))
        for k, lab in (('profundo', 'profundo'), ('rem', 'REM'), ('leve', 'leve')):
            print('    %-9s %4d min  %4.1f%%' % (lab, s[k], 100.0 * s[k] / s['total']))
        print('    acordado  %4d min' % s['acordado_min'])
        if s.get('blocos'):
            print('  arquitetura:')
            for ini, st, n in s['blocos']:
                print('    %s  %-6s %3d min  %s' % (ini, st, n, '.' * (n // 3)))

    fc = r.get('fc')
    if fc:
        for lab, vs in (('noite', fc['noite']), ('dia', fc['dia'])):
            if vs:
                print('FC %s: n=%d  min=%d  media=%.0f  max=%d' % (
                    lab, len(vs), min(vs), sum(vs) / len(vs), max(vs)))

    if r.get('atividade'):
        a = r['atividade']
        print('ATIVIDADE %s: %s passos, %s m, %s kcal' % (
            a['date'], a['steps'], a['distance'], a['calories']))

    for d in r['desporto']:
        print('DESPORTO %s  %s  %.1f min  %.0f kcal%s' % (
            d['inicio'], d['tipo'], d['min'], d['kcal'],
            '  %.0f m' % d['dist_m'] if d['dist_m'] else ''))

    if r['vazios']:
        print('\nVAZIOS no export: %s' % ', '.join(r['vazios']))
        if 'BODY' in r['vazios']:
            print('  -> a balanca Xiaomi nao esta na Zepp. Export separado noutra app.')


if __name__ == '__main__':
    main()
