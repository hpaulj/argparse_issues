# http://bugs.python.org/issue12806, http://bugs.python.org/file22977/argparse_formatter.py

import argparse
import re
import textwrap
import os, shutil
os.environ['COLUMNS'] = str(shutil.get_terminal_size().columns)

from preformat import preformat

print(preformat('____\n_____\n\n____'))
print(preformat('____\n_____\n\n____')._split_lines(80))
print(preformat('____\n_____\n\n____')._fill_text(80,''))

if __name__ == '__main__':
    """
    parser = argparse.ArgumentParser(prog='PROG',
                                     description=Para('''\
        This description help text will have this first long line wrapped to\
        fit the target window size so that your text remains flexible.

            1. But lines such as
            2. this that that are indented beyond the first line's indent,
            3. are reproduced verbatim, with no wrapping.
               or other formatting applied.

        You must use backslashes at the end of lines to indicate that you\
        want the text to wrap instead of preserving the newline. '''
        'Alternatively you can avoid using backslashes by using the '
        'fact that Python concatenates adjacent string literals as '
        'we are doing now.\n\n'
        ''
        'As with docstrings, the leading space to the text block is ignored.'))
    parser.add_argument('--example', help=Para('''\
        This argument's help text will have this first long line wrapped to\
        fit the target window size so that your text remains flexible.

            1. But lines such as
            2. this that that are indented beyond the first line's indent,
            3. are reproduced verbatim, with no wrapping.
               or other formatting applied.

        You must use backslashes at the end of lines to indicate that you\
        want the text to wrap instead of preserving the newline. '''
        'Alternatively you can avoid using backslashes by using the '
        'fact that Python concatenates adjacent string literals as '
        'we are doing now.\n\n'
        ''
        'As with docstrings, the leading space to the text block is ignored.'))

    parser.print_help()
    """

    parser = argparse.ArgumentParser(prog='PROG',
                                     description=preformat('''\
        This description help text will have this first long line wrapped to
        fit the target window size so that your text remains flexible.

            1. But lines such as
            2. this that that are indented beyond the first line's indent,
            3. are reproduced verbatim, with no wrapping.
               or other formatting applied.

        The ParagraphFormatterML class will treat consecutive lines of
        text as a single block to rewrap.  So there is no need to end lines
        with backslashes to create a single long logical line.

        As with docstrings, the leading space to the text block is ignored.'''))

    parser.add_argument('--example', help=preformat('''\
        This argument's help text will have this first long line wrapped to
        fit the target window size so that your text remains flexible.

            1. But lines such as
            2. this that that are indented beyond the first line's indent,
            3. are reproduced verbatim, with no wrapping.
               or other formatting applied.

        The ParagraphFormatterML class will treat consecutive lines of
        text as a single block to rewrap.  So there is no need to end lines
        with backslashes to create a single long logical line.

        As with docstrings, the leading space to the text block is ignored.'''))
    parser.print_help()

"""
why blank line between paragraphs in description
but not in help?
fill_lines used with description
split_lines with help

''.splitlines() => []
' '.splitlines() => [' ']
textwrap.wrap(' ',drop_whitespace=False) => [' ']

textwrap.wrap(' ',drop_whitespace=True) ==> []


"""