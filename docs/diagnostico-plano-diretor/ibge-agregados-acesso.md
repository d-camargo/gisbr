# Medição de Acesso aos Agregados Tabulares do IBGE (API v3)

Documento de medição empírica e registro de arquitetura para acesso a dados tabulares do IBGE (PAM e Censo Agropecuário 2017) via API de Agregados v3.

---

## 1. Descarte do APISIDRA (`apisidra.ibge.gov.br`)

O endpoint legado `apisidra.ibge.gov.br` foi medido e **descartado** por estar bloqueado por WAF/Cloudflare (retorna HTTP 403 acompanhado do HTML de desafio "Just a moment...").

### Comando de medição real
```bash
curl -i -s "https://apisidra.ibge.gov.br/values/t/1612/n6/3106200/v/all/p/last" | head -n 25
```

### Saída real capturada
```http
HTTP/2 403 
date: Thu, 17 Sep 2026 22:13:53 GMT
content-type: text/html; charset=UTF-8
server: cloudflare
cf-mitigated: challenge

<!DOCTYPE html><html lang="en-US"><head><title>Just a moment...</title>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
...
```

> **Decisão:** Não utilizar `apisidra.ibge.gov.br` em nenhuma circunstância. Utilizar exclusivamente a API v3 de Serviços de Dados (`servicodados.ibge.gov.br/api/v3/agregados`).

---

## 2. Formato de URL da API v3 de Agregados

A API v3 nativa do IBGE é pública e não requer autenticação nem token. O padrão de requisição para agregados tabulares por município é:

```text
https://servicodados.ibge.gov.br/api/v3/agregados/{tabela}/periodos/{periodo}/variaveis/{v1|v2|...}?localidades=N6[{code_muni}]&classificacao={id_class}[all]
```

### Parâmetros principais
- `{tabela}`: Código numérico da tabela de agregados (ex.: `1612`, `1613`, `6881`).
- `{periodo}`: Ano desejado (ex.: `2023`, `2017`) ou `-1` para a medição/período mais recente.
- `{v1|v2}`: IDs das variáveis separados pelo caractere `|` (pipe).
- `localidades`: Nível territorial `N6` para municípios, no formato `N6[{code}]` (código IBGE de 7 dígitos, ex.: `3106200` para BH ou `3170404` para Unaí).
- `classificacao`: Filtro de classificação temática, ex.: `81[all]` para todos os produtos ou `81[2713]` para um produto específico.

---

## 3. Tabelas Decididas, Variáveis e Classificações

Para a rodada atual, foram definidas **3 fontes tabulares de dados agropecuários**:

### 3.1. PAM Lavouras Temporárias — Tabela `1612`
- **Nome:** Produção Agrícola Municipal - Lavouras temporárias.
- **Variáveis (`/metadados`):**
  - `109`: Área plantada (Hectares)
  - `216`: Área colhida (Hectares)
  - `214`: Quantidade produzida (Toneladas)
  - `112`: Rendimento médio da produção (Kg/ha)
  - `215`: Valor da produção (Mil Reais)
- **Classificação:** `81` — Produto das lavouras temporárias (ex.: `2713` Soja, `2711` Milho, `2696` Cana-de-açúcar, `2702` Feijão).

### 3.2. PAM Lavouras Permanentes — Tabela `1613`
- **Nome:** Produção Agrícola Municipal - Lavouras permanentes.
- **Variáveis (`/metadados`):**
  - `2313`: Área destinada à colheita (Hectares)
  - `216`: Área colhida (Hectares)
  - `214`: Quantidade produzida (Toneladas)
  - `112`: Rendimento médio da produção (Kg/ha)
  - `215`: Valor da produção (Mil Reais)
- **Classificação:** `82` — Produto das lavouras permanentes (ex.: `2717` Café em grão, `2719` Laranja, `2718` Banana).

### 3.3. Censo Agropecuário 2017 — Tabela `6881`
- **Nome:** Número de estabelecimentos agropecuários com área e Área dos estabelecimentos agropecuários, por tipologia, utilização das terras, condição do produtor em relação às terras, grupos de atividade econômica e origem da orientação técnica recebida.
- **Variáveis (`/metadados`):**
  - `9587`: Número de estabelecimentos agropecuários com área (Unidades)
  - `184`: Área dos estabelecimentos agropecuários (Hectares)
- **Classificação:** `222` — Utilização das terras (ex.: `110087` Total, `113470` Lavouras permanentes, `113471` Lavouras temporárias, `113473` Pastagens naturais, `113474` Pastagens plantadas, `113477` Matas ou florestas naturais).

---

## 4. Resolução de Períodos (`periodos/-1` vs Fixo)

A API v3 aceita o sinalizador `periodos/-1` para retornar a apuração mais recente da tabela.

### Teste de validação empírica

