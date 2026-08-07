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
import os, sys, json, base64, urllib.parse, urllib.request, urllib.error, datetime

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


def autenticar(email, palavra):
    # 1. codigo de acesso
    url = 'https://api-user.huami.com/registrations/%s/tokens' % urllib.parse.quote(email, safe='')
    status, headers, corpo = _post(url, {
        'client_id': 'HuaMi', 'password': palavra, 'redirect_uri': REDIRECT,
        'token': 'access'}, seguir=False)
    loc = headers.get('Location', '')
    if DIAG:
        print('[diag] passo 1: HTTP %s  Location=%s' % (status, loc[:120] or '(vazia)'))
    if 'access=' not in loc:
        raise SystemExit('Passo 1 falhou (HTTP %s). Email ou palavra-passe errados, '
                         'ou a Zepp mudou o endpoint.\nResposta: %s' % (status, corpo[:300]))
    q = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query)
    codigo = q['access'][0]
    pais = (q.get('country_code') or ['PT'])[0]

    # 2. login
    status, _, corpo = _post('https://account.huami.com/v2/client/login', {
        'app_name': 'com.xiaomi.hm.health', 'app_version': '4.6.0', 'code': codigo,
        'country_code': pais, 'device_id': '02:00:00:00:00:00', 'device_model': 'phone',
        'grant_type': 'access_token', 'third_name': 'huami', 'allow_registration': 'false',
        'dn': 'account.huami.com,api-user.huami.com,api-mifit.huami.com',
        'source': 'com.xiaomi.hm.health', 'lang': 'pt'})
    dados = json.loads(corpo)
    if DIAG:
        seguro = {k: v for k, v in dados.items() if k != 'token_info'}
        print('[diag] passo 2: HTTP %s  %s' % (status, json.dumps(seguro)[:300]))
    ti = dados.get('token_info')
    if not ti or not ti.get('app_token'):
        raise SystemExit('Passo 2 falhou (HTTP %s): %s' % (status, corpo[:400]))
    host = ti.get('region') or 'api-mifit-de.huami.com'
    if not host.startswith('api-'):
        host = 'api-mifit-%s.huami.com' % host
    print('Autenticado. utilizador=%s  regiao=%s' % (ti['user_id'], host))
    return ti['app_token'], ti['user_id'], host


def buscar(app_token, uid, host, de, ate):
    url = ('https://%s/v1/data/band_data.json?query_type=summary&device_type=android_phone'
           '&userid=%s&from_date=%s&to_date=%s' % (host, uid, de, ate))
    status, corpo = _get(url, {'apptoken': app_token})
    d = json.loads(corpo)
    if DIAG:
        print('[diag] band_data: HTTP %s  code=%s  n=%d' % (
            status, d.get('code'), len(d.get('data') or [])))
    if not d.get('data'):
        raise SystemExit('band_data sem dados (HTTP %s): %s' % (status, corpo[:400]))
    return d['data']


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
    email = os.environ.get('ZEPP_EMAIL')
    palavra = os.environ.get('ZEPP_PASSWORD')
    if not email or not palavra:
        raise SystemExit('Faltam ZEPP_EMAIL e ZEPP_PASSWORD no ambiente.')

    dias = 7
    if '--dias' in sys.argv:
        dias = int(sys.argv[sys.argv.index('--dias') + 1])
    hoje = datetime.date.today()
    de, ate = hoje - datetime.timedelta(days=dias), hoje

    app_token, uid, host = autenticar(email, palavra)
    registos = buscar(app_token, uid, host, de.isoformat(), ate.isoformat())
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
