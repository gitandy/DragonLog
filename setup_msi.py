import sys
from cx_Freeze import setup, Executable
from dragonlog.DragonLog import __prog_name__, __prog_desc__, __version__, __author_name__, __author_email__, __copyright__


base = 'Win32GUI'

build_exe_options = {
    'packages': ['dragonlog'],
    'excludes': ['tkinter', 
                 'unittest',
                 ],
    'zip_include_packages': ["encodings", "PyQt6"]
}

msi_data = {
    'ProgId': [
        (__prog_name__, None, None, __prog_desc__, 'IconId', None),
    ],
    'Icon': [
        ('IconId', 'dragonlog/icons/logo.ico'),
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
    'upgrade_code': '{D6D9A26C-4DFC-46B3-905D-B556D091B62B}',
    'data': msi_data,
    'summary_data': msi_sum,
    'extensions': msi_ext,
    'target_name': __prog_name__,
}

executables = [
    Executable('main.py',
               target_name='DragonLog',
               base=base,
               icon='dragonlog/icons/logo.ico',
               shortcut_name=__prog_name__,
               shortcut_dir='DesktopFolder',
               copyright=__copyright__)
]

setup(options={
          'build_exe': build_exe_options,
          'bdist_msi': bdist_msi_options,
      },
      executables=executables)
