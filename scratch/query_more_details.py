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

if __name__ == '__main__':
    print("\n--- MInfra Rodovias Federais ---")
    fields = query_wfs_schema("https://geoservicos.inde.gov.br/geoserver/ows", "MInfra:Rodovias Federais")
    print(fields)
    
    print("\n--- MPOG Rodovias ---")
    fields = query_wfs_schema("https://geoservicos.inde.gov.br/geoserver/ows", "MPOG:Rodovias")
    print(fields)
