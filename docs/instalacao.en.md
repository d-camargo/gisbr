# Installation

## From the official QGIS plugin repository

This is the normal path. In QGIS:

1. *Plugins → Manage and Install Plugins…*
2. **All** tab, search for **GisBR**.
3. Click **Install Plugin**.

The plugin then shows up in two places: the **GisBR** menu/toolbar, which opens
the [Master Plan diagnostic panel](guias/diagnostico.md), and the **Processing
Toolbox**, under the *GisBR* provider, with the
[`read_*` geobr mirror algorithms](guias/geobr.md).

## Development install (symlink)

To work on the code, deploy by symlink instead of copying files — that way what
is in the repository is what QGIS loads:

```bash
cd ~/Documents/GIS/gisbr/   # or wherever the repository lives
make deploy        # symlinks to profiles/default/python/plugins/gisbr
make test          # syntax check only (ast.parse, no QGIS)
```

Reload with the **Plugin Reloader** or restart QGIS, then enable the plugin in
*Plugins → Manage and Install Plugins…*.

!!! warning "`make test` is not the compatibility gate"
    `make test` only runs `ast.parse` and catches syntax errors. The actual
    compatibility check is the **smoke test that imports every plugin module
    under both Qt5 (QGIS 3.x) and Qt6 (QGIS 4.x)**.

## Requirements

- **QGIS 3.16 or newer**, including **QGIS 4.x (Qt6)** — the plugin declares
  `supportsQt6=True` and is tested against both Qt5 and Qt6 builds.
- **An internet connection** for the first download of each dataset; later uses
  are served from the local cache.
- **No `pip install`**: the plugin uses only PyQGIS and the Python stdlib that
  already ship with QGIS.

### Optional: Parquet (v2 algorithms and `join_censo`)

GisBR **works without it**. All of Phase 1 (the 26 GeoPackage-based `read_*`
algorithms) and the diagnostic panel do not depend on Parquet.

Parquet support is only needed for the `read_*_v2` algorithms (the geobr v2.0.0
backend), for the v2-only diagnostic sources and for `join_censo` (the censobr
join). Either option is enough:

- **`pyarrow`** — recommended on Linux (QGIS from apt or Flatpak), since it
  reuses the QGIS you already have:

    ```bash
    pip install --user pyarrow
    ```

- **The GDAL `Parquet`/`Arrow` driver** — official Windows and macOS builds
  usually ship it already. To check:

    ```bash
    ogrinfo --formats | grep -i parquet
    ```

    If it is missing, conda-forge is the reliable path, with a version matching
    the GDAL used by QGIS:

    ```bash
    conda install -c conda-forge libgdal-arrow-parquet
    ```

!!! note "Pop!_OS / Ubuntu / Flatpak"
    These builds do **not** ship the GDAL Parquet driver (measured on GDAL 3.8.4
    from apt and 3.13 from Flatpak), and the apt `gdal-plugins` package does not
    install it either. Use `pyarrow`.

With neither of them, the v2 algorithms tell you which option to install and
Phase 1 keeps working normally.
