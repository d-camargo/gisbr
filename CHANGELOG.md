# Changelog

Generated from the `changelog` block of `gisbr/metadata.txt` by `tools/build_docs_site.py` — do not edit by hand.

## 1.0.0

- New extent selector: choose between single Municipality or
Metropolitan Region (RM) mode in the diagnostic panel.
- Embedded official IBGE metropolitan composition data (extracted on
2026-09-20) covering the 84 state-instituted metropolitan regions
in Brazil (RIDEs are not part of this catalog).
- Added boundary layer rm_<id> containing individual municipality
polygons for the selected metropolitan region.
- Note: OSM network and POI sources remain scoped to the target municipality
in RM mode to keep query performance fast and light.

## 0.12.0

- The OSM road network verification and layers are now built for ONE
network per run, vehicle by default, instead of running vehicle and
pedestrian every time; this also halves the cost of the geometric
verification step.
- Dead ends (ponta_solta) are no longer listed in osm_problemas by
default, since a dead end is normal, not an error; the count of
skipped dead ends is reported in the log instead of being silently
dropped.
- One-way traps (mao_unica_sem_saida/mao_unica_borda) now produce one
point per trap (group of nodes), not one per node.
- New REDE (vehicle/pedestrian) and PONTAS_SOLTAS parameters on the
gisbr:osm_network Processing algorithm.
- Removed the componente_pe/grau_pe fields from osm_links/osm_nodes;
componente/grau are now generic, for whichever network ran.

## 0.11.0

- The OSM road network is now built from the real OSM topology: ways are
split into arcs at shared node_ids, so junctions in the middle of a
way are no longer lost; the osm_links/osm_nodes schema changed
accordingly (arc_id, from_node/to_node, component, degree).
- New osm_problemas_<code> layer with a connectivity check: types ilha,
ilha_borda, ponta_quase_conectada, ponta_solta, mao_unica_sem_saida,
mao_unica_borda and cruzamento_sem_no, each with a severity and the
network it belongs to.
- The vehicle network is now separated from the pedestrian network, and
highway types that are not real links (construction, platform,
busway, area=yes, etc.) are discarded.
- New link attributes for transport modelling: maxspeed,
velocidade_kmh, comprimento_m.
- New gisbr:osm_network Processing algorithm (LINKS/NODES/PROBLEMAS
outputs), so other plugins can consume the road network via
processing.run().
- The road network now loads in a background QgsTask: progress bar,
working Cancel button, QGIS no longer freezes during the download.
- Municipal clipping now keeps whole arcs that cross the boundary
(instead of native:clip), to preserve from_node/to_node.

## 0.10.0

- New 9th diagnostic axis (Agriculture & Livestock) featuring IBGE Agregados v3 data (PAM temporary and permanent crops, and Census of Agriculture 2017).
- MapBiomas Brasil Collection 9 land cover and land use raster integration via Cloud Optimized GeoTIFF (COG).
- ANM/SIGMINE mining claims broken down by process phase via remote ZIP extraction.

## 0.9.2

- The plugin is now called GISBR everywhere in the interface: the
toolbar button tooltip and the Plugins menu entry show GISBR instead of the
full diagnostic name, the dock panel title is just GISBR, and the Processing
provider is listed as GISBR.

## 0.9.1

- The toolbar button now shows the GisBR icon with a short GisBR label
instead of the full algorithm name; the complete name is kept in the
Plugins menu and in the button tooltip.

## 0.9.0

- Diagnostic panel reorganised into five tabs (Location, Sources, Census,
Output, Log); the Load button now sits below the tabs and is always
visible, the panel switches to the Log tab when a load starts, and the
Census tab is only enabled when the census tracts source is selected.
Panel labels translated to Brazilian Portuguese.

## 0.8.0

- New option in the diagnostic panel: attach censobr Census tables to the
census tracts layer, so the GeoPackage layer already carries the Census
variables. The tract geometry year follows the selected Census year
(2000, 2010, 2022); the censobr table is filtered by municipality before
the layer is built; the join core is now shared with the `join_censo`
algorithm.

## 0.7.2

- Fix: POI loading issue where QgsGeos.contains received a QgsPointXY.

## 0.7.1

- Fixes for Overpass data sources (osm_roads and osm_pois): transport timeout
enforcement, HTTP and server error response detection, fallback mirror
rotation, and strict validation of cached response payload.

## 0.7.0

- New OpenStreetMap POI engine (source `osm_pois`, Urban axis): downloads
buildings, amenities and station-like POIs for the selected municipality
via Overpass, using the same POI predicate as osm2gmns, and writes two
GeoPackage layers (`osm_pois_<code>`, points, and `osm_pois_area_<code>`,
footprints) with area in m2/ft2 and centroid-based municipal clipping.
- New `gisbr:export_poi_gmns` Processing algorithm exporting the POI layer
as a poi.csv in the exact osm2gmns/grid2demand column layout.

