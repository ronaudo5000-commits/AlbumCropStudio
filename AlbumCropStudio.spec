# -*- mode: python ; coding: utf-8 -*-

from importlib.metadata import distribution
from pathlib import Path


# インストール済みpypdfium2のライセンス文書を取得
pdfium_package = distribution("pypdfium2")

pdfium_license_dir = Path(
    pdfium_package.locate_file(
        f"pypdfium2-{pdfium_package.version}.dist-info/licenses"
    )
)

if not pdfium_license_dir.is_dir():
    raise FileNotFoundError(
        f"PDFiumライセンスフォルダが見つかりません: "
        f"{pdfium_license_dir}"
    )


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
datas=[
    (
        str(pdfium_license_dir),
        'licenses/pypdfium2',
    ),
    (
        'resources/app_icon.png',
        'resources',
    ),
    (
        'resources/splash.png',
        'resources',
    ),
    (
        'translations/albumcrop_en.qm',
        'translations',
    ),
    (
        'translations/albumcrop_zh_TW.qm',
        'translations',
    ),
],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AlbumCropStudio',
    icon='resources/app_icon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AlbumCropStudio',
)
