#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python}"
echo "Building native modules with: $($PYTHON_BIN -c 'import sys; print(sys.executable)')"
echo "Python ABI: $($PYTHON_BIN -c 'import sysconfig; print(sysconfig.get_config_var("SOABI"))')"

# Remove extension modules built for another Python ABI.
find common apps/simulated/plant_models -maxdepth 1 -type f \
  \( -name '*.so' -o -name '*.pyd' \) -print -delete
rm -rf build

"$PYTHON_BIN" setup_native.py build_ext --inplace --parallel 8
"$PYTHON_BIN" - <<'PY'
from common.honu_native import NATIVE_AVAILABLE
from common.mlp_native import NATIVE_AVAILABLE as MLP_AVAILABLE
from common.mrac_native import NATIVE_AVAILABLE as MRAC_AVAILABLE
from common.physical_native import NATIVE_AVAILABLE as ODE_AVAILABLE
if not NATIVE_AVAILABLE:
    raise SystemExit("Native extension build completed, but import failed")
print("C++ HONU kernel: available")
if not MLP_AVAILABLE:
    raise SystemExit("Native MLP extension import failed")
print("C++ recursive MLP rollout: available")
if not MRAC_AVAILABLE:
    raise SystemExit("Native MRAC extension import failed")
print("C++ MRAC adaptation: available")
if not ODE_AVAILABLE:
    raise SystemExit("Native physical ODE extension import failed")
print("C++ physical ODE RK4: available")
PY
