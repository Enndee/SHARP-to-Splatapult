# SHARP → Splatapult

**Turn any single photo into an interactive 3D scene — in one click.**

SHARP → Splatapult chains Apple's [SHARP](https://github.com/apple/ml-sharp) model with the [splatapult](https://github.com/hyperlogic/splatapult) viewer so you can go from a JPEG to a fully interactive 3D Gaussian Splat without touching the command line.




https://github.com/user-attachments/assets/d6374ab6-0c8c-4cc0-8af5-9e457b934254


<img width="3322" height="1776" alt="grafik" src="https://github.com/user-attachments/assets/a56ce94a-1e2d-4e79-adeb-67950933ff4a" />


---

## What it does

```
📷 photo.jpg
   │
   ▼  Step 1 — Apple SHARP  (AI reconstruction)
   │
   ▼  Step 2 — Coordinate transform  (OpenCV → OpenGL axes)
   │
   ▼  Step 3 — 3dgsconverter  (PLY → .spz, ~10× smaller)
   │
   ▼  splatapult.exe  (real-time viewer, free-fly camera)
```

---

## Requirements

| Requirement | Notes |
|---|---|
| **Windows 10 / 11 x64** | Required |
| **NVIDIA GPU (GTX 10xx or newer)** | Strongly recommended – GPU runs SHARP ~10× faster than CPU |
| **[Anaconda](https://www.anaconda.com/download) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html)** | Required |
| **[Git for Windows](https://git-scm.com/download/win)** | Required |
| ~6 GB free disk space | For the conda env + PyTorch |
| Internet connection (first setup only) | To download SHARP weights (~500 MB) |

---

## Quick Start — Pre-built release (recommended)

1. **Download** the latest release zip from the [Releases](../../releases) page
2. **Extract** it anywhere (e.g. `C:\Tools\SHARP-to-Splatapult\`)
3. **Run `Setup_NewPC.bat`** once — this installs the `sharp` conda environment, PyTorch, and all dependencies (~15 min first time)
4. **Done!** Either:
   - Double-click **`SHARP_to_Splatapult.exe`** and pick an image
   - Right-click any JPEG/PNG → **Send To → SHARP to Splatapult** (shortcut created by Setup)

> **First run note:** SHARP downloads its model weights (~500 MB) automatically on the very first conversion. Subsequent runs are instant.

---

## Quick Start — Run from source

```bat
git clone https://github.com/Enndee/SHARP-to-Splatapult.git
cd SHARP-to-Splatapult
Setup_NewPC.bat
```

Then either:
- Run `python SHARP_to_Splatapult.py` directly from the `sharp` conda env
- Or build the standalone exe with `build_exe.bat`

> You will also need a compiled `splatapult\` folder next to the script.  
> See [Building splatapult](#building-splatapult) below.

---

## Release folder layout

After extracting a release zip, the folder looks like this:

```
SHARP-to-Splatapult\
├── SHARP_to_Splatapult.exe   ← Main GUI (double-click to launch)
├── Setup_NewPC.bat           ← Run once on a new PC
├── splatapult\               ← Viewer binaries (required, do not move)
│   ├── splatapult.exe
│   ├── SDL2.dll
│   ├── glew32.dll
│   └── shader\, data\, ...
└── README.md
```

The `.exe` and the `splatapult\` folder **must stay in the same directory**.

---

## GUI overview

| Element | Function |
|---|---|
| Click zone / Send To | Select the input image |
| CUDA / CPU radio | Choose GPU (fast) or CPU (slow) compute |
| Log area | Live output from SHARP and the converter |
| Progress bar | Spins while a conversion is running |

---

## Using the batch script (`SHARP_to_Splatapult.bat`)

If you prefer not to use the GUI, you can drag-and-drop an image onto `SHARP_to_Splatapult.bat` directly, or call it from the command line:

```bat
SHARP_to_Splatapult.bat "C:\Photos\my_room.jpg"
```

The `.spz` output is saved next to the input image.

---

## Building splatapult

The viewer is a fork of [hyperlogic/splatapult](https://github.com/hyperlogic/splatapult) with added `.spz` loading support (see [PR](https://github.com/hyperlogic/splatapult/pulls)).

```bat
git clone --recurse-submodules https://github.com/Enndee/splatapult.git
cd splatapult
git checkout feature/spz-format-support
cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE=vcpkg/scripts/buildsystems/vcpkg.cmake
cmake --build build --config Release
```

Then copy the `build\Release\` contents into a `splatapult\` folder next to `SHARP_to_Splatapult.exe`.

---

## Building the .exe from source

```bat
build_exe.bat
```

Requires the `sharp` conda environment (run `Setup_NewPC.bat` first). Produces `dist\SHARP_to_Splatapult.exe` using PyInstaller.

---

## How it works

### Step 1 — SHARP reconstruction
[Apple's SHARP](https://github.com/apple/ml-sharp) (Single image **H**igh-quality **A**uto-**R**egressive **P**redictor) is a transformer-based model that predicts a full 3D Gaussian Splat scene from a single RGB image. It runs via the `sharp predict` CLI.

### Step 2 — Coordinate system fix
SHARP outputs PLY files in OpenCV convention (+Z forward, Y-down). Splatapult uses OpenGL convention (−Z forward, Y-up). The Y and Z position axes and the corresponding quaternion components (rot_2, rot_3) are negated.

### Step 3 — SPZ compression
[3dgsconverter](https://github.com/francescofugazzi/3dgsconverter) converts the PLY to Niantic's [`.spz` format](https://github.com/nianticlabs/spz) — a gzip-compressed binary that is typically **~10× smaller** than the equivalent PLY. The PLY is deleted after successful conversion.

### Step 4 — Viewer
[splatapult](https://github.com/hyperlogic/splatapult) renders the `.spz` file in real time using a free-fly camera. Our fork adds native `.spz` loading support alongside the existing `.ply` support.

---

## Troubleshooting

**"splatapult.exe not found"**  
Make sure the `splatapult\` folder is next to the `.exe`. If building from source, run the cmake build first.

**"Conda env 'sharp' not found"**  
Run `Setup_NewPC.bat`. If conda itself is not found, install [Anaconda](https://www.anaconda.com/download) first.

**SHARP fails with a CUDA error**  
Switch to CPU mode in the GUI. Also check your GPU driver is up to date.

**SPZ conversion produces a warning and falls back to PLY**  
Make sure `3dgsconverter` is installed: `conda run -n sharp pip install git+https://github.com/francescofugazzi/3dgsconverter.git`

**First run is very slow**  
SHARP downloads ~500 MB of model weights on the first conversion. This is normal and only happens once.

---

## Acknowledgements

| Project | License | Role |
|---|---|---|
| [Apple ml-sharp](https://github.com/apple/ml-sharp) | [SHARP Research License](https://github.com/apple/ml-sharp/blob/main/LICENSE) | 3D reconstruction model |
| [hyperlogic/splatapult](https://github.com/hyperlogic/splatapult) | MIT | Real-time Gaussian Splat viewer |
| [nianticlabs/spz](https://github.com/nianticlabs/spz) | MIT | SPZ format C++ library |
| [francescofugazzi/3dgsconverter](https://github.com/francescofugazzi/3dgsconverter) | MIT | PLY → SPZ conversion |

---

## License

MIT — see [LICENSE](LICENSE)
