import argparse
import paraformatter
ParagraphFormatter = paraformatter.ParagraphFormatter
ParagraphFormatterML = paraformatter.ParagraphFormatterML

parser = argparse.ArgumentParser(formatter_class=ParagraphFormatter,
                                 description='''\
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
    'As with docstrings, the leading space to the text block is ignored.')
parser.add_argument('--example', help='''\
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
    'As with docstrings, the leading space to the text block is ignored.')
parser.print_help()

print('\n=================')

parser = argparse.ArgumentParser(formatter_class=ParagraphFormatterML,
                                 description='''\
    This description help text will have this first long line wrapped to
    fit the target window size so that your text remains flexible.

        1. But lines such as
        2. this that that are indented beyond the first line's indent,
        3. are reproduced verbatim, with no wrapping.
           or other formatting applied.

    The ParagraphFormatterML class will treat consecutive lines of
    text as a single block to rewrap.  So there is no need to end lines
    with backslashes to create a single long logical line.

    As with docstrings, the leading space to the text block is ignored.''')

parser.add_argument('--example', help='''\
    This argument's help text will have this first long line wrapped to
    fit the target window size so that your text remains flexible.

        1. But lines such as
        2. this that that are indented beyond the first line's indent,
        3. are reproduced verbatim, with no wrapping.
           or other formatting applied.

    The ParagraphFormatterML class will treat consecutive lines of
    text as a single block to rewrap.  So there is no need to end lines
    with backslashes to create a single long logical line.

    As with docstrings, the leading space to the text block is ignored.''')
parser.print_help()

print('\n=================')

WrapFormatter = argparse.WrapHelpFormatter
description = ('''\
This description help text will have this first long line wrapped to \
fit the target window size so that your text remains flexible.

    1. But lines such as
    2. this that are indented beyond the first line's indent,
    3. are reproduced with indenting; indentation is not preserved \
       when wrapping.

You must use backslashes at the end of lines to indicate that you \
want the text to wrap instead of preserving the newline. '''
'Alternatively you can avoid using backslashes by using the '
'fact that Python concatenates adjacent string literals as '
'we are doing now.\n\n'
''
'As with docstrings, the leading space to the text block is ignored.')

example_help = ('''\
This argument's help text will have this first long line wrapped to \
fit the target window size so that your text remains flexible.

    1. But lines such as
    2. this that that are indented beyond the first line's indent,
    3. are reproduced verbatim, with no wrapping. \
or other formatting applied.

You must use backslashes at the end of lines to indicate that you \
want the text to wrap instead of preserving the newline. '''
'Alternatively you can avoid using backslashes by using the '
'fact that Python concatenates adjacent string literals as '
'we are doing now.\n\n'
''
'As with docstrings, the leading space to the text block is ignored.')

parser = argparse.ArgumentParser(formatter_class=WrapFormatter,
                                 description=description)
parser.add_argument('--example', help=example_help)
parser.print_help()
