# Diagnóstico de Cadeia de Certificados SSL — IPEA

Este documento registra o diagnóstico da cadeia de certificados SSL do servidor do IPEA (`www.ipea.gov.br`), conforme planejado no passo 1 do [PLAN.md](file:///home/diego/projects/gisbr/PLAN.md).

## Comando Executado

```bash
openssl s_client -connect www.ipea.gov.br:443 -servername www.ipea.gov.br -showcerts < /dev/null
```

## Resultados do Diagnóstico

A execução do comando no ambiente de desenvolvimento (Linux/Pop!_OS) completou com sucesso, indicando status de verificação **OK** (`Verify return code: 0 (ok)`).

### Cadeia de Certificados Entregue pelo Servidor

O servidor do IPEA entrega **três certificados** na cadeia TLS:

1. **Certificado 0 (Folha / Leaf):**
   * **Subject:** `CN = *.ipea.gov.br`
   * **Issuer:** `C = GB, O = Sectigo Limited, CN = Sectigo Public Server Authentication CA DV R36`
   * **Validade:** Em vigor.

2. **Certificado 1 (Intermediário 1):**
   * **Subject:** `C = GB, O = Sectigo Limited, CN = Sectigo Public Server Authentication CA DV R36`
   * **Issuer:** `C = GB, O = Sectigo Limited, CN = Sectigo Public Server Authentication Root R46`

3. **Certificado 2 (Intermediário 2 / Root Cruzado):**
   * **Subject:** `C = GB, O = Sectigo Limited, CN = Sectigo Public Server Authentication Root R46`
   * **Issuer:** `C = US, ST = New Jersey, L = Jersey City, O = The USERTRUST Network, CN = USERTrust RSA Certification Authority`

### Validação da Cadeia

```
[*.ipea.gov.br] (Folha)
       │
       ▼ (Assinado por)
[Sectigo Public Server Authentication CA DV R36] (Intermediário 1)
       │
       ▼ (Assinado por)
[Sectigo Public Server Authentication Root R46] (Intermediário 2 / Root Cruzado)
       │
       ▼ (Assinado por)
[USERTrust RSA Certification Authority] (Root CA de Confiança)
```

## Conclusões

1. **Cadeia Completa do Lado do Servidor:** O servidor do IPEA **não** está enviando uma cadeia incompleta de intermediários. Ele fornece todos os certificados intermediários necessários (Certificados 1 e 2) até a Autoridade Certificadora Raiz (`USERTrust RSA Certification Authority`).
2. **Causa Provável do Erro no Windows/QGIS (OSGeo4W):**
   * O erro `"Unable to find issuer certificate"` (ou "Impossível Localizar o Emissor do Certificado") no QGIS para Windows ocorre porque o store de CAs do ambiente do QGIS/OSGeo4W (ou a biblioteca Qt utilizada por ele) **não confia** ou **não possui** a raiz `USERTrust RSA Certification Authority` ou o certificado intermediário `Sectigo Public Server Authentication Root R46`.
   * Como o Linux/Pop!_OS confia na raiz `USERTrust` por padrão, a verificação passa sem problemas no ambiente de desenvolvimento do Diego.
3. **Próximos Passos (Passo 2 e 3 do PLAN.md):**
   * Confirmar se o erro se resolve no Windows fornecendo o certificado intermediário/raiz faltante no plugin (injetando-o via `QSslConfiguration` na requisição de rede sem desabilitar a verificação de segurança).
