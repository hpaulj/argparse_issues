# http://bugs.python.org/issue12806, http://bugs.python.org/file22977/argparse_formatter.py

import argparse
import re
import textwrap
import os, shutil
os.environ['COLUMNS'] = str(shutil.get_terminal_size().columns)

import preformat
Hanging = preformat.Hanging
preformat = preformat.preformat
from functools import partial
Hanging = partial(Hanging, header_indent=6)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog='PROG',
                                     description=preformat('''\
        This description help text will have this first long line wrapped to
        fit the target window size so that your text remains flexible.

            1. But lines such as
            2. this that that are indented beyond the first line's indent,
            3. are reproduced verbatim, with no wrapping or other formatting applied.

        The ParagraphFormatterML class will treat consecutive lines of
        text as a single block to rewrap.  So there is no need to end lines
        with backslashes to create a single long logical line.

        As with docstrings, the leading space to the text block is ignored.''',
        indent_style=Hanging))

    a = parser.add_argument('--example', help=preformat('''\
        This argument's help text will have this first long line wrapped to
        fit the target window size so that your text remains flexible.

            1. But lines such as
            2) this that are indented beyond the first line's indent,
            - are reproduced verbatim, with no wrapping or other formatting applied.

        The ParagraphFormatterML class will treat consecutive lines of
        text as a single block to rewrap.  So there is no need to end lines
        with backslashes to create a single long logical line.

        As with docstrings, the leading space to the text block is ignored.''',
        indent_style=Hanging))

    parser.print_help()

"""
 description
split_lines with help

''.splitlines() => []
' '.splitlines() => [' ']
textwrap.wrap(' ',drop_whitespace=False) => [' ']

textwrap.wrap(' ',drop_whitespace=True) ==> []


"""