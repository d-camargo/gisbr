# Instalação

## Pelo repositório oficial do QGIS

É o caminho normal de uso. No QGIS:

1. *Complementos → Gerenciar e Instalar Complementos…*
2. Aba **Todos**, procure por **GisBR**.
3. Clique em **Instalar Complemento**.

O plugin aparece então em dois lugares: o menu/barra de ferramentas **GisBR**,
que abre o painel de [diagnóstico de Plano Diretor](guias/diagnostico.md), e a
**Caixa de Ferramentas de Processamento**, no provedor *GisBR*, com os
algoritmos [`read_*` do espelho geobr](guias/geobr.md).

## Instalação de desenvolvimento (symlink)

Para trabalhar no código, faça o deploy por symlink em vez de copiar arquivos —
assim o que está no repositório é o que o QGIS carrega:

```bash
cd ~/Documentos/SIG/gisbr/   # ou onde estiver o repositório
make deploy        # symlink -> profiles/default/python/plugins/gisbr
make test          # checagem de sintaxe (ast.parse, sem QGIS)
```

Recarregue com o **Plugin Reloader** ou reinicie o QGIS, e ative o plugin em
*Complementos → Gerenciar e Instalar Complementos…*.

!!! warning "`make test` não é o portão de compatibilidade"
    O `make test` só roda `ast.parse` e pega erro de sintaxe. A verificação real
    de compatibilidade é o **smoke test que importa todos os módulos do plugin
    sob Qt5 (QGIS 3.x) e Qt6 (QGIS 4.x)**.

## Requisitos

- **QGIS 3.16 ou superior**, incluindo **QGIS 4.x (Qt6)** — o plugin declara
  `supportsQt6=True` e é testado nos dois ambientes, Qt5 e Qt6.
- **Conexão com a internet** no primeiro download de cada base; os usos
  seguintes aproveitam o cache local.
- **Nada de `pip install`**: o plugin usa apenas PyQGIS e a stdlib do Python que
  já vêm com o QGIS.

### Opcional: Parquet (algoritmos v2 e `join_censo`)

O GisBR **funciona sem isto**. Toda a Fase 1 (os 26 algoritmos `read_*` sobre
GeoPackage) e o painel de diagnóstico não dependem de Parquet.

O suporte a Parquet só é necessário para os algoritmos `read_*_v2` (backend
v2.0.0 do geobr), para as fontes só-v2 do diagnóstico e para o `join_censo`
(junção com o censobr). Basta **uma** das opções:

- **`pyarrow`** — recomendado no Linux (QGIS do apt ou Flatpak), porque
  aproveita o QGIS já instalado:

    ```bash
    pip install --user pyarrow
    ```

- **Driver GDAL `Parquet`/`Arrow`** — as builds oficiais de Windows e macOS
  costumam já trazer. Para conferir:

    ```bash
    ogrinfo --formats | grep -i parquet
    ```

    Se faltar, o caminho confiável é o conda-forge, com a versão casando com a
    do GDAL do QGIS:

    ```bash
    conda install -c conda-forge libgdal-arrow-parquet
    ```

!!! note "Pop!_OS / Ubuntu / Flatpak"
    Nessas builds o driver GDAL Parquet **não vem** (verificado em GDAL 3.8.4 do
    apt e 3.13 do Flatpak) e o pacote `gdal-plugins` do apt não o instala. Use o
    `pyarrow`.

Sem nenhum dos dois, os algoritmos v2 avisam qual opção instalar e a Fase 1
continua funcionando normalmente.
