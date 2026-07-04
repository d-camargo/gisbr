# PLAN — gisbr (fix SSL no download do metadado IPEA, Windows)

## Objetivo

Corrigir o erro **"Impossível Localizar o Emissor do Certificado"** que ocorre no
QGIS para Windows ao baixar `metadata_1.7.0_gpkg.csv` do IPEA
(`core/catalog.py` → `download_metadata()` → `downloader.fetch_bytes(METADATA_URL)`),
sem enfraquecer a verificação SSL (`verify=False` está proibido pelo CLAUDE.md §10),
e sem deixar o plugin travado quando o IPEA estiver com a cadeia de certificado
incompleta ou inacessível.

## Decisões de arquitetura

- **Não desabilitar verificação de certificado.** Nada de
  `QSslConfiguration.setPeerVerifyMode(QSslSocket.VerifyNone)` ou equivalente.
  Se a causa raiz exigir isso para "funcionar", a solução certa é outra (mirror,
  cert adicional, ou fallback vendorizado) — não abrir mão de segurança.
- **Gap identificado no código atual:** `fetch()` (dados `.gpkg`) já tem cadeia
  de mirrors (IPEA → GitHub, via `_mirror_urls`/`_fetch_to_cache`), mas
  `fetch_bytes(METADATA_URL)` (usado só para o CSV de metadados) **não tem
  nenhum fallback** — uma falha de SSL nesse único ponto derruba o plugin
  inteiro antes de qualquer `read_*` funcionar. Esse é o alvo principal do fix.
- **Diagnóstico antes de remediar.** "Unable to find issuer certificate" tem 3
  causas plausíveis e cada uma pede um fix diferente:
  1. Servidor do IPEA manda a cadeia incompleta (falta intermediário) — comum
     em `.gov.br`. Fix: o plugin injeta o(s) certificado(s) intermediário(s)
     faltante(s) na requisição (`QSslConfiguration`, **somando** à cadeia
     confiável, nunca desligando validação).
  2. Store de CA do QGIS/Windows (build OSGeo4W) desatualizado/incompleto.
     Fix: mesmo caminho do item 1 (plugin fornece o intermediário), já que não
     dá para pedir ao usuário para mexer no store do sistema.
  3. Proxy corporativo/antivírus fazendo inspeção TLS (MITM) — bastante comum
     em máquina Windows corporativa. **Não dá para "consertar" isso com
     certificado embutido** (a CA do MITM não é conhecida a priori). Fix:
     fallback para mirror/CSV vendorizado + mensagem de erro explicando a
     causa provável, sem tentar contornar a validação.
- **Fallback em camadas, sempre com feedback explícito de qual fonte foi
  usada** (cache disco → IPEA → mirror GitHub → CSV vendorizado no pacote),
  espelhando o padrão que `fetch()` já usa para dados, estendido ao metadado.
- **CSV vendorizado é o último recurso, não o primeiro.** Ele garante que o
  plugin nunca fica 100% bloqueado, mas pode ficar desatualizado — sempre usar
  com aviso (`feedback.pushWarning`) e só depois de IPEA e mirror falharem.

## Passos (executor marca [x] ao concluir)

- [x] 1. Diagnosticar a cadeia de certificado real do IPEA: rodar
      `openssl s_client -connect www.ipea.gov.br:443 -servername www.ipea.gov.br -showcerts`
      (Linux/Pop!_OS, ambiente atual do Diego) e registrar se o servidor entrega
      a cadeia completa ou se falta intermediário. Anotar o resultado em
      `docs/ssl-ipea-windows.md` (novo arquivo).
- [x] 2. Coletar do usuário que reportou o erro (ou reproduzir, se possível)
      informação mínima de ambiente Windows: versão do QGIS/OSGeo4W, se a
      máquina é corporativa com antivírus/proxy com inspeção TLS ativa. Registrar
      em `docs/ssl-ipea-windows.md` — isso decide entre o caminho 1/2 (cert
      faltante) e o caminho 3 (MITM, sem fix de certificado possível).