## 0.6.0

- New local-file protocol for official datasets that sit behind a personal
gov.br login: instead of a network endpoint, the source reads a file the
user downloaded manually, resolves it by pattern from the manual
downloads folder, and follows the standard pipeline (clip to the
municipality polygon, GeoPackage, skip-if-exists). Missing file skips
with guidance instead of failing.
- Added the INCRA/SIGEF certified parcels source (administrative axis) —
the INCRA export service requires a gov.br login, so it uses the new
protocol; the plugin never asks for or stores credentials.
- New "Manual downloads folder" selector in the diagnostic panel.

## 0.5.0

- New data sources in the Master Plan diagnostic panel, all public federal
services: geological risk sectors (SGB/CPRM), mining claims (ANM/SIGMINE),
groundwater wells (SIAGAS), IBGE BC250 2025 layers (roads, railways,
drainage, water bodies, densely built-up areas), IBGE urbanised areas
(2019) and subnormal agglomerations (2010), and the IBGE BDIA physical
environment set (soil, geology, geomorphology, vegetation).
- Truncated downloads are no longer silent: when a service returns fewer
features than matched the filter (WFS numberMatched) or stops at its
record limit (ArcGIS maxRecordCount), the log shows a warning and the
layer keeps a "truncado" custom property.
- Server errors returned with HTTP 200 (ArcGIS error bodies and OGC
ExceptionReport documents) are now reported with the code and message
sent by the server, instead of a generic failure to open the layer.

## 0.4.3

- Fix: two error handlers discarded their exception silently. Failing to
remove the cached metadata file when refreshing the catalog, and failing
to read the local Overpass cache while falling back to it, are now
reported with the underlying cause instead of being swallowed.
- No functional change: the 0.4.2 SSL fix is unchanged and ships here.

## 0.4.2

- Fix (SSL on freshly installed Windows/OSGeo4W): downloads failed with
"unable to find issuer certificate" because the bundled CA material only
covered the IPEA server and was only injected in the geobr downloader.
The plugin now ships the self-signed roots used by the GitHub mirror,
SICAR, ANA/SNIRH, INDE, SGB, IBAMA, Overpass and the satellite basemap.
- The certificate injection moved to a single module (core/ssl_support.py)
and is now applied to the WFS, ArcGIS REST and Overpass connectors, plus
the default SSL configuration used by the XYZ basemap.
- Certificates are only added as trust anchors; no verification setting is
ever relaxed.
- Network failures now report the host and the underlying error instead of
a generic message.

## 0.4.1

- Fix (QGIS 4.x / Qt6): the cache directory lookup used the unscoped
QStandardPaths.CacheLocation enum, which raises on PyQt6 and made the
municipality list fail with "geobr catalog unavailable". The enum is now
scoped, and the same fix was applied to the Overpass network error check.
- The catalog error message now appends the real underlying exception
instead of only showing the generic connection hint.
- The metadata cache path is resolved defensively, so a cache failure falls
back to the bundled offline CSV instead of aborting.
- Declares supportsQt6 so Qt6 builds of QGIS offer the plugin.

## 0.4.0

- Added explicit QGIS 4.x compatibility

## 0.3.2

- New: municipal OSM road network via Overpass — links + nodes topology,
persisted to the municipality GeoPackage, with the same skip-if-exists
behavior as the WFS/ArcGIS sources.
- Robust error handling for Overpass fetches (network errors, invalid
JSON responses, per-source timeout honored).
- Fix: SSL certificate failure when loading IPEA metadata on Windows,
with a safe fallback.
- First non-experimental release.

## 0.3.1

- Packaging: exclude the scratch/ research scripts from the published zip
(they used urllib/ssl/xml and were flagged by the repository security scan).
No change to plugin behavior.

## 0.3.0

- Master Plan diagnostic: dock panel (state -> municipality) that loads
official layers by axis into a local GeoPackage.
- New connectors: WFS (CQL_FILTER) and ArcGIS REST (where=), plus an Esri
World Imagery satellite basemap.
- 29-source declarative catalog across 8 axes; server-side filter by
municipality with client-side clip to the municipality polygon.

## 0.2.0

- Phase 2: Parquet backend (geobr v2.0.0) with 28 read_*_v2 algorithms.
- censobr integration: join_censo joins geobr census tracts with census tables.
- Parquet read via the GDAL driver or a pyarrow fallback (driver-independent).
- 55 algorithms total (26 v1 + 28 v2 + join_censo).

## 0.1.0

- Initial release (Phase 1): Processing provider with the legacy GPKG v1.7.0 backend.
- read_country, read_region, read_state, read_municipality, read_census_tract,
read_weighting_area, read_metro_area, read_biomes and more.
- On-disk cache and mirror fallback (IPEA -> GitHub).
- Fully PyQGIS + stdlib, no external dependencies.
