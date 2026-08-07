#!/usr/bin/env python3
"""Leitor de ficheiros .FIT exportados da app Zepp (Amazfit Balance).

A Zepp exporta cada treino como .fit — por vezes com extensao .zip enganadora,
mas o conteudo e FIT binario. Este leitor nao tem dependencias externas.

Uso:
    python ferramentas/fit.py <ficheiro.fit>              resumo legivel
    python ferramentas/fit.py <ficheiro.fit> --csv        linha para dados/treinos.csv
    python ferramentas/fit.py <ficheiro.fit> --minutos    FC media por minuto

Porque existe: o separador Esforco da app mostra indices proprietarios sem
significado externo. O .FIT tem a serie de FC crua a 1 Hz, que e o que permite
distinguir uma sessao densa de uma sessao com muito tempo parado.
"""
import struct, sys, datetime, collections

FIT_EPOCH = 631065600  # 1989-12-31T00:00:00Z

# base_type -> (tamanho_elemento, formato_struct, valor_invalido)
BT = {
    0x00: (1, 'B', 0xFF), 0x01: (1, 'b', 0x7F), 0x02: (1, 'B', 0xFF),
    0x83: (2, 'h', 0x7FFF), 0x84: (2, 'H', 0xFFFF),
    0x85: (4, 'i', 0x7FFFFFFF), 0x86: (4, 'I', 0xFFFFFFFF),
    0x07: (1, 's', None), 0x88: (4, 'f', None), 0x89: (8, 'd', None),
    0x0A: (1, 'B', 0), 0x8B: (2, 'H', 0), 0x8C: (4, 'I', 0),
    0x0D: (1, 'B', 0xFF), 0x8E: (8, 'q', None), 0x8F: (8, 'Q', None),
    0x90: (8, 'Q', 0),
}

SPORT = {0: 'generico', 1: 'corrida', 2: 'ciclismo', 4: 'maquina', 5: 'natacao',
         10: 'crossfit', 11: 'caminhada', 15: 'remo', 17: 'caminhada'}

# session: field_def_num -> nome
S = {253: 'timestamp', 2: 'start_time', 5: 'sport', 6: 'sub_sport',
     7: 'elapsed_ms', 8: 'timer_ms', 9: 'distancia_cm', 11: 'kcal',
     14: 'vel_media', 15: 'vel_max', 16: 'fc_media', 17: 'fc_max',
     24: 'efeito_aerobio_x10', 26: 'n_voltas', 64: 'fc_min',
     65: 'tempo_por_zona_ms', 137: 'efeito_anaerobio_x10'}


def ts(v):
    if v is None:
        return None
    return datetime.datetime.fromtimestamp(FIT_EPOCH + v, datetime.timezone.utc)


def _read(d, pos, dm):
    out, en = {}, dm['en']
    for fdn, sz, bt in dm['fields']:
        raw = d[pos:pos + sz]
        pos += sz
        if bt not in BT:
            out[fdn] = raw
            continue
        esz, fmt, inval = BT[bt]
        if fmt == 's':
            out[fdn] = raw.split(b'\x00')[0].decode('utf-8', 'replace')
            continue
        n = sz // esz
        try:
            vals = struct.unpack(en + fmt * n, raw)
        except struct.error:
            out[fdn] = raw
            continue
        vals = [None if (inval is not None and v == inval) else v for v in vals]
        out[fdn] = vals[0] if n == 1 else list(vals)
    for _, dsz, _ in dm['devf']:      # campos de developer: consumir, ignorar
        pos += dsz
    return out, pos


