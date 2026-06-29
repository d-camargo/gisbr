# Referência — imagem de satélite de fundo (precedente do haCARthon)

O Diego já implementou "imagem de satélite como fundo" no **bot Terra em Dia**
(haCARthon raiz). Aqui registramos o que existe, para reaproveitar no GisBR.

> ⚠️ Contexto diferente: no bot é **geração de imagem estática** (matplotlib +
> download REST). No **QGIS** o fundo de satélite é um **XYZ tile layer** — bem
> mais simples (ver §3). Mas a **fonte** (Esri World Imagery) e as lições de
> alinhamento valem.

## 1. O que existe no bot (`src/terra-em-dia-bot/mapa.py`)

Origem: `~/Drive/02_Projetos_Tecnicos/haCARthon/src/terra-em-dia-bot/mapa.py` (677 linhas).

Funções principais:
- `gerar_mapa(imovel: dict, saida: str | Path, modo: str = "atual") -> Path`
- `gerar_comparativo(imovel: dict, saida: str | Path, feicao: str = "app") -> Path | None`

Ambas baixam o fundo de satélite e desenham os vetores por cima (matplotlib
`ax.imshow` + feições do SICAR).

## 2. Fonte e endpoint (Esri World Imagery — ArcGIS REST `export`)

```
https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export
  ?bbox=<xmin,ymin,xmax,ymax>
  &bboxSR=<epsg>          # o bot usa o EPSG UTM métrico do imóvel
  &imageSR=<epsg>
  &size=<W,H>
  &format=jpg
  &f=json                 # devolve { href, extent }
```

Lições de alinhamento já resolvidas no bot (relevantes se algum dia usarmos o
`export` em vez de XYZ):
- **Preservar o aspect** do bbox no `size` (W/H == dx/dy); **não** multiplicar por
  `cos(lat)`.
- Pedir `f=json`, ler o **`extent` real devolvido** pelo Esri e usar **esse**
  extent no `imshow` — torna o alinhamento robusto para imóveis de qualquer
  proporção (resolveu o problema do `clamp` de tamanho mínimo).
- Trabalhar em **UTM métrico** (`bboxSR`/`imageSR` = EPSG UTM) evita distorção.
- Sempre ter **fallback offline** (fundo branco) quando o serviço falha.

## 3. Como fazer no QGIS (recomendado para o GisBR)

No QGIS **não** baixamos imagem por `export`; adicionamos uma **camada XYZ** de
tiles do Esri World Imagery, que o próprio QGIS recorta/zooma:

```python
url = ("type=xyz&zmax=19&zmin=0&url="
       "https://server.arcgisonline.com/ArcGIS/rest/services/"
       "World_Imagery/MapServer/tile/%7Bz%7D/%7By%7D/%7Bx%7D")
layer = QgsRasterLayer(url, "Esri World Imagery", "wms")  # provider "wms" cobre xyz
QgsProject.instance().addMapLayer(layer)
```

- Provider é `"wms"` (o QGIS trata XYZ por baixo dele).
- `%7Bz%7D/%7By%7D/%7Bx%7D` = `{z}/{y}/{x}` URL-encodado.
- CRS de exibição: Web Mercator (EPSG:3857); o QGIS reprojeta na hora sobre os
  vetores em 4674.
- Atribuição: "Esri, Maxar, Earthstar Geographics" (Esri World Imagery é de uso
  permitido como basemap; registrar a fonte na camada via `data_extracao`/`fonte`).

> No GisBR isso vira um conector `core/connectors/basemap.py` + um algoritmo
> simples "Adicionar imagem de satélite (fundo)" — sem parâmetro de município
> (é fundo global; o usuário dá zoom no município).
