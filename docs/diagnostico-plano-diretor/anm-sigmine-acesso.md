# Acesso aos Processos Minerários do SIGMINE (ANM) — Medição de 2026-09-17

Este documento registra as medições efetuadas diretamente nos endpoints da Agência Nacional de Mineração (ANM) para embasar a integração dos processos minerários do SIGMINE no diagnóstico de Plano Diretor do **GisBR**.

---

## 1. Teste de `app.anm.gov.br` (Desempate do Host — D6, D8)

### Comando e Saída Crus

Tentativa via utilitário de verificação de TLS do projeto:

```
$ python3 tools/check_sources_tls.py --host app.anm.gov.br
app.anm.gov.br -> nenhum certificado recebido [ERRO]
```

Tentativas de conexão direta via HTTP e HTTPS (`curl`):

```
$ curl -iv --max-time 10 https://app.anm.gov.br/
* Host app.anm.gov.br:443 was resolved.
* IPv4: 200.198.193.243
* Trying 200.198.193.243:443...
* Connected to app.anm.gov.br (200.198.193.243) port 443
* Connection timed out after 10002 milliseconds
* Closing connection
curl: (28) Connection timed out after 10002 milliseconds

$ curl -iv --max-time 5 http://app.anm.gov.br/
* Host app.anm.gov.br:80 was resolved.
* IPv4: 200.198.193.243
* Trying 200.198.193.243:80...
* Connection timed out after 5002 milliseconds
* Closing connection
curl: (28) Connection timed out after 5002 milliseconds
```

### Conclusão Binária

**NÃO RESPONDE** (servidor inacessível / tempo limite de conexão esgotado).

### Impacto na Decisão de Arquitetura (D8)

Como o host `app.anm.gov.br` (onde se localizavam os downloads em lote / shapefiles zipados da ANM) está offline e não responde a requisições de rede, a decisão **D8** confirma que a única alternativa funcional e automatizada para o plugin é consumir o SIGMINE via serviço ArcGIS REST Server em `geo.anm.gov.br`. Caso `app.anm.gov.br` volte a responder no futuro, a URL exata do ZIP, tamanho e data de referência deverão ser aferidos e documentados.

---

## 2. Conjunto Completo dos Valores de `FASE` (Medição 10)

### Comportamento do MapServer (`returnDistinctValues`)

Ao consultar a API do MapServer (`https://geo.anm.gov.br/arcgis/rest/services/SIGMINE/dados_anm/MapServer/0/query`):
- A utilização de `returnDistinctValues=true` acompanhada de filtro geométrico retorna **erro HTTP 400**: `{"code": 400, "message": "Geometry is not supported with DISTINCT.", "details": []}`.
- A utilização de `returnDistinctValues=true` com `returnGeometry=false` faz com que o servidor ignore a cláusula de busca distinta, retornando todos os registros sem desduplicação até o limite máximo de 5.000 feições por requisição.

### Apuração por Contagem (Estado de Minas Gerais — MG)

Diante disso, a apuração dos valores foi realizada por varredura com contagem completa no estado de Minas Gerais (MG), utilizando uma grade espacial 10x10 para garantir que nenhuma sub-região ultrapassasse o limite de 5.000 feições por requisição.

Total de processos minerários únicos contabilizados em MG: **48.827**.

### Literais de `FASE` em Minas Gerais (exatamente como retornados pela API)

1. `APTO PARA DISPONIBILIDADE` (552)
2. `AUTORIZAÇÃO DE PESQUISA` (24.533)
3. `CONCESSÃO DE LAVRA` (3.126)
4. `DIREITO DE REQUERER A LAVRA` (1.028)
5. `DISPONIBILIDADE` (1.766)
6. `LAVRA GARIMPEIRA` (276)
7. `LICENCIAMENTO` (3.388)
8. `RECONHECIMENTO GEOLÓGICO` (2)
9. `REGISTRO DE EXTRAÇÃO` (225)
10. `REQUERIMENTO DE LAVRA` (5.940)
11. `REQUERIMENTO DE LAVRA GARIMPEIRA` (1.400)
12. `REQUERIMENTO DE LICENCIAMENTO` (2.208)
13. `REQUERIMENTO DE PESQUISA` (4.074)
14. `REQUERIMENTO DE REGISTRO DE EXTRAÇÃO` (309)

*(Nota: Em varredura nacional por amostragem, identificou-se adicionalmente a ocorrência dos valores `DADO NÃO CADASTRADO` e string em branco/vazia `" "` em pequenos lotes residuais fora de MG).*

---

## 3. Campos da Base e Referencial Cartográfico / CRS (Medição 9)

### Campos de `geo.anm.gov.br` (Layer 0 — Processos minerários ativos)

Endpoint: `https://geo.anm.gov.br/arcgis/rest/services/SIGMINE/dados_anm/MapServer/0`

| Nome do Campo | Tipo ArcGIS | Alias Exibido |
|---|---|---|
| `PROCESSO` | `esriFieldTypeString` | Processo |
| `NUMERO` | `esriFieldTypeInteger` | Número |
| `ANO` | `esriFieldTypeSmallInteger` | Ano |
| `FASE` | `esriFieldTypeString` | Fase |
| `NOME` | `esriFieldTypeString` | Titular |
| `SUBS` | `esriFieldTypeString` | Substância |
| `USO` | `esriFieldTypeString` | Uso |
| `AREA_HA` | `esriFieldTypeDouble` | Área (ha) |
| `UF` | `esriFieldTypeString` | UF |
| `ULT_EVENTO` | `esriFieldTypeString` | Último evento |
| `ID` | `esriFieldTypeString` | ID |
| `FID` | `esriFieldTypeOID` | FID |
| `Shape` | `esriFieldTypeGeometry` | Shape |
| `DSProcesso` | `esriFieldTypeString` | Processo minerário |

### Conferência do CRS

- O serviço ArcGIS REST da ANM em `geo.anm.gov.br` declara nativamente a referência espacial `EPSG:4674` (SIRGAS 2000 em coordenadas geográficas).
- Devido à indisponibilidade de `app.anm.gov.br`, a conferência do arquivo `.prj` do shapefile ZIP em lote não pôde ser realizada via download direto.
- **Orientações para o caso de uso de arquivos ZIP manuais**: Se um arquivo Shapefile de processos minerários for obtido por download manual e seu arquivo `.prj` estiver ausente ou indicar datum legado (ex.: SAD69 / EPSG:4291 ou WGS84 / EPSG:4326), o fluxo deve atribuir explicitamente a camada ao CRS `EPSG:4674` (SIRGAS 2000) e reprojetar para o sistema de coordenadas de destino do projeto (`EPSG:4674` ou `EPSG:31983` para UTM 23S).

---

## 4. Comparação entre a Base Nacional e a Fonte `anm_sigmine` Existente (D7)

A fonte `anm_sigmine` existente no GisBR consome o serviço interativo ArcGIS REST da ANM (`geo.anm.gov.br`), permitindo consultas espacialmente filtradas por bounding-box diretamente durante a execução do diagnóstico. Em contrapartida, os downloads em lote via zip (historicamente em `app.anm.gov.br`) entregariam a base nacional completa em Shapefile/CSV para uso offline, porém exigem processamento local massivo e dependem de um host que atualmente se encontra indisponível.
