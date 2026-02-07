# PyInstaller spec file for building standalone binaries.
# Build on each target OS separately.

# pylint: disable=all

hiddenimports = [
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebEngineCore",
]

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "PyQt5",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "PyQt5.QtWebEngineWidgets",
        "PyQtWebEngine",
        "PyQtWebEngine.QtWebEngineWidgets",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="gpx-animator",
    debug=False,
    strip=False,
    upx=True,
    console=False,
)
