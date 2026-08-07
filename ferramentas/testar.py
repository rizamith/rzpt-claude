#!/usr/bin/env python3
"""Verifica o sistema todo de uma vez, no terminal local.

    python ferramentas/testar.py           tudo, sem escrever nada
    python ferramentas/testar.py --rede     inclui os testes que tocam na Zepp

Sem --rede nao faz um unico pedido a internet — util para correr as vezes que
se quiser sem arriscar o limite de pedidos (HTTP 429) do endpoint da Zepp.
"""
import os, sys, csv, glob, json, collections

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'ferramentas'))
os.chdir(RAIZ)

REDE = '--rede' in sys.argv
falhas = []


def secao(t):
    print('\n' + '=' * 68)
    print(t)
    print('=' * 68)


def ok(t):
    print('  [ok]    %s' % t)


def mau(t):
    print('  [FALHA] %s' % t)
    falhas.append(t)


def aviso(t):
    print('  [aviso] %s' % t)


# ------------------------------------------------------------------ modulos
secao('1. Modulos carregam')
mods = {}
for nome in ('fit', 'zepp', 'zepp_api', 'sincronizar', 'dedup'):
    try:
        mods[nome] = __import__(nome)
        ok('%s.py' % nome)
    except Exception as e:
        mau('%s.py -> %s' % (nome, e))

# ------------------------------------------------------------------- dados
secao('2. Integridade dos CSV')
ESPERADO = {
    'corpo.csv': 'data,peso_kg,gordura_pct',
    'natacao.csv': 'data,prova,piscina_m',
    'treinos.csv': 'data,modalidade,duracao_min',
    'sono.csv': 'data,deitar,acordar',
    'atividade.csv': 'data,passos,distancia_m',
    'forca.csv': 'data,exercicio,series',
    'prontidao.csv': 'data,carga_pct,fadiga',
    'nutricao.csv': 'data,adesao_0_5,kcal',
}
for f, prefixo in ESPERADO.items():
    caminho = os.path.join('dados', f)
    if not os.path.exists(caminho):
        mau('%s nao existe' % f)
        continue
    linhas = list(csv.DictReader(open(caminho, encoding='utf-8')))
    cab = open(caminho, encoding='utf-8').readline().strip()
    if not linhas:
        aviso('%-14s vazio (so cabecalho)' % f)
        continue
    if not cab.startswith(prefixo):
        mau('%s: cabecalho inesperado -> %s' % (f, cab[:60]))
        continue
    ncol = len(cab.split(','))
    maus = [i for i, l in enumerate(linhas, 2) if len(l) != ncol or None in l.values()]
    datas = [l['data'] for l in linhas if l.get('data')]
    fora = [d for d in datas if not (len(d) == 10 and d[4] == '-' and d[7] == '-')]
    if maus:
        mau('%s: %d linha(s) com numero de colunas errado (ex. linha %d)' % (f, len(maus), maus[0]))
    elif fora:
        mau('%s: %d data(s) mal formatada(s), ex. %s' % (f, len(fora), fora[0]))
    else:
        ok('%-14s %5d linhas, %d colunas, %s -> %s' % (
            f, len(linhas), ncol, min(datas) if datas else '-', max(datas) if datas else '-'))

# ---------------------------------------------------------------- coerencia
secao('3. Coerencia dos dados')
tre = list(csv.DictReader(open('dados/treinos.csv', encoding='utf-8')))
origens = [l['origem'] for l in tre if l.get('origem')]
dups = [o for o, n in collections.Counter(origens).items() if n > 1]
if dups:
    mau('origens repetidas em treinos.csv: %s' % dups[:3])
else:
    ok('treinos.csv sem origens repetidas (%d com origem, %d sem)' % (
        len(origens), len(tre) - len(origens)))

chaves = collections.Counter((l['data'], l['modalidade'], l['duracao_min']) for l in tre)
rep = [k for k, n in chaves.items() if n > 1]
if rep:
    mau('%d sessao(oes) possivelmente duplicada(s), ex. %s. Correr dedup.py' % (len(rep), rep[0]))
else:
    ok('sem duplicados por (data, modalidade, duracao)')

sem_rpe = [l for l in tre if not l.get('rpe') and l['modalidade'] not in
           ('trotinete', 'caminhada', 'descanso')]
if sem_rpe:
    aviso('%d sessao(oes) de treino sem RPE (o mais recente: %s %s)' % (
        len(sem_rpe), sem_rpe[-1]['data'], sem_rpe[-1]['modalidade']))

