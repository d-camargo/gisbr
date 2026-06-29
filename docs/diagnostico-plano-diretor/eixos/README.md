# Mapeamento de Geoservers por Eixo Temático

Este diretório contém o catálogo de geoservers, serviços OGC (WMS/WFS), REST e bases de dados estruturados por eixo temático para subsidiar o diagnóstico municipal do Plano Diretor.

## Classificação por Eixo Temático

Os dados estão estruturados nos seguintes documentos:

1. [**Infraestrutura de Transportes**](1-transportes.md) — rodovias, ferrovias, aeródromos e vias urbanas.
2. [**Drenagem e Saneamento**](2-drenagem-saneamento.md) — hidrografia, bacias, reservatórios e redes de abastecimento.
3. [**Demografia**](3-demografia.md) — setores censitários, grades estatísticas e dados demográficos do IBGE.
4. [**Ambiental**](4-ambiental.md) — áreas protegidas, CAR, alertas de desmatamento e zoneamento ecológico-econômico.
5. [**Educação**](5-educacao.md) — equipamentos escolares e infraestrutura de ensino.
6. [**Saúde**](6-saude.md) — estabelecimentos de saúde, hospitais e divisões de regiões de saúde.

---

## Legenda e Estrutura das Tabelas

Cada documento possui tabelas estruturadas com as seguintes informações:

- **Fonte / Órgão:** Entidade pública ou privada produtora do dado.
- **Nível:** Abrangência geográfica (Federal, Estadual, Municipal).
- **Serviço:** Protocolo ou formato (WFS, WMS, ArcGIS REST, Download, API).
- **Endpoint / URL:** Link do serviço (com a URL direta de `GetCapabilities` para serviços OGC).
- **Camadas Principais:** Nomes das feições/camadas de interesse (`typeNames` ou `Layers`).
- **CRS:** Sistema de Referência de Coordenadas suportado (priorizando EPSG:4674 - SIRGAS 2000).
- **Licença:** Regras de uso (Open Data, Licença Pública, Requer Login, etc.).
- **Data de Acesso:** Data da verificação real de disponibilidade.
- **Status:** Status da verificação (`Online - GetCapabilities verificado`, `Não Confirmado - [Motivo/Erro]` ou `Apenas Download`).

## Resumo de Esforço e Cobertura (GisBR)

| Eixo | Nível de Cobertura Atual pelo GisBR | Esforço Necessário | Método de Integração Sugerido |
| --- | --- | --- | --- |
| 1. Transportes | Nenhuma | Médio | Conector WFS nativo (DNIT / DER-MG) |
| 2. Drenagem/Saneamento | Nenhuma | Médio | Conector WFS (SGB) ou ArcGIS REST (ANA) |
| 3. Demografia | **Alta** (resolvido por Fases 1 & 2) | Baixo | Reuso de algoritmos `read_census_tract` + `join_censo` |
| 4. Ambiental | **Média** (biomas, terras indígenas, UCs) | Médio | Conector WFS (ICMBio / SICAR) e WMS (MapBiomas) |
| 5. Educação | **Alta** (resolvido por Censo Escolar/GisBR) | Baixo | Reuso do algoritmo `read_schools` |
| 6. Saúde | **Alta** (resolvido por CNES/GisBR) | Baixo | Reuso de `read_health_facilities` e `read_health_region` |
