# Rede, SSL e Certificados

O **GisBR** conecta-se a diversos serviços geográficos e repositórios oficiais na nuvem (IPEA, IBGE, ANA, IBAMA, Overpass/OSM, GeoServers federais e estaduais) para carregar malhas territoriais e camadas temáticas de diagnóstico municipal. Esta página documenta como o plugin executa requisições de rede, lida com a cadeia de certificados SSL/TLS, gerencia *mirrors* e cache local, e lida com eventuais falhas de conexão.

---

## 1. Princípios de infraestrutura de rede

- **Pilha nativa do QGIS (`QgsBlockingNetworkRequest` / `QNetworkRequest`)**: Todas as requisições HTTP/HTTPS utilizam a infraestrutura de rede nativa do Qt e do PyQGIS. O plugin não instala nem utiliza bibliotecas externas como `requests` ou `urllib3`.
- **Respeito às configurações do QGIS e do sistema**: Por reutilizar a pilha de rede do QGIS, o plugin herda automaticamente as opções globais definidas em **Configurações › Opções › Rede**, incluindo:
  - Proxies corporativos (HTTP, SOCKS5);
  - Configurações de timeout e reutilização de conexões (*Keep-Alive*);
  - Identificação via cabeçalho *User-Agent* customizado (ex.: `geobr-qgis/0.1`).
- **Verificação estrita de SSL (sem atalhos inseguros)**: O GisBR **nunca** desativa a verificação de certificados SSL (não altera `PeerVerifyMode` para ignorar erros nem aceita certificados inválidos). Problemas de SSL em plataformas como o Windows são corrigidos exclusivamente fornecendo as Autoridades Certificadoras (CAs) confiáveis necessárias.

---

## 2. Injeção de certificados SSL/TLS no Windows

### O problema do SSL no Windows (OSGeo4W)

No Windows (especialmente em ambientes QGIS instalados via OSGeo4W), requisições HTTPS para determinados servidores governamentais — em especial o servidor do IPEA (`www.ipea.gov.br`) — costumam falhar com o erro:

> `SSL handshake failed: Unable to find issuer certificate` (Impossível localizar o emissor do certificado)

### Causa raiz

A cadeia de certificados entregue pelo servidor do IPEA é composta por:

1. **Certificado Folha**: `*.ipea.gov.br`
2. **Intermediário 1**: `Sectigo Public Server Authentication CA DV R36`
3. **Intermediário 2 / Root Cruzado**: `Sectigo Public Server Authentication Root R46`
4. **CA Raiz**: `USERTrust RSA Certification Authority`

Embora o servidor envie os certificados intermediários, o *store* de CAs empacotado na instalação do Qt/OSGeo4W nem sempre possui a CA intermediária ou a CA raiz no repositório de confiança padrão.

### Solução implementada no GisBR (`gisbr/core/ssl_support.py`)

Em vez de desabilitar a checagem de SSL, o GisBR resolve o problema de forma segura através da **injeção aditiva de CAs**:

1. **Certificados empacotados**: Os certificados das CAs necessárias são armazenados em arquivos `.pem` na pasta `gisbr/core/certs/`.
2. **Carregamento aditivo (`configure_request`)**: O módulo `gisbr/core/ssl_support.py` varre a pasta de certificados e injeta as CAs na requisição (`QNetworkRequest`), preservando as CAs do sistema operacional (`QSslConfiguration.systemCaCertificates()`).
3. **Configuração global (`install_default_ca_certificates`)**: Registra as CAs na configuração SSL padrão do processo (`QSslConfiguration.setDefaultConfiguration`), permitindo que requisições sem `QNetworkRequest` explícita (como as camadas de Basemap XYZ do Esri World Imagery) também funcionem perfeitamente.

---

## 3. Cadeia de mirrors e cache local

### Downloads de dados (geobr e censobr)

Para garantir alta disponibilidade e resiliência contra indisponibilidades temporárias no IPEA, o GisBR implementa uma **cadeia de mirrors com fallback automático**:

- **Dados v1 (GeoPackage)**:
  1. **Primário**: `http://www.ipea.gov.br/geobr/...`
  2. **Mirror**: `https://github.com/ipeaGIT/geobr/releases/download/v1.7.0/...`
- **Dados v2 (GeoParquet)** e **censobr**:
  1. **Primário**: Release oficial no GitHub (`ipeaGIT/geobr_prep_data` ou `ipeaGIT/censobr`).
  2. **Fallback**: Servidor alternativo do IPEA (`IPEA_V2_FALLBACK_BASE`).

Caso o servidor primário retorne erro de rede ou código HTTP $\ge 400$, o download tenta o próximo mirror de forma transparente para o usuário.

### Cache local em disco

- Todo arquivo baixado pelo geobr ou censobr é armazenado na pasta de cache do sistema:
  - **Linux/macOS**: `~/.cache/geobr-qgis/`
  - **Windows**: `%LOCALAPPDATA%\geobr-qgis\` (ou caminho resolvido por `QStandardPaths.CacheLocation`)
- Execuções subsequentes para a mesma geografia, ano e nível de simplificação **não realizam requisições de rede**, lendo o arquivo salvo em disco.

---

## 4. Comportamento de rede por conector

Cada protocolo utilizado pelo GisBR no Diagnóstico Municipal gerencia sua própria comunicação de rede:

| Protocolo | Mecanismo | Comportamento e Resiliência |
|---|---|---|
| **WFS** | `QgsBlockingNetworkRequest` | Consulta feições GeoJSON com suporte a `CQL_FILTER` por município/estado ou BBOX. Caso a requisição falhe, pode tentar fallback via VSI (`/vsicurl/`). |
| **ArcGIS REST** | `QgsBlockingNetworkRequest` | Executa requisições à operação `/query?f=geojson` em Geosserviços ArcGIS Server (ex.: ANA, IBAMA). |
| **OSM / Overpass** | Requisição HTTP POST | Envia consultas em Overpass QL para a API Overpass (`overpass-api.de`). Erros de rede ou respostas HTTP 429 (*Rate Limit*) são tratados com exceções tipadas (`OverpassError`). |
| **Basemap XYZ** | Camada Raster QGIS (`wms`) | Carrega blocos de imagem de satélite (Esri World Imagery) usando as CAs ativadas via `install_default_ca_certificates()`. |
| **Arquivo local (`arquivo`)** | Leitura local de arquivo | Usado para bases que exigem login (ex.: parcelas do SIGEF/INCRA via `gov.br`). **Não realiza tráfego de rede**, não solicita e nunca armazena credenciais. |

---

## 5. Solução de problemas

Em caso de falhas de download ou se uma fonte aparecer como `FALHOU` no painel de diagnósticos:

1. **Examine o painel de log do QGIS**: As mensagens exibem a URL tentada, o host e o erro SSL ou HTTP reportado.
2. **Verifique as CAs locais**: Certifique-se de que os arquivos `.pem` em `gisbr/core/certs/` estão presentes no plugin.
3. **Ambiente corporativo / Proxy MITM**: Antivírus ou firewalls corporativos que fazem inspeção de tráfego HTTPS (Man-In-The-Middle) substituem os certificados do servidor. Solicite ao administrador da rede a liberação dos seguintes domínios:
   - `www.ipea.gov.br`
   - `github.com` / `raw.githubusercontent.com`
   - `overpass-api.de`
   - `services.arcgisonline.com`
4. **Instabilidade em servidores públicos**: Geosserviços de órgãos governamentais podem sofrer quedas temporárias. Quando isso ocorrer, desmarque a fonte afetada no painel para concluir a carga das demais; dados já salvos no GeoPackage não serão perdidos.