- [x] 3. Se o diagnóstico (passo 1) confirmar cadeia incompleta do lado do
      servidor: extrair o certificado intermediário faltante (via `openssl`
      ou exportação do navegador) e salvar em `core/certs/ipea_chain.pem`.
      — arquivos: `core/certs/ipea_chain.pem` (novo).
- [x] 4. Implementar `core/downloader.py::_configure_ssl_config(request)`:
      carrega `core/certs/ipea_chain.pem` (se existir) e injeta via
      `QSslConfiguration.addCaCertificates`/`setCaCertificates` na
      `QNetworkRequest` antes do `blocking.get(...)`, sem alterar
      `PeerVerifyMode`. Aplicar em `_http_get`. — arquivos: `core/downloader.py`.
- [x] 5. Estender a cadeia de fallback do metadado: trocar
      `fetch_bytes(METADATA_URL)` em `core/catalog.py::download_metadata()` por
      uma chamada que tenta IPEA → mirror GitHub (reaproveitar
      `_mirror_urls`/`_fetch_to_cache`, adicionando o CSV como asset conhecido
      no mirror, se existir; senão só documentar a ausência). — arquivos:
      `core/downloader.py`, `core/catalog.py`, `core/constants.py` (se precisar
      de nova constante de URL de mirror do CSV).
- [x] 6. Vendorizar uma cópia de segurança do metadado como último recurso:
      salvar o CSV atual em `core/data/metadata_1.7.0_gpkg.csv` (empacotado no
      plugin) e, em `download_metadata()`, usá-lo só se IPEA e mirror falharem,
      emitindo aviso claro de que os dados podem estar desatualizados.
      — arquivos: `core/data/metadata_1.7.0_gpkg.csv` (novo), `core/catalog.py`.
- [x] 7. Mensagem de erro amigável no `DownloadError` final (quando todas as
      fontes falham): explicar as causas prováveis em português — certificado
      intermediário ausente vs. antivírus/proxy corporativo interceptando
      HTTPS — e não travar silenciosamente. — arquivos: `core/downloader.py`.
- [x] 8. Atualizar `build-qgis-zip` / checagem de empacotamento para confirmar
      que `core/certs/` e `core/data/` (novos) **entram** no zip publicado
      (diferente de `scratch/`, que é excluído de propósito — CLAUDE.md §10).
      — arquivos: `.claude/skills/build-qgis-zip/` (conferir, sem regressão).
- [x] 9. Validar no Windows (máquina/usuário que reportou o bug):
      `download_metadata()` completa sem erro de certificado, e confirmar que
      nenhuma verificação SSL foi desabilitada (checklist de segurança manual:
      grep por `VerifyNone`/`verify=False` não deve retornar nada em
      `core/`).
- [x] 10. Documentar a descoberta e a solução em `CLAUDE.md` §10 (novo
      pitfall, no mesmo estilo dos já registrados: scan de segurança, `%` no
      metadata.txt, i18n).

## Critério de aceite

- No QGIS para Windows (ambiente onde o erro foi reportado),
  `core.catalog.download_metadata()` completa com sucesso — direto do IPEA
  (com o certificado corrigido) **ou** via fallback (mirror/vendorizado) —
  sem lançar o erro de certificado e sem exigir nenhuma ação manual do
  usuário final.
- Nenhum ponto do código desabilita/enfraquece a verificação de certificado
  SSL (`grep -rn "VerifyNone\|verify=False" core/` vazio).
- Se todas as fontes falharem (ex.: MITM corporativo desconhecido), o erro
  exibido ao usuário explica a causa provável e o que fazer — não é um
  traceback cru.
- Causa raiz documentada em `docs/ssl-ipea-windows.md` e em `CLAUDE.md` §10.
