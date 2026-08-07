#!/usr/bin/env python3
"""Busca dados da Zepp pela API da propria app, sem export manual.

    ZEPP_EMAIL=... ZEPP_PASSWORD=... python ferramentas/zepp_api.py --dias 7
    ... --importar     escreve em dados/sono.csv e dados/atividade.csv
    ... --diag         imprime as respostas em bruto (sem a palavra-passe)

⚠️ API NAO OFICIAL. A Zepp nao publica API para utilizadores; isto usa os
mesmos endpoints que a app. Funciona, mas parte quando eles mudarem algo. O
export manual (ferramentas/zepp.py) fica como rede de seguranca.

Sem dependencias externas — so a biblioteca padrao, para correr no GitHub
Actions sem `pip install`.

Fluxo de autenticacao, em tres passos:
  1. POST api-user.huami.com/registrations/{email}/tokens  -> devolve um 303
     cuja Location tem o `access=...`. Nao se segue o redireccionamento.
  2. POST account.huami.com/v2/client/login com esse codigo -> app_token,
     user_id e o host regional a usar a seguir.
  3. GET  {host}/v1/data/band_data.json -> um registo por dia, com o sono e os
     passos num campo `summary` em JSON e a FC por minuto em base64.
"""
import os, sys, time, json, base64, urllib.parse, urllib.request, urllib.error, datetime

# A API devolve instantes Unix. As linhas que ja estao em dados/sono.csv usam
# hora local, por isso convertemos para Europe/Lisbon. O zoneinfo existe no
# Ubuntu do Actions; no Windows pode faltar a tzdata, e nesse caso aproxima-se
# a regra da UE (ultimo domingo de marco ao ultimo domingo de outubro).
try:
    from zoneinfo import ZoneInfo
    LISBOA = ZoneInfo('Europe/Lisbon')
except Exception:
    LISBOA = None


def _local(unix):
    dt = datetime.datetime.fromtimestamp(int(unix), datetime.timezone.utc)
    if LISBOA is not None:
        return dt.astimezone(LISBOA)
    ultimo_dom = lambda a, m: max(
        d for d in (datetime.date(a, m, x) for x in range(25, 32)) if d.weekday() == 6)
    verao = (ultimo_dom(dt.year, 3) <= dt.date() < ultimo_dom(dt.year, 10))
    return dt + datetime.timedelta(hours=1 if verao else 0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zepp as zepplib

UA = 'MiFit/4.6.0 (iPhone; iOS 14.0; Scale/3.00)'
REDIRECT = 'https://s3-us-west-2.amazonaws.com/hm-registration/successsignin.html'
DIAG = '--diag' in sys.argv

try:                       # ordem correcta das linhas no log do GitHub Actions
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

# A Huami passou a chamar-se Zepp e manteve as duas infraestruturas. Contas mais
# recentes vivem em *.zepp.com, as antigas em *.huami.com. Tentam-se as duas.
HOSTS_AUTH = [('api-user.huami.com', 'account.huami.com'),
              ('api-user.zepp.com', 'account.zepp.com')]


def _post(url, dados, headers=None, seguir=True):
    corpo = urllib.parse.urlencode(dados).encode()
    h = {'User-Agent': UA, 'Content-Type': 'application/x-www-form-urlencoded'}
    h.update(headers or {})
    req = urllib.request.Request(url, data=corpo, headers=h)

    class SemRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    op = urllib.request.build_opener() if seguir else urllib.request.build_opener(SemRedirect)
    try:
        with op.open(req, timeout=30) as r:
            return r.status, dict(r.headers), r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode('utf-8', 'replace')


def _get(url, headers=None):
    h = {'User-Agent': UA}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')


# A Zepp/Huami tem variantes por regiao e por versao da app. Em vez de gastar
# uma ronda de depuracao por cada uma, tentam-se todas e reporta-se o que cada
# uma respondeu.
THIRD_NAMES = ['huami', 'email', 'huami_phone']
HOSTS = ['api-mifit-de.huami.com', 'api-mifit-de2.huami.com',
         'api-mifit-us2.huami.com', 'api-mifit.huami.com']


ESPERAS = [0, 45, 90, 180]   # segundos antes de cada tentativa, em caso de 429


def _tentar_passo1(email, palavra, user_host, account_host):
    """(codigo, pais, account_host) | ('429', ...) | None"""
    url = 'https://%s/registrations/%s/tokens' % (
        user_host, urllib.parse.quote(email, safe=''))
    status, headers, corpo = _post(url, {
        'client_id': 'HuaMi', 'password': palavra, 'redirect_uri': REDIRECT,
        'token': 'access'}, seguir=False)
    loc = headers.get('Location', '')
    erro = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query).get('error', [''])[0]
    print('[passo 1] %s -> HTTP %s  %s' % (
        user_host, status, loc[:150] or (corpo[:200].strip() or '(sem Location)')), flush=True)
    if 'access=' in loc:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query)
        print('[passo 1] ok em %s' % user_host, flush=True)
        return q['access'][0], (q.get('country_code') or ['PT'])[0], account_host
    if status == 429 or '"code":12' in corpo or 'too many requests' in corpo.lower():
        return '429', None, None
    return None, erro or str(status), None


