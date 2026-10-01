#!/usr/bin/env bash
#
# Reprodução da visibilidade do botão GISBR na barra de plugins (Wayland / QGIS).
#
# Saída medida sem a correção (reprodução da M1):
#   Startup: platform=wayland toolbar_width=62 visible=False
#   Reload: platform=wayland toolbar_width=62 visible=False
#   Resultado: FALHA (botão oculto no transbordo)
#   Exit code: 1
#
# Saída medida pós-correção (D1):
#   Startup: platform=wayland toolbar_width=62 visible=True
#   Reload: platform=wayland toolbar_width=62 visible=True
#   Resultado: SUCESSO (visível no startup e após reload)
#   Exit code: 0
#

set -euo pipefail

IMAGE="${1:-docker.io/qgis/qgis:3.44}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Rodando reprodução com imagem: ${IMAGE}"

podman run --rm \
  -v "${REPO_DIR}:/w:z" \
  "${IMAGE}" bash -c '
    set -euo pipefail

    # 1. Instala weston se não estiver presente
    if ! command -v weston >/dev/null 2>&1; then
      apt-get update -qq && apt-get install -y -qq weston >/dev/null 2>&1
    fi

    # 2. Sobe weston headless com socket wayland-1
    export XDG_RUNTIME_DIR=/tmp/runtime-root
    mkdir -p "$XDG_RUNTIME_DIR"
    chmod 700 "$XDG_RUNTIME_DIR"

    weston --backend=headless-backend.so --socket=wayland-1 >/tmp/weston.log 2>&1 &
    WESTON_PID=$!

    # Aguarda socket do Wayland
    for i in $(seq 1 50); do
      if [ -S "$XDG_RUNTIME_DIR/wayland-1" ]; then
        break
      fi
      sleep 0.1
    done

    if [ ! -S "$XDG_RUNTIME_DIR/wayland-1" ]; then
      echo "ERRO: socket do Wayland não foi criado a tempo." >&2
      cat /tmp/weston.log >&2
      kill "$WESTON_PID" 2>/dev/null || true
      exit 1
    fi

    # 3. Variáveis de ambiente exigidas
    export WAYLAND_DISPLAY=wayland-1
    export QT_QPA_PLATFORM=wayland
    export DISPLAY=:99

    # 4. Configura perfil limpo com symlink para /w/gisbr e gisbr=true
    for VER in QGIS3 QGIS4; do
      for PROF in default repro; do
        PDIR="/root/.local/share/QGIS/${VER}/profiles/${PROF}"
        mkdir -p "${PDIR}/python/plugins"
        mkdir -p "${PDIR}/QGIS"
        ln -sf /w/gisbr "${PDIR}/python/plugins/gisbr"
        cat <<EOF > "${PDIR}/QGIS/${VER}.ini"
[PythonPlugins]
gisbr=true
EOF
      done
    done

    # 5. Executa QGIS com o harness de reprodução
    set +e
    qgis --nologo --noversioncheck --code /w/tools/repro_barra_ferramentas.py
    QGIS_EXIT=$?
    set -e

    kill "$WESTON_PID" 2>/dev/null || true
    wait "$WESTON_PID" 2>/dev/null || true

    exit "$QGIS_EXIT"
  '
