import sys
from cx_Freeze import setup, Executable
from DragonLog import __prog_name__, __prog_desc__, __version__, __author_name__, __author_email__, __copyright__

include_files = ['DragonLog_de.qm',
                 'icons',
                 'bands.json',
                 'modes.json',
                 'cb_channels.json',
                 'README.md',
                 'README.txt',
                 'adx314.xsd',
                 'adx314generic.xsd',
                 ]

if sys.platform == 'win32':
    include_files.append('venv/Lib/site-packages/qt6_applications/Qt/plugins/platforms')
    include_files.append('venv/Lib/site-packages/qt6_applications/Qt/plugins/styles')
    base = 'Win32GUI'
else:
    base = None

build_exe_options = {
    'packages': [],
    'excludes': ['tkinter',
                 ],
    'include_files': include_files,
}

msi_data = {
    'ProgId': [
        (__prog_name__, None, None, __prog_desc__, 'IconId', None),
    ],
    'Icon': [
        ('IconId', 'icons/logo.ico'),
    ],
}

msi_sum = {
    'author': __author_name__,
    'comments': __prog_desc__,
    'keywords': 'Logging',
}

msi_ext = [
    {
        'extension': 'qlog',
        'verb': 'edit',
        'executable': 'DragonLog.exe',
        'context': 'Edit with DragonLog',
        'argument': '"%1"',
    },
]

bdist_msi_options = {
    'upgrade_code': '{7F56886F-6EFB-3808-B7DE-FE9FF862094F}',
    'data': msi_data,
    'summary_data': msi_sum,
    'extensions': msi_ext,
    'target_name': __prog_name__,
}

executables = [
    Executable('DragonLog.py',
               target_name='DragonLog',
               base=base,
               icon='icons/logo.ico',
               shortcut_name=__prog_name__,
               shortcut_dir='DesktopFolder',
               copyright=__copyright__)
]

setup(name=__prog_name__,
      version=__version__[1:].split('-')[0],
      author=__author_name__,
      author_email=__author_email__,
      license=__copyright__,
      description=__prog_desc__,
      options={
          'build_exe': build_exe_options,
          'bdist_msi': bdist_msi_options,
      },
      executables=executables)
