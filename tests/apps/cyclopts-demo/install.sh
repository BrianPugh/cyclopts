#!/usr/bin/env bash
# Reinstall cyclopts-demo against the in-tree cyclopts and reinstall its zsh
# completion script, so manual TAB testing reflects the current source.
#
# After running, in a fresh zsh:
#   cyclopts-demo deploy --environment=<TAB>     # expect: dev staging production
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$DEMO_DIR/../../.." && pwd)"
INSTALLED="$HOME/.zsh/completions/_cyclopts-demo"

cd "$REPO"

echo "==> Project: $REPO"
echo "==> Demo:    $DEMO_DIR"

echo "==> Installing cyclopts-demo (editable, --no-deps) into project venv..."
uv pip install -e "$DEMO_DIR" --no-deps --quiet

echo "==> uv run resolves cyclopts-demo to:"
uv run --no-sync bash -c 'command -v cyclopts-demo' | sed 's/^/    /'

echo "==> uv run python sees cyclopts at:"
uv run --no-sync python -c "import cyclopts; print('   ', cyclopts.__file__); print('    version:', cyclopts.__version__)"

echo "==> Removing stale completion at $INSTALLED..."
rm -f "$INSTALLED"

echo "==> Generating + installing completion..."
uv run --no-sync cyclopts-demo --install-completion --shell zsh

if [[ ! -f "$INSTALLED" ]]; then
    echo "FAIL: $INSTALLED was not written" >&2
    exit 1
fi

n_prepass=$(grep -c '^[[:space:]]*compset -P' "$INSTALLED" || true)
echo "==> $INSTALLED ($n_prepass eq-form prepass entries)"
if [[ "$n_prepass" -eq 0 ]]; then
    echo "FAIL: zero prepass entries -- generator came from a stale cyclopts." >&2
    echo "      Check that the cyclopts file printed above is in $REPO/cyclopts/." >&2
    exit 1
fi

cat <<'EOF'

==> Done. Verify in zsh:

    exec zsh
    cyclopts-demo deploy --environment=<TAB>    # expect: dev staging production
    cyclopts-demo deploy --environment <TAB>    # space form
    cyclopts-demo files cp --rec<TAB>           # bool flag completion
EOF
