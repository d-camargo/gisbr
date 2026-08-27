# GisBR

**GisBR** brings official Brazilian spatial data into QGIS: it is both a
**geobr/censobr mirror** (IPEA), offering "1 line → 1 layer" access to IBGE
datasets as Processing algorithms, and a **municipal diagnostic panel** that,
given a municipality, loads the official layers a city needs in order to draft or
review its *Plano Diretor* (Master Plan), organized in 8 thematic axes.

The guiding principle is non-negotiable: **only PyQGIS and the Python stdlib**.
There is no `pip install` to use the plugin — the single exception is optional
(`pyarrow` or the GDAL Parquet driver) and only concerns the v2 algorithms and
`join_censo`. All data is delivered in **SIRGAS 2000 / EPSG:4674**.

<div class="grid cards" markdown>

-   **[Installation](instalacao.md)**

    ---

    Install from the official QGIS plugin repository or by symlink for
    development, plus the requirements (QGIS 3.16+, Qt5 or Qt6).

-   **[Master Plan Diagnostic](guias/diagnostico.md)**

    ---

    The panel end to end: state → municipality, sources by axis, output
    GeoPackage, and what to expect from the clip to the municipality polygon.

-   **[geobr/censobr mirror](guias/geobr.md)**

    ---

    The `read_*` algorithms in the console and in the Processing Toolbox, the
    common parameters (`YEAR`, `CODE`, `SIMPLIFIED`) and `join_censo`.

-   **[Data sources](referencia/fontes.md)**

    ---

    The full diagnostic source catalog, grouped by axis, with protocol, filter
    type and license — generated from the plugin's own code.

</div>

GisBR is free software under **GPL-3.0**. The code lives at
[github.com/d-camargo/gisbr](https://github.com/d-camargo/gisbr).
