# Acesso às parcelas do SIGEF (INCRA) — medição de 2026-08-23

Este documento existe para registrar, com medição na mão, o que acontece quando
se tenta integrar as parcelas certificadas do SIGEF a partir do endpoint
`https://certificacao.incra.gov.br/csv_shp/export_shp.py`. O pedido chegou
como "colocar o SIGEF a partir dessa URL"; a resposta, medida em 2026-08-23, é
que **aquela URL não é pública** — está atrás de login gov.br — e que nenhuma
alternativa anônima existe hoje. As duas tabelas abaixo são transcrições
literais da medição; nada aqui foi re-testado ou "melhorado".

## Medição ao vivo do endpoint pedido

`https://certificacao.incra.gov.br/csv_shp/export_shp.py`

| Tentativa | Resultado medido |
|---|---|
| GET sem parâmetro | **HTTP 200**, 11.966 b, `Content-Type` ausente, corpo = **página de login HTML** (`saved from url=https://acervofundiario.incra.gov.br/acervo/login.php`) |
| GET `tipo=shp&formato=shp&uf=MG&municipio=3118601` | idêntico — 200 / 11.966 b / login |
| GET `tipo=privado…`, `tipo=publico…`, `tipo=csv…`, só `uf=MG`, sem `tipo` | idênticos — 200 / 11.966 b / login |
| POST mesmo corpo | idêntico — 200 / 11.966 b / login |
| `GET /csv_shp/` (listagem) | **HTTP 403** (IIS 7.5 — 403.14) |
| `GET /csv_shp/export_csv.py` | **HTTP 502** |

O único `href` acionável da página é:

```
https://sso.acesso.gov.br/authorize
  ?client_id=certificacao.incra.gov.br
  &redirect_uri=https://certificacao.incra.gov.br/csv_shp/export_shp.py
  &response_type=code
  &scope=openid+email+phone+profile+govbr_confiabilidades
```

Ou seja: **OIDC authorization-code do gov.br**, conta pessoal de CPF,
interativa (2FA/captcha). Não há chave de API, não há token anônimo, e o
`redirect_uri` está fixado no próprio `export_shp.py` — não dá para
consumir fora de um navegador logado.

⚠️ Note que o endpoint devolve **200 com corpo de erro**, exatamente a
armadilha já catalogada no `CLAUDE.md` §10. Se alguém tivesse plugado essa
URL num conector sem inspecionar o corpo, o GDAL falharia com "não foi
possível abrir a camada" e ninguém descobriria que o motivo é login.

## Busca por alternativa pública — todas negativas

| Candidato | Resultado |
|---|---|
| `geoservicos.inde.gov.br/geoserver/INCRA/ows` (WFS GetCapabilities) | **404** |
| `geoservicos.inde.gov.br/geoserver/ows` — capabilities global (3,59 MB, todos os workspaces) | **zero** ocorrências de `incra`/`sigef` em qualquer tag. Workspaces presentes: ATT, BAPSlvdor, BDES, COMPAAz, DIT, DPC, DPHDM, EPE, ICA, ICMBio, IFPI, IEA, ISA, MAPA, MDIC, MDS, MGPovLi, MInfr, MMA, MPA, MPOG, MPOR, MTU, PGGM, PIPRODATER, RJPCboFrio, RJPPrcbi, SCSJFMADS, SEMACECE, SPM, SPU, UFABC, UILA, VALEC, gn |
| `acervofundiario.incra.gov.br/geoserver/ows` | **404** |
| `acervofundiario.incra.gov.br/i3geo/ogc.php` | **timeout** (sem resposta em 45 s) |
| `acervofundiario.incra.gov.br/` | 200, mas é só `<meta refresh>` → `/acervo/acv.php` (gov.br) |
| `geoservicos.incra.gov.br` | **não responde** |
| `certificacao.incra.gov.br/arcgis/rest/services?f=json` | **404** |
| `sigef.incra.gov.br` | 200, mas o portal inteiro é gov.br SSO — nenhum link OGC/API na home |
| `dados.gov.br/api/publico/conjuntos-dados?nomeConjuntoDados=SIGEF` | **401** (API do dados.gov.br também exige credencial) |
| geobr/IPEA (v1 ou v2) | não publica parcelas certificadas — não há geografia SIGEF no catálogo (§7 do `CLAUDE.md`) |

## Consequência para o plugin

**Conclusão da medição:** não existe hoje caminho anônimo, oficial e estável
para as parcelas SIGEF. O download manual autenticado é o único que existe.

Por isso o plugin consome essa base pelo protocolo **`arquivo`** (fonte
`incra_sigef_parcelas` em `gisbr/core/sources.py`): o usuário baixa o
arquivo logado no navegador com a própria conta gov.br, o plugin lê o
arquivo da pasta de downloads manuais e daí segue exatamente o pipeline
padrão das demais fontes — recorte pelo polígono do município → GeoPackage
→ projeto. Se o arquivo não estiver na pasta, a fonte pula com um aviso que
diz o que fazer (mesmo padrão de `requer_parquet`).

A URL de autenticação fica registrada apenas como `origem_url` da fonte,
para o aviso saber o que dizer ao usuário — nunca como `endpoint` de
conector. O plugin **não pede, não guarda e não manipula credencial gov.br
de forma nenhuma**.

## Nota de manutenção

Se o INCRA reabrir acesso anônimo (ou publicar as parcelas na INDE / num
GeoServer público), a fonte `incra_sigef_parcelas` deve migrar de
`protocolo="arquivo"` para `wfs`/`arcgis` — e aí sim passa a exigir âncora
TLS medida e cobertura em `check_sources_tls.py`. Re-testar os candidatos da
tabela "Busca por alternativa pública" antes de assumir que nada mudou.
