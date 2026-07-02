# Makefile — geobr-qgis
# Deploy por symlink para o perfil default do QGIS (padrao dos outros plugins).

PLUGINNAME = gisbr
QGIS_PLUGINS = $(HOME)/.local/share/QGIS/QGIS3/profiles/default/python/plugins
# Perfil do QGIS instalado via Flatpak (org.qgis.qgis) — traz GDAL com GeoParquet.
FLATPAK_PLUGINS = $(HOME)/.var/app/org.qgis.qgis/data/QGIS/QGIS3/profiles/default/python/plugins
TARGET = $(QGIS_PLUGINS)/$(PLUGINNAME)
FLATPAK_TARGET = $(FLATPAK_PLUGINS)/$(PLUGINNAME)
SRC = $(CURDIR)

.PHONY: deploy deploy-flatpak undeploy undeploy-flatpak clean test help

help:
	@echo "make deploy          - symlink do plugin no perfil do QGIS do sistema"
	@echo "make deploy-flatpak  - symlink no perfil do QGIS Flatpak (Fase 2/Parquet)"
	@echo "make undeploy        - remove o symlink (sistema)"
	@echo "make undeploy-flatpak- remove o symlink (flatpak)"
	@echo "make clean           - remove __pycache__"
	@echo "make test            - smoke test de sintaxe (sem QGIS)"

deploy:
	@mkdir -p $(QGIS_PLUGINS)
	@if [ -e "$(TARGET)" ] && [ ! -L "$(TARGET)" ]; then \
		echo "ERRO: $(TARGET) existe e nao e symlink. Remova manualmente."; exit 1; \
	fi
	@ln -sfn "$(SRC)" "$(TARGET)"
	@echo "symlink: $(TARGET) -> $(SRC)"
	@echo "Recarregue no QGIS (Plugin Reloader) ou reinicie."

deploy-flatpak:
	@if [ ! -d "$(dir $(FLATPAK_PLUGINS))" ]; then \
		echo "ERRO: perfil Flatpak nao existe ainda."; \
		echo "Instale e abra o QGIS Flatpak uma vez:"; \
		echo "  flatpak install -y flathub org.qgis.qgis && flatpak run org.qgis.qgis"; \
		exit 1; \
	fi
	@mkdir -p "$(FLATPAK_PLUGINS)"
	@if [ -e "$(FLATPAK_TARGET)" ] && [ ! -L "$(FLATPAK_TARGET)" ]; then \
		echo "ERRO: $(FLATPAK_TARGET) existe e nao e symlink."; exit 1; \
	fi
	@ln -sfn "$(SRC)" "$(FLATPAK_TARGET)"
	@echo "symlink (flatpak): $(FLATPAK_TARGET) -> $(SRC)"

undeploy:
	@if [ -L "$(TARGET)" ]; then rm "$(TARGET)" && echo "removido $(TARGET)"; \
	else echo "nada a remover"; fi

undeploy-flatpak:
	@if [ -L "$(FLATPAK_TARGET)" ]; then rm "$(FLATPAK_TARGET)" && echo "removido $(FLATPAK_TARGET)"; \
	else echo "nada a remover"; fi

clean:
	@find . -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "limpo"

transup:
	@mkdir -p i18n
	@lupdate provider.py geobr_qgis_plugin.py gui/diagnostico_dock.py algorithms/*.py -ts i18n/gisbr_pt.ts

transcompile:
	@lrelease i18n/gisbr_pt.ts

test:
	@python3 -c "import ast,glob,sys; [ast.parse(open(f).read(), f) for f in glob.glob('**/*.py', recursive=True)]; print('sintaxe OK')"

