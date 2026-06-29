# Taxonomia e Classificação de Cidades

Este documento consolida as regras legais para a obrigatoriedade do Plano Diretor e as classificações oficiais que ajudam a tipificar as cidades, facilitando a automação de diagnósticos.

## 1. Estatuto da Cidade (Lei 10.257/2001)

O **Plano Diretor** é o instrumento básico da política de desenvolvimento e expansão urbana. De acordo com o Artigo 41 do Estatuto da Cidade, a elaboração do Plano Diretor é **obrigatória** para os municípios que se enquadram em pelo menos uma das seguintes situações:

1. **População:** Cidades com mais de 20 mil habitantes.
2. **Regiões Metropolitanas:** Municípios integrantes de regiões metropolitanas e aglomerações urbanas.
3. **Instrumentos Urbanos:** Onde o Poder Público municipal pretenda utilizar instrumentos de política urbana (parcelamento, edificação ou utilização compulsórios).
4. **Turismo:** Municípios integrantes de áreas de especial interesse turístico.
5. **Impacto Ambiental:** Municípios inseridos na área de influência de empreendimentos ou atividades com significativo impacto ambiental de âmbito regional ou nacional.
6. **Risco:** Municípios incluídos no cadastro nacional de áreas suscetíveis à ocorrência de deslizamentos de grande impacto, inundações bruscas ou processos geológicos/hidrológicos correlatos.

## 2. IBGE: REGIC (Regiões de Influência das Cidades)

A REGIC classifica os centros urbanos brasileiros em cinco níveis de hierarquia, com base em sua capacidade de atrair fluxos (bens, serviços, gestão pública/privada):

- **1. Metrópoles:** (Ex: Grande Metrópole Nacional - São Paulo, Metrópoles Nacionais e Metrópoles). Alta atração e influência nacional/regional.
- **2. Capitais Regionais (A, B, C):** Alta concentração de atividades de gestão com alcance espacial menor que metrópoles.
- **3. Centros Sub-Regionais (A, B):** Atividades de gestão menos complexas, influenciando municípios próximos.
- **4. Centros de Zona (A, B):** Centros menores que polarizam poucas cidades vizinhas.
- **5. Centros Locais:** A influência se restringe aos limites do próprio município.

**Conexão com `code_muni`:** A unidade de análise pode ser o município (identificado pelo código IBGE de 7 dígitos) ou um "Arranjo Populacional" (agrupamento de municípios conurbados). No `GisBR`, cruzamos os dados da REGIC usando o `code_muni`.

## 3. Outras Classificações Relevantes do IBGE

- **Arranjos Populacionais:** Agrupamentos de municípios com forte integração populacional (movimentos pendulares para trabalho/estudo). 
- **Classificação Rural-Urbano:** Tipifica os municípios com base no grau de urbanização, densidade e acessibilidade, variando de "Urbano" a "Rural Remoto".

Essas tipologias ajudam o diagnóstico a parametrizar quais indicadores exibir com mais peso (ex: mobilidade em arranjos populacionais vs. agricultura em rurais remotos).