```python
import urllib.request, json, gzip

def check_period(table_id):
    url = f"https://servicodados.ibge.gov.br/api/v3/agregados/{table_id}/periodos/-1/variaveis/default?localidades=N6[3106200]"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        content = resp.read()
        if content[:2] == b"\x1f\x8b":
            content = gzip.decompress(content)
        data = json.loads(content.decode("utf-8"))
        period = list(data[0]["resultados"][0]["series"][0]["serie"].keys())[0]
        return period

print("Tabela 1612 (PAM Temp):", check_period(1612)) # 2025
print("Tabela 1613 (PAM Perm):", check_period(1613)) # 2025
print("Tabela 6881 (Censo Agro):", check_period(6881)) # 2017
```

### Conclusão
- `periodos/-1` **é aceito** e resolve automaticamente para o período mais recente disponível (`2025` para PAM 1612/1613, `2017` para Censo Agropecuário 6881).

---

## 5. Códigos Especiais em `serie`

A API v3 do IBGE retorna no dicionário `serie` valores numéricos codificados como strings, além de códigos especiais padronizados da estatística oficial brasileira:

| Código Especial | Significado | Tratamento no GisBR |
|---|---|---|
| `"-"` | Zero absoluto / Fenômeno não existente | **`NULL` / `None`** (ver nota abaixo) |
| `"..."` | Dado numérico não disponível / desconhecido | Tratar como `NULL` / `None` |
| `".."` | Não se aplica / informação não prestada | Tratar como `NULL` / `None` |
| `"X"` | Dado omitido/suprimido por sigilo estatístico | Tratar como `NULL` / `None` (registrar nota de sigilo no log) |
| `"*"` | Valor estimado ou preliminar | Tratar valor numérico correspondente (se presente) |

> **Nota de decisão (D4 da rodada 18):** embora a convenção estatística clássica
> trate `"-"` como zero absoluto, o GisBR converte **todos** os códigos especiais
> — incluindo `"-"` — para `NULL`, nunca para `0`. Num diagnóstico de Plano
> Diretor, "não há dado apurado" e "a área plantada é zero" são conclusões
> opostas; na dúvida, o plugin preserva a ausência. Implementado em
> `gisbr/core/agregados_parser.py` (`SPECIAL_NONE_CODES`).

---

## 6. Fixture JSON Real (Abreviada)

Exemplo de resposta capturada da API v3 para a Tabela `1612` (Município de Unaí/MG, código `3170404`, ano `2023`, produto `2713` Soja em grão):

```json
[
  {
    "id": "109",
    "variavel": "Área plantada",
    "unidade": "Hectares",
    "resultados": [
      {
        "classificacoes": [
          {
            "id": "81",
            "nome": "Produto das lavouras temporárias",
            "categoria": {
              "2713": "Soja (em grão)"
            }
          }
        ],
        "series": [
          {
            "localidade": {
              "id": "3170404",
              "nivel": {
                "id": "N6",
                "nome": "Município"
              },
              "nome": "Unaí (MG)"
            },
            "serie": {
              "2023": "185000"
            }
          }
        ]
      }
    ]
  },
  {
    "id": "214",
    "variavel": "Quantidade produzida",
    "unidade": "Toneladas",
    "resultados": [
      {
        "classificacoes": [
          {
            "id": "81",
            "nome": "Produto das lavouras temporárias",
            "categoria": {
              "2713": "Soja (em grão)"
            }
          }
        ],
        "series": [
          {
            "localidade": {
              "id": "3170404",
              "nivel": {
                "id": "N6",
                "nome": "Município"
              },
              "nome": "Unaí (MG)"
            },
            "serie": {
              "2023": "699300"
            }
          }
        ]
      }
    ]
  },
  {
    "id": "215",
    "variavel": "Valor da produção",
    "unidade": "Mil Reais",
    "resultados": [
      {
        "classificacoes": [
          {
            "id": "81",
            "nome": "Produto das lavouras temporárias",
            "categoria": {
              "2713": "Soja (em grão)"
            }
          }
        ],
        "series": [
          {
            "localidade": {
              "id": "3170404",
              "nivel": {
                "id": "N6",
                "nome": "Município"
              },
              "nome": "Unaí (MG)"
            },
            "serie": {
              "2023": "1847725"
            }
          }
        ]
      }
    ]
  }
]
```

---

## 7. Porta Aberta: Consulta por Estado Inteiro (`N6[in N3[{uf}]]`)

Fica registrado que o parâmetro `localidades=N6[in N3[{uf}]]` (ex.: `N6[in N3[31]]` para Minas Gerais) é suportado nativamente pela API v3 do IBGE.
Quando utilizado, o parâmetro retorna os dados de **todos os municípios do Estado em uma única requisição HTTP** (ex.: 853 séries no caso de MG).

> **Nota de Implementação:** Esta funcionalidade permanece como **porta aberta** (não implementada nesta rodada), já que o conector do GisBR consulta por município individual (`N6[{code}]`).
