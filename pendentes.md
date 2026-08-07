# Pendentes

Perguntas em aberto e coisas por fazer. **Lê isto no início de qualquer sessão** — é o que
transporta o contexto entre conversas, já que as conversas não viajam entre dispositivos.

Quando algo se resolver, apaga a linha e escreve o resultado no ficheiro que lhe corresponde
(`perfil.md`, `clinico.md`, `plano.md`, ou o CSV certo).

Última revisão: 2026-08-07.

---

## A perguntar ao Ricardo — por ordem de valor

1. **RPE das sessões de 1 a 6 de agosto.** Seis sessões registadas, zero RPE. É o único
   bloqueio para avaliar se a semana produziu algo. Mesmo aproximado ou de memória serve.
2. **O `tipo42` é snowboard?** 16 sessões de ~199 min e ~21 km, em abril/2026. Está em
   `dados/treinos.csv` com o código em bruto por não estar identificado.
3. **De onde vem a pesagem de 25/07/2026 no export da Zepp?** Diz 100.0 kg com 18.5 % de gordura
   e 75.3 % de músculo; a balança Xiaomi diz 27.6 % e 68.3 % para o mesmo peso. Está importada
   com `fonte=zepp` para não contaminar a série, mas não se sabe que aparelho a produziu.
4. **O tinnitus está presente actualmente?** Historicamente reativo a stress e falta de sono, e
   é o indicador de sobrecarga do SNC. Sem isto não há linha de base.
5. **O hábito de "pastar" frutos secos ao fim da tarde cessou?** Vinha dos relatórios importados.
6. **O recordista dos 31.90 nos 50 Bruços está na faixa 50–54 e vai a março de 2027?** Em masters
   a composição do pódio muda de ano para ano, e isso altera a leitura do objetivo.

## Clínico — a levar ao médico

- [ ] **Análises de sangue:** glicemia/HbA1c, perfil lipídico, enzimas hepáticas e **ferritina**.
      Justificação: gordura visceral em 11 ("muito alta"), álcool regular, e a ferritina é
      indispensável antes de retomar o suplemento de ferro (ver `suplementos.md`).
- [ ] **Confirmar a margem real do ombro** com médico ou fisioterapeuta antes de subir volume de
      bruços. Está a 95 % por sensação própria, sem alta documentada — e bruços era precisamente
      o estilo proibido pela RM de abril/2026.

## Sistema

- [ ] **Na primeira sessão pelo telemóvel, verificar:** faz `commit` directo no `main` ou abre
      pull request? E o conector do Google Drive está disponível? Se estiver, a importação dos
      treinos deixa de precisar do PC.
- [ ] **Apagar os Secrets `ZEPP_EMAIL` e `ZEPP_PASSWORD`** do GitHub. A via da API está fechada,
      não servem para nada e é credencial a mais na nuvem.
- [ ] **Apagar a conta Zepp `rzamith@drig.pt`**, criada só para diagnóstico.
- [ ] **Decidir se se limpa a `password` de `C:\dev\_secrets\zepp_secrets.json`.** Sem a API a
      funcionar, não tem utilidade.
- [ ] **Export da Zepp:** nesta fase inicial, mais do que uma vez por mês — a série de sono só
      tem 11 noites contínuas e precisa de massa crítica.

## Decidido, para não se reabrir

- **Balança S400: fica na foto.** As vias automáticas estão esgotadas — BLE não resolvido para
  este modelo (issues abertas no Home Assistant), sem export na app, e o Ricardo não é o dono do
  dispositivo. A foto custa 10 segundos e é fiável.
- **API da Zepp: fechada.** O endpoint de autenticação devolve sempre 429. Eliminadas por teste
  as explicações de conta, IP, cliente antigo e tempo. Ver `CLAUDE.md`.
- **Sem Strava.** Os treinos já chegam pelo Drive; era dependência a mais sem ganho.
- **Relógio não vai à água nem se usa a dormir por gosto** — o Ricardo espera pelo Amazfit Helio
  Strap 2. Entretanto o volume de natação entra por texto, e tem dormido com o Balance desde
  27/07 apesar de não gostar.
