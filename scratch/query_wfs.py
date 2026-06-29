import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import ssl

# Desabilitar verificação de SSL se necessário (muitos geoservers do governo têm certificados inválidos)
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
            
            # Salvar XML cru
            filename = f"scratch/{type_name.replace(':', '_')}.xsd"
            with open(filename, 'wb') as f:
                f.write(content)
                
            # Parse XML
            root = ET.fromstring(content)
            
            # Namespaces
            ns = {
                'xsd': 'http://www.w3.org/2001/XMLSchema',
                'gml': 'http://www.opengis.net/gml/3.2'
            }
            
            fields = []
            # Procura por elementos no complexType
            for elem in root.findall('.//xsd:element', ns):
                name = elem.get('name')
                type_attr = elem.get('type')
                if name and name != 'the_geom' and name != 'geom' and name != 'ogc_fid':
                    fields.append(f"{name} ({type_attr.split(':')[-1] if type_attr else 'unknown'})")
            
            print(f"Success for {type_name}: {len(fields)} fields found.")
            return fields
    except Exception as e:
        print(f"Error querying {type_name}: {e}")
        return str(e)

def query_arcgis_schema(url):
    full_url = f"{url}?f=json"
    print(f"Querying ArcGIS REST: {full_url}")
    try:
        req = urllib.request.Request(full_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            content = response.read().decode('utf-8')
            data = json.loads(content)
            
            # Salvar JSON cru
            filename = f"scratch/arcgis_{url.split('/')[-3]}_{url.split('/')[-1]}.json"
            with open(filename, 'w') as f:
                f.write(json.dumps(data, indent=2))
                
            fields = []
            if 'fields' in data:
                for f in data['fields']:
                    fields.append(f"{f['name']} ({f['type']})")
            
            wkid = data.get('spatialReference', {}).get('latestWkid', data.get('spatialReference', {}).get('wkid', 'unknown'))
            
            print(f"Success for {url}: {len(fields)} fields found. WKID: {wkid}")
            return {
                'fields': fields,
                'wkid': wkid,
                'name': data.get('name', 'unknown')
            }
    except Exception as e:
        print(f"Error querying {url}: {e}")
        return str(e)

if __name__ == '__main__':
    import os
    os.makedirs('scratch', exist_ok=True)
    
    # 1. Testar SICAR MG WFS
    sicar_fields = query_wfs_schema("https://geoserver.car.gov.br/geoserver/sicar/wfs", "sicar:sicar_imoveis_mg")
    print("SICAR Fields:", sicar_fields)
    
    # 2. Testar DER-MG / IDE-Sisema WFS
    der_fields = query_wfs_schema("https://geoserver.meioambiente.mg.gov.br/IDE/wfs", "IDE:ide_0403_mg_rodovias_der_l")
    print("DER-MG Fields:", der_fields)
    
    # 3. Testar IDE-Sisema CAR Veg
    veg_fields = query_wfs_schema("https://geoserver.meioambiente.mg.gov.br/IDE/wfs", "IDE:ide_210604_mg_analise_car_veg_2025_ap_pol")
    print("Sisema Veg Fields:", veg_fields)