def parse(path):
    d = open(path, 'rb').read()
    if d[8:12] != b'.FIT':
        raise SystemExit('%s nao e um ficheiro FIT' % path)
    pos, end = d[0], d[0] + struct.unpack('<I', d[4:8])[0]
    defs, msgs = {}, collections.defaultdict(list)
    while pos < end:
        hdr = d[pos]
        pos += 1
        if hdr & 0x80:                        # cabecalho de timestamp comprimido
            dm = defs.get((hdr >> 5) & 0x03)
            if dm is None:
                break
            rec, pos = _read(d, pos, dm)
            msgs[dm['num']].append(rec)
            continue
        local = hdr & 0x0F
        if hdr & 0x40:                        # mensagem de definicao
            pos += 1
            en = '<' if d[pos] == 0 else '>'
            pos += 1
            gnum = struct.unpack(en + 'H', d[pos:pos + 2])[0]
            pos += 2
            nf = d[pos]
            pos += 1
            fields = []
            for _ in range(nf):
                fields.append((d[pos], d[pos + 1], d[pos + 2]))
                pos += 3
            devf = []
            if hdr & 0x20:                    # tem campos de developer
                nd = d[pos]
                pos += 1
                for _ in range(nd):
                    devf.append((d[pos], d[pos + 1], d[pos + 2]))
                    pos += 3
            defs[local] = {'num': gnum, 'en': en, 'fields': fields, 'devf': devf}
        else:                                 # mensagem de dados
            dm = defs.get(local)
            if dm is None:
                break
            rec, pos = _read(d, pos, dm)
            msgs[dm['num']].append(rec)
    return msgs


def resumo(msgs):
    ses = msgs.get(18, [{}])[0]
    g = lambda k: ses.get(k)
    recs = msgs.get(20, [])
    fc = [r[3] for r in recs if r.get(3)]
    dur = (g(7) or 0) / 1000.0
    out = {
        'inicio': ts(g(2)), 'modalidade': SPORT.get(g(5), 'sport=%s' % g(5)),
        'duracao_min': round(dur / 60, 1), 'kcal': g(11),
        'fc_media': g(16), 'fc_max': g(17), 'fc_min': g(64),
        'distancia_m': (g(9) or 0) / 100.0,
        'efeito_aerobio': (g(24) or 0) / 10.0,
        'efeito_anaerobio': (g(137) or 0) / 10.0,
        'amostras_fc': len(fc), 'zonas_ms': g(65),
    }
    return out, fc, recs


def main():
    path = sys.argv[1]
    modo = sys.argv[2] if len(sys.argv) > 2 else ''
    msgs = parse(path)
    r, fc, recs = resumo(msgs)

    if modo == '--csv':
        # data,modalidade,duracao_min,rpe,energia_1_5,resultado,dor_zona,dor_0_10,notas
        print('%s,%s,%d,,,%d kcal / FC %s-%s media %s,,,Importado de FIT. %d amostras a 1 Hz' % (
            r['inicio'].date(), r['modalidade'], round(r['duracao_min']), r['kcal'],
            r['fc_min'], r['fc_max'], r['fc_media'], r['amostras_fc']))
        return

    print('%s  %s' % (r['modalidade'].upper(), r['inicio']))
    print('  duracao        %.1f min' % r['duracao_min'])
    print('  calorias       %s kcal  (%.1f kcal/min)' % (r['kcal'], r['kcal'] / r['duracao_min']))
    if r['distancia_m']:
        print('  distancia      %.0f m' % r['distancia_m'])
    print('  FC             min %s / media %s / max %s bpm' % (r['fc_min'], r['fc_media'], r['fc_max']))
    print('  efeito treino  aerobio %.1f / anaerobio %.1f' % (r['efeito_aerobio'], r['efeito_anaerobio']))
    if r['zonas_ms']:
        tot = sum(z for z in r['zonas_ms'] if z)
        print('  tempo por zona (contagem do proprio relogio):')
        for i, z in enumerate(r['zonas_ms']):
            if z:
                print('     Z%d  %5.1f min  %4.1f%%' % (i, z / 60000.0, 100.0 * z / tot))

    if modo == '--minutos' and fc:
        t0 = [r_[253] for r_ in recs if r_.get(3)][0]
        bym = collections.OrderedDict()
        for rec in recs:
            if rec.get(3):
                bym.setdefault((rec[253] - t0) // 60, []).append(rec[3])
        print('\n  FC media por minuto:')
        for m, vs in bym.items():
            med = round(sum(vs) / len(vs))
            print('     min %3d  %3d  %s' % (m, med, '#' * max(0, (med - 60) // 3)))


if __name__ == '__main__':
    main()
