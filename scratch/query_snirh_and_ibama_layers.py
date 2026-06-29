import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def query_url(url):
    print(f"Querying: {url}")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")
        return None

def inspect_layer(url):
    data = query_url(f"{url}?f=json")
    if data:
        name = data.get('name', 'unknown')
        wkid = data.get('spatialReference', {}).get('latestWkid', data.get('spatialReference', {}).get('wkid', 'unknown'))
        fields = []
        raw_fields = data.get('fields')
        if raw_fields:
            for f in raw_fields:
                fields.append(f"{f.get('name')} ({f.get('type')})")
        print(f"\n--- Layer: {name} (WKID: {wkid}) ---")
        print("Fields:")
        for fd in fields:
            print(f"  {fd}")
        return {'name': name, 'wkid': wkid, 'fields': fields}
    return None

if __name__ == '__main__':
    # Inspect SNIRH Divisoes_bacias_hidrograficas layers
    print("\n=== SNIRH Divisoes_bacias_hidrograficas ===")
    div_data = query_url("https://www.snirh.gov.br/arcgis/rest/services/Divisoes_bacias_hidrograficas/MapServer?f=json")
    if div_data and 'layers' in div_data:
        for layer in div_data['layers']:
            print(f"Layer ID: {layer['id']}, Name: {layer['name']}")
        # Inspect layer 0 or 1 or 2
        inspect_layer("https://www.snirh.gov.br/arcgis/rest/services/Divisoes_bacias_hidrograficas/MapServer/0") # Bacias
        inspect_layer("https://www.snirh.gov.br/arcgis/rest/services/Divisoes_bacias_hidrograficas/MapServer/1") # Sub-bacias

    # Inspect SNIRH DADOSABERTOS
    print("\n=== SNIRH DADOSABERTOS ===")
    da_data = query_url("https://www.snirh.gov.br/arcgis/rest/services/DADOSABERTOS/MapServer?f=json")
    if da_data and 'layers' in da_data:
        for layer in da_data['layers']:
            print(f"Layer ID: {layer['id']}, Name: {layer['name']}")
        # Let's inspect some layer of interest (e.g. outorgas or captações if present, let's inspect layer 0)
        inspect_layer("https://www.snirh.gov.br/arcgis/rest/services/DADOSABERTOS/MapServer/0")

    # Inspect IBAMA Auto de Infração
    print("\n=== IBAMA Auto de Infração ===")
    inspect_layer("https://pamgia.ibama.gov.br/server/rest/services/app_dadosabertos/adm_auto_infracao_p/MapServer/0")

    # Inspect IBAMA Esgotamento
    print("\n=== IBAMA Esgotamento ===")
    inspect_layer("https://pamgia.ibama.gov.br/server/rest/services/SIGAGEO/Sistema_de_Esgotamento_Sanit%C3%A1rio/MapServer/0")

    # Inspect IBAMA Abastecimento
    print("\n=== IBAMA Abastecimento ===")
    inspect_layer("https://pamgia.ibama.gov.br/server/rest/services/SIGAGEO/Sistema_de_Abastecimento_de_%C3%81gua/MapServer/0")
