# GisBR

O **GisBR** traz dados espaciais oficiais do Brasil para dentro do QGIS: ele é ao
mesmo tempo um **espelho do geobr/censobr** (IPEA), com acesso "1 linha → 1 camada"
aos dados do IBGE como algoritmos de Processamento, e um **painel de diagnóstico
municipal** que, dado um município, sobe as camadas oficiais necessárias para
elaborar ou revisar o Plano Diretor, organizadas em 8 eixos temáticos.

O princípio é inegociável: **apenas PyQGIS e a stdlib do Python**. Não há
`pip install` para usar o plugin — a única exceção é opcional (`pyarrow` ou o
driver GDAL Parquet), e serve só aos algoritmos v2 e ao `join_censo`. Todos os
dados saem em **SIRGAS 2000 / EPSG:4674**.

<div class="grid cards" markdown>

-   **[Instalação](instalacao.md)**

    ---

    Instalar pelo repositório oficial do QGIS ou por symlink para
    desenvolvimento, e o que é requisito (QGIS 3.16+, Qt5 ou Qt6).

-   **[Diagnóstico de Plano Diretor](guias/diagnostico.md)**

    ---

    O painel de ponta a ponta: UF → município, fontes por eixo, GeoPackage de
    saída, e o que esperar do recorte pelo polígono do município.

-   **[Espelho geobr/censobr](guias/geobr.md)**

    ---

    Os algoritmos `read_*` no console e na Caixa de Ferramentas, os parâmetros
    comuns (`YEAR`, `CODE`, `SIMPLIFIED`) e o `join_censo` com o censobr.

-   **[Fontes de dados](referencia/fontes.md)**

    ---

    O catálogo completo de fontes do diagnóstico, agrupado por eixo, com
    protocolo, tipo de filtro e licença — gerado do código do plugin.

</div>

O GisBR é software livre sob **GPL-3.0**. O código vive em
[github.com/d-camargo/gisbr](https://github.com/d-camargo/gisbr).