corpo = list(csv.DictReader(open('dados/corpo.csv', encoding='utf-8')))
pesos = [(l['data'], float(l['peso_kg'])) for l in corpo if l.get('peso_kg')]
absurdos = [(d, p) for d, p in pesos if not 60 < p < 150]
if absurdos:
    mau('peso fora do plausivel: %s' % absurdos[:3])
else:
    ok('%d pesagens, todas entre %.1f e %.1f kg' % (
        len(pesos), min(p for _, p in pesos), max(p for _, p in pesos)))

nat = list(csv.DictReader(open('dados/natacao.csv', encoding='utf-8')))
mal = [l for l in nat if l.get('piscina_m') not in ('25', '50')]
if mal:
    mau('%d tempo(s) de natacao sem piscina valida' % len(mal))
else:
    ok('%d tempos de natacao, todos com piscina 25 ou 50 m' % len(nat))

# ------------------------------------------------------------------- leitor
secao('4. Leitor de FIT')
fits = glob.glob(r'G:\My Drive\Zepp\*.fit') + glob.glob('import/Zepp/*.fit')
if not fits:
    aviso('nenhum .fit encontrado para testar')
else:
    for c in fits[:3]:
        try:
            r, _, recs = mods['fit'].resumo(mods['fit'].parse(c))
            ok('%s -> %s, %.0f min, %s kcal, %d amostras' % (
                os.path.basename(c), r['modalidade'], r['duracao_min'], r['kcal'], len(recs)))
        except Exception as e:
            mau('%s -> %s' % (os.path.basename(c), e))

# ---------------------------------------------------------------- segredos
secao('5. Credenciais')
za = mods.get('zepp_api')
if za:
    s = za.ler_segredos()
    if not s:
        # Na nuvem o ficheiro de segredos NAO existe por desenho: as credenciais
        # vem dos Secrets do GitHub Actions. Marcar isto como falha ensinava a
        # ignorar o resultado do testar.py no ambiente onde ele mais corre.
        if os.name == 'nt':
            mau('%s nao existe ou esta ilegivel' % za.SEGREDOS)
        else:
            aviso('sem ficheiro de segredos — normal fora do PC; na nuvem '
                  'as credenciais vem do ambiente')
    else:
        for campo, obrig in (('email', True), ('password', False),
                             ('app_token', False), ('user_id', False)):
            v = str(s.get(campo) or '')
            if v:
                ok('%-10s presente (%d caracteres)' % (campo, len(v)))
            elif obrig:
                mau('%-10s EM FALTA' % campo)
            else:
                aviso('%-10s vazio' % campo)
        if s.get('app_token') and s.get('user_id'):
            ok('ha app_token: as buscas nao precisam de autenticar')
        elif s.get('password'):
            aviso('sem app_token. Correr: python ferramentas/zepp_api.py --token')
        else:
            aviso('preencher "password" em %s' % za.SEGREDOS)

# --------------------------------------------------------------------- rede
secao('6. Zepp (so com --rede)')
if not REDE:
    print('  saltado. Acrescentar --rede para testar.')
    print('  Deliberado: cada tentativa de autenticacao conta para o limite de')
    print('  pedidos da Zepp, e o bloqueio dura dezenas de minutos.')
else:
    try:
        token, uid, hosts = za.obter_token()
        ok('credenciais resolvidas (utilizador %s)' % uid)
        import datetime
        hoje = datetime.date.today()
        regs = za.buscar(token, uid, hosts, (hoje - datetime.timedelta(days=2)).isoformat(),
                         hoje.isoformat())
        ok('%d dia(s) devolvido(s)' % len(regs))
        sono, ativ = za.converter(regs)
        for x in sono:
            ok('sono %s: %d min (prof %d, REM %d), FC min %s' % (
                x['data'], x['sono_min'], x['profundo_min'], x['rem_min'], x['fc_min']))
        for x in ativ:
            ok('atividade %s: %s passos, FC repouso %s' % (
                x['data'], x['passos'], x['fc_repouso']))
        if not sono:
            aviso('nenhum dia com sono no intervalo')
    except SystemExit as e:
        mau(str(e).splitlines()[0])
    except Exception as e:
        mau('%s: %s' % (type(e).__name__, e))

# ------------------------------------------------------------------ resumo
secao('RESUMO')
if falhas:
    print('  %d falha(s):' % len(falhas))
    for f in falhas:
        print('    - %s' % f)
    sys.exit(1)
print('  Tudo ok.')
