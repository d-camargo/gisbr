import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def query_wfs_schema(url, type_name):
    params = {
        'service': 'WFS',
        'version': '2.0.0',
        'request': 'DescribeFeatureType',
        'typeName': type_name
    }
    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"
    print(f"Querying WFS: {full_url}")
    try:
        req = urllib.request.Request(full_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            content = response.read()
            # Parse XML
            root = ET.fromstring(content)
            ns = {
                'xsd': 'http://www.w3.org/2001/XMLSchema',
                'gml': 'http://www.opengis.net/gml/3.2'
            }
            fields = []
            for elem in root.findall('.//xsd:element', ns):
                name = elem.get('name')
                type_attr = elem.get('type')
                if name and name not in ['the_geom', 'geom', 'ogc_fid', 'gid', 'geom_original', 'geometry']:
                    fields.append(f"{name} ({type_attr.split(':')[-1] if type_attr else 'unknown'})")
            print(f"Success for {type_name}: {len(fields)} fields found.")
            return fields
    except Exception as e:
        print(f"Error querying {type_name}: {e}")
        return str(e)

def query_arcgis_catalog(url):
    full_url = f"{url}?f=json"
    print(f"Querying ArcGIS Catalog: {full_url}")
    try:
        req = urllib.request.Request(full_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            content = response.read().decode('utf-8')
            data = json.loads(content)
            services = data.get('services', [])
            folders = data.get('folders', [])
            print(f"ArcGIS Services: {len(services)}, Folders: {len(folders)}")
            # Salvar catálogo em scratch
            with open("scratch/arcgis_catalog.json", "w") as f:
                f.write(json.dumps(data, indent=2))
            return data
    except Exception as e:
        print(f"Error cataloging {url}: {e}")
        return str(e)

def query_arcgis_layer(url):
    full_url = f"{url}?f=json"
    print(f"Querying ArcGIS Layer: {full_url}")
    try:
        req = urllib.request.Request(full_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            content = response.read().decode('utf-8')
            data = json.loads(content)
            fields = []
            if 'fields' in data:
                for f in data['fields']:
                    fields.append(f"{f['name']} ({f['type']})")
            wkid = data.get('spatialReference', {}).get('latestWkid', data.get('spatialReference', {}).get('wkid', 'unknown'))
            print(f"Success for layer: {data.get('name', 'unknown')} | WKID: {wkid}")
            # print fields
            return {
                'name': data.get('name', 'unknown'),
                'fields': fields,
                'wkid': wkid
            }
    except Exception as e:
        print(f"Error querying layer {url}: {e}")
        return str(e)

if __name__ == '__main__':
    # 1. Query WFS schemas
    print("\n--- SISEMA Rodovias ---")
    r = query_wfs_schema("https://geoserver.meioambiente.mg.gov.br/IDE/wfs", "IDE:ide_0401_mg_rodovias_lin")
    print(r)
    
    print("\n--- SISEMA Ferrovias ---")
    r = query_wfs_schema("https://geoserver.meioambiente.mg.gov.br/IDE/wfs", "IDE:ide_0402_mg_ferrovias_lin")
    print(r)
    
    print("\n--- CPRM Rios ---")
    r = query_wfs_schema("https://opendata.sgb.gov.br/geoserver/ows", "p3m:vw_ibge_rios")
    print(r)

    print("\n--- CPRM Bacia Nivel 6 ---")
    r = query_wfs_schema("https://opendata.sgb.gov.br/geoserver/ows", "p3m:vw_ibge_bacia_hidro_6")
    print(r)

    # 2. Query ArcGIS catalog
    print("\n--- ANA ArcGIS catalog ---")
    query_arcgis_catalog("https://intranet.snirh.gov.br/arcgis/rest/services")

    print("\n--- IBAMA ArcGIS catalog ---")
    query_arcgis_catalog("https://pamgia.ibama.gov.br/server/rest/services")
