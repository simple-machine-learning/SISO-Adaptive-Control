# SISO Adaptive Control

A unified desktop software package for data generation or import, HONU-based system identification, model-reference adaptive control (MRAC), and model predictive control (MPC) of SISO systems.

## Installation and start

The Python application can be run on both Windows and Linux. Using a virtual environment is recommended.

### Windows

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python launcher.py
```

### Linux

```bash	
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
chmod +x build_native_linux.sh
./build_native_linux.sh
python launcher.py
```

After activation, `python -m pip` installs packages into the same interpreter that runs the application. The `py` command is a Windows launcher and is therefore used only to create the Windows virtual environment.

## Modes

**Simulated systems** uses physical nonlinear ODE plants. The user can select a plant, generate training data, identify an LNU or QNU model, compare GD, NGD, batch and LM learning, train an MRAC controller, test the controller on the physical plant, and run HONU MPC experiments.

**Measured systems** imports experimental records and maps selected channels to the common sampled interface `t`, `u`, `y`. The user can inspect and resample data, identify an LNU or QNU model, train MRAC, and investigate HONU MPC using the measured record.

## Repository structure

```text
SISO_Adaptive_Control/
├── launcher.py
├── common/                 shared numerical modules
├── apps/
│   ├── simulated/          physical ODE workflow
│   └── measured/           measured-data workflow
├── documentation/          unified Sphinx documentation
├── development_notes/      consolidated historical implementation notes
└── native					native C++ and Cython extensions, benchmarks and tests
```

The mode-specific computational scripts were deliberately retained to avoid changing validated execution paths. Only modules that were byte-identical in both variants were moved into `common`.

## Documentation

Build the unified documentation from the project root.

### Windows

```bat
python -m pip install -r documentation\requirements.txt
python -m sphinx -b html documentation documentation\_build\html
```

Open `documentation\_build\html\index.html`.

### Linux

```bash
python -m pip install -r documentation/requirements.txt
python -m sphinx -b html documentation documentation/_build/html
```

Open `documentation/_build/html/index.html`.

## Direct multi-horizon HONU MPC (experimental, pure Python)

The simulated-data HONU MPC page now contains a **prediction** selector:

- `Recursive`: original one-step HONU recursively rolled over the MPC horizon.
- `Direct multi-horizon`: one multi-output HONU maps the current measured history and the complete candidate future input sequence directly to all predicted outputs. Predicted outputs are therefore not fed back recursively.

A direct model is tied to the selected MPC horizon `Np`. After changing `Np`, identify the HONU plant again before running frozen MPC. Sliding retraining rebuilds the direct model for the active horizon automatically. The implementation is intentionally pure Python/NumPy for validation before native Linux acceleration.

## Direct multi-horizon identification diagnostics

For `prediction = Direct multi-horizon`, the identification result now displays aligned direct predictions for selected horizons (first, middle, and final), per-horizon prediction errors, RMSE by horizon, HONU weight-vector norm by horizon, and per-horizon local AR-equivalent spectral-radius diagnostics (median and maximum over the identification data). The spectral-radius plot is a sensitivity diagnostic for each static direct predictor; it is not a recursive closed-loop stability certificate.

## Recursive rollout-trained HONU

The simulated-data MPC page includes a third prediction mode, `Recursive rollout-trained`.
It identifies one LNU/QNU predictor by minimizing truncated free-running rollout errors over the active MPC horizon `Np`. Each rollout starts from measured output/input history; inside the rollout, predicted outputs are fed back into the HONU regressor. Frozen and sliding MPC use the same predictor interface as the original recursive mode.

Smoke test:

```bash
cd apps/simulated
PYTHONPATH=../../common:. python test_recursive_rollout_training.py
```

## MRAC plant HONU recurrent rollout training

The simulated MRAC GUI now offers `Plant HONU training: One-step / Recursive rollout` and a rollout length `N_r`. The selected original identifier (Ridge, GD/NGD, or LM) first supplies one-step weights. In recursive-rollout mode those weights are then refined on overlapping free-running segments. Each segment starts from measured output/input history and feeds back predicted output only within the segment. The MRAC controller adaptation law is unchanged.

Smoke test:

```bash
cd apps/simulated
PYTHONPATH=../../common:. python test_mrac_rollout_plant_training.py
```
