# DragonLog (c) 2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/
"""Writes a file with list of all available contests as Markdown if a file name is given.
Else prints out the content."""

import sys

from . import build_contest_list

if len(sys.argv) > 1:
    with open(sys.argv[1], 'w', encoding='UTF-8') as cf:
        cf.write(build_contest_list())
else:
    print(build_contest_list())
