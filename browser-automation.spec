# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files

# apify: только данные
apify_datas = collect_data_files('apify_fingerprint_datapoints')
apify_binaries, apify_hiddenimports = [], []

def _no_dist_info(datas):
    return [(s, d) for s, d in datas if '.dist-info' not in d and '.egg-info' not in d]

# camoufox и language_tags (без dist-info — ломает распаковку)
camoufox_datas, camoufox_binaries, camoufox_hiddenimports = collect_all('camoufox')
camoufox_datas = _no_dist_info(camoufox_datas)
lang_datas, lang_binaries, lang_hiddenimports = collect_all('language_tags')
lang_datas = _no_dist_info(lang_datas)

a = Analysis(
    ['src/browser_automation/main.py'],
    pathex=['src'],
    binaries=apify_binaries + camoufox_binaries + lang_binaries,
    datas=apify_datas + camoufox_datas + lang_datas,
    hiddenimports=apify_hiddenimports + camoufox_hiddenimports + lang_hiddenimports,
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
    a.binaries,
    a.datas,
    [],
    name='browser-automation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
