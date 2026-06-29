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

# Listar serviços sob folders comuns
folders = ["01_Publicacoes", "app_dadosabertos", "SIGAGEO"]
for folder in folders:
    url = f"https://pamgia.ibama.gov.br/server/rest/services/{folder}?f=json"
    data = query_url(url)
    if data and 'services' in data:
        print(f"\n--- Services in {folder} ---")
        for s in data['services']:
            print(f" - Name: {s['name']}, Type: {s['type']}")
            
# Vamos listar as camadas do serviço "app_dadosabertos" se ele for um serviço direto na raiz
# Mas espera, "app_dadosabertos" é uma pasta. Vamos ver se tem serviços nela.
# Vamos rodar esse script e ver o output.