def passo1(email, palavra):
    """Troca email+palavra por um codigo de acesso.

    Tenta os dois dominios (Huami e Zepp) e, em caso de HTTP 429, volta a
    tentar com esperas crescentes: a Zepp limita pedidos ao endpoint de tokens
    e algumas tentativas seguidas bastam para bloquear durante minutos.
    """
    ultimo = None
    for i, espera in enumerate(ESPERAS):
        if espera:
            print('[passo 1] limitado por excesso de pedidos. A esperar %ds '
                  '(tentativa %d de %d)...' % (espera, i + 1, len(ESPERAS)), flush=True)
            time.sleep(espera)
        limitado = False
        for user_host, account_host in HOSTS_AUTH:
            a, b, c = _tentar_passo1(email, palavra, user_host, account_host)
            if a == '429':
                # Os dois dominios partilham a infraestrutura: insistir no
                # segundo so agrava o limite. Esperar e o unico caminho.
                limitado = True
                break
            if a:
                return a, b, c
            ultimo = b
        if not limitado:
            break        # falha real, nao vale esperar

    if ultimo in (None, '429'):
        raise SystemExit(
            'PASSO 1 FALHOU por LIMITE DE PEDIDOS (HTTP 429), nao por credenciais.\n'
            'A Zepp bloqueia o endpoint de tokens depois de varias tentativas seguidas,\n'
            'e ja esperamos %ds sem sucesso.\n'
            'NAO mexas na conta nem nos Secrets: nao e ai o problema.\n'
            'Espera 30 a 60 minutos e corre o workflow outra vez.' % sum(ESPERAS))
    if ultimo == '401':
        raise SystemExit(
            'PASSO 1 FALHOU com error=401: a Zepp rejeitou o par email/palavra-passe.\n'
            '  1. Confirma que consegues entrar na app com exactamente essas credenciais.\n'
            '  2. Se a conta nao tem palavra-passe propria (criada com Google/Apple),\n'
            '     define uma nas definicoes da conta Zepp.\n'
            '  3. Se a conta se identifica por telefone, diz-me: o endpoint aceita o\n'
            '     numero com indicativo no lugar do email.')
    raise SystemExit('PASSO 1 FALHOU com erro inesperado: %s. Ver as linhas [passo 1] acima.'
                     % ultimo)


def autenticar(email, palavra):
    codigo, pais, account_host = passo1(email, palavra)
    print('[passo 1] country_code=%s, login por %s' % (pais, account_host))

    # --- passo 2: trocar o codigo por app_token ---------------------------
    erros = []
    for tn in THIRD_NAMES:
        status, _, corpo = _post('https://%s/v2/client/login' % account_host, {
            'app_name': 'com.xiaomi.hm.health', 'app_version': '4.6.0', 'code': codigo,
            'country_code': pais, 'device_id': '02:00:00:00:00:00', 'device_model': 'phone',
            'grant_type': 'access_token', 'third_name': tn, 'allow_registration': 'false',
            'dn': 'account.huami.com,api-user.huami.com,api-mifit.huami.com',
            'source': 'com.xiaomi.hm.health', 'lang': 'pt'})
        try:
            dados = json.loads(corpo)
        except ValueError:
            erros.append('third_name=%s -> HTTP %s, resposta nao e JSON: %s' % (tn, status, corpo[:200]))
            continue
        ti = dados.get('token_info') or {}
        if ti.get('app_token'):
            print('[passo 2] ok com third_name=%s. utilizador=%s' % (tn, ti['user_id']))
            regiao = ti.get('region') or ''
            hosts = HOSTS[:]
            if regiao:
                h = regiao if regiao.startswith('api-') else 'api-mifit-%s.huami.com' % regiao
                hosts = [h] + [x for x in hosts if x != h]
            return ti['app_token'], ti['user_id'], hosts
        erros.append('third_name=%s -> HTTP %s, code=%s, msg=%s' % (
            tn, status, dados.get('code'), dados.get('message') or dados.get('error_code')))
    print('[passo 2] todas as variantes falharam:')
    for e in erros:
        print('   ' + e)
    raise SystemExit('PASSO 2 FALHOU. O codigo do passo 1 foi obtido, portanto as credenciais '
                     'estao certas — o problema esta no login. As mensagens acima dizem qual.')


