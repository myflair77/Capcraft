# Capcraft source and licenses

Copyright (C) 2026 JBH.

Capcraft's original application code is licensed under the GNU General Public License, version 3 (GPL-3.0-only). You may redistribute and modify it under that license. It is provided WITHOUT ANY WARRANTY, including merchantability or fitness for a particular purpose. See LICENSE for the full terms. Third-party components retain their respective licenses.

The corresponding application source for version 1.2.0, including build scripts, the editable usage guide and dependency/model manifests, is available at:

- https://github.com/myflair77/Capcraft/tree/v1.2.0
- https://github.com/myflair77/Capcraft/releases/tag/v1.2.0 (source archive)

Build instructions: DEPLOYMENT.md, build.bat, requirements-build.txt, Capcraft_v1.2.spec, installer_v1.2.iss. OCR model provenance and pinned hashes: models/ocr/manifest.json and README.md; scripts/setup_ocr.py downloads those versions. App source includes guide.html; installed builds embed it inside the Python archive rather than distributing a standalone HTML file. This is packaging, not DRM or a restriction on GPL rights.

Third-party notices are supplied under `_internal/licenses` and `_internal/vendor/licenses`. The Python inventory lists exact installed versions and source-distribution index URLs (build-only dependencies may also appear in the inventory). These notices do not relicense third-party components.

Upstream source locations for bundled components:

- Python: https://www.python.org/downloads/source/
- PyQt6, PyQt6-WebEngine and PyQt6-sip: exact-version source distributions listed in the Python inventory; https://www.riverbankcomputing.com/software/pyqt/download
- Qt 6.11.2 (QtBase, QtDeclarative, QtWebEngine, QtPositioning, QtWebChannel, QtSvg, QtTools and relevant Qt modules): https://download.qt.io/archive/qt/6.11/6.11.2/submodules/ ; https://code.qt.io/ . QtWebEngine source contains its Chromium third-party source/notices.
- ONNX Runtime: https://github.com/microsoft/onnxruntime
- RapidOCR: https://github.com/RapidAI/RapidOCR ; PaddleOCR models: https://github.com/PaddlePaddle/PaddleOCR
- Other Python components: `_internal/licenses/python-packages.json` identifies exact versions and their source indexes/project URLs.
- Browser libraries: package-lock.json and vendor/versions.json identify exact versions. vendor/licenses contains their notices; npm package metadata identifies their upstream source repositories.

No upstream library source was intentionally modified. Keep source access available for recipients of each distributed binary; an upstream URL is not a reason to remove the matching application source. Contact: myflair77@gmail.com.