def buscar(app_token, uid, hosts, de, ate):
    erros = []
    for host in hosts:
        url = ('https://%s/v1/data/band_data.json?query_type=summary'
               '&device_type=android_phone&userid=%s&from_date=%s&to_date=%s'
               % (host, uid, de, ate))
        status, corpo = _get(url, {'apptoken': app_token})
        try:
            d = json.loads(corpo)
        except ValueError:
            erros.append('%s -> HTTP %s, nao e JSON: %s' % (host, status, corpo[:200]))
            continue
        n = len(d.get('data') or [])
        print('[passo 3] %s -> HTTP %s, code=%s, %d dia(s)' % (host, status, d.get('code'), n))
        if n:
            if DIAG:
                print('[diag] chaves do primeiro dia: %s' % sorted(d['data'][0].keys()))
                print('[diag] summary em bruto: %s' % str(d['data'][0].get('summary'))[:600])
            return d['data']
        erros.append('%s -> HTTP %s, sem dados: %s' % (host, status, corpo[:300]))
    print('[passo 3] nenhum host devolveu dados:')
    for e in erros:
        print('   ' + e)
    raise SystemExit('PASSO 3 FALHOU. Autenticacao ok mas nenhum host regional devolveu dados. '
                     'Pode ser regiao errada ou o intervalo de datas nao ter nada.')


def fc_do_dia(b64):
    """data_hr: um byte por minuto desde as 00:00. 0 e 255 sao invalidos."""
    if not b64:
        return {}
    try:
        bs = base64.b64decode(b64)
    except Exception:
        return {}
    vals = [(i, v) for i, v in enumerate(bs) if 0 < v < 255]
    if not vals:
        return {}
    noite = [v for i, v in vals if i < 360]          # antes das 06:00
    todos = [v for _, v in vals]
    return {'min': min(noite) if noite else min(todos),
            'media': round(sum(todos) / len(todos)), 'max': max(todos)}


def converter(registos):
    sono, atividade = [], []
    for r in registos:
        data = r.get('date_time') or r.get('date')
        try:
            s = json.loads(r.get('summary') or '{}')
        except ValueError:
            continue
        fc = fc_do_dia(r.get('data_hr'))

        slp = s.get('slp') or {}
        prof, leve = int(slp.get('dp') or 0), int(slp.get('lt') or 0)
        rem, acordado = int(slp.get('rem') or 0), int(slp.get('wk') or 0)
        total = prof + leve + rem
        if total > 0:
            deitar = _local(slp['st']).strftime('%H:%M') if slp.get('st') else ''
            acordar = _local(slp['ed']).strftime('%H:%M') if slp.get('ed') else ''
            sono.append({
                'data': data, 'deitar': deitar, 'acordar': acordar,
                'cama_min': total + acordado, 'sono_min': total, 'profundo_min': prof,
                'rem_min': rem, 'leve_min': leve, 'acordado_min': acordado,
                'fc_min': fc.get('min', ''), 'score': '', 'fonte': 'balance',
                'notas': 'API Zepp'})

        stp = s.get('stp') or {}
        passos = int(stp.get('ttl') or 0)
        if passos > 0:
            atividade.append({
                'data': data, 'passos': passos, 'distancia_m': int(stp.get('dis') or 0),
                'kcal_atividade': int(stp.get('cal') or 0), 'fc_repouso': fc.get('min', ''),
                'fc_media': fc.get('media', ''), 'fc_max': fc.get('max', ''),
                'fonte': 'balance'})
    return sono, atividade


def main():
    # strip(): colar num Secret do GitHub arrasta espacos e mudancas de linha
    # com facilidade, e isso sozinho da um 401.
    email = (os.environ.get('ZEPP_EMAIL') or '').strip()
    palavra = (os.environ.get('ZEPP_PASSWORD') or '').strip()
    if not email or not palavra:
        raise SystemExit('Faltam ZEPP_EMAIL e ZEPP_PASSWORD no ambiente.')
    print('Credenciais: email com %d caracteres, palavra-passe com %d.' % (len(email), len(palavra)))

    if '--passo1' in sys.argv:      # teste rapido, so a autenticacao
        passo1(email, palavra)
        print('Passo 1 ok.')
        return

    dias = 7
    if '--dias' in sys.argv:
        dias = int(sys.argv[sys.argv.index('--dias') + 1])
    hoje = datetime.date.today()
    de, ate = hoje - datetime.timedelta(days=dias), hoje

    app_token, uid, hosts = autenticar(email, palavra)
    registos = buscar(app_token, uid, hosts, de.isoformat(), ate.isoformat())
    sono, atividade = converter(registos)
    print('%s a %s: %d dia(s) devolvidos, %d com sono, %d com passos' % (
        de, ate, len(registos), len(sono), len(atividade)))

    if '--importar' not in sys.argv:
        for s in sono:
            print('  sono %s  %d min (prof %d / REM %d)  FC min %s' % (
                s['data'], s['sono_min'], s['profundo_min'], s['rem_min'], s['fc_min']))
        print('\nSem --importar nada foi escrito.')
        return

    n1, _ = zepplib.fundir('sono.csv', zepplib.COLS['sono'], sono, lambda l: l['data'])
    n2, _ = zepplib.fundir('atividade.csv', zepplib.COLS['atividade'], atividade,
                           lambda l: l['data'])
    print('sono.csv +%d   atividade.csv +%d' % (n1, n2))


if __name__ == '__main__':
    main()
