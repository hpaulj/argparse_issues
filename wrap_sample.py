import argparse
import textwrap as _textwrap

def myfill(text, **kwargs):
    # apply textwrap to each line individually
    lines = text.splitlines()
    lines =[_textwrap.fill(line, **kwargs) for line in lines]
    return '\n'.join(lines)

description = """\
This description help text with long lines.  Note the space and \
backslash to continue lines.

1. Points work
2. 2nd point
    1. Indented points as well
    2. but be wary of wrapping

It is simpler if we avoid the use of leading spaces.
"""

epilog = """Epilog can also be wrapped in a custom way.
    a) point one
    b) point two
"""

arg_help = '''\
Help text may also be wrapped
- be extra carefull about wrapping
- with the narrow help text

'''
epilog = myfill(epilog, width=40,
  initial_indent='    ',
  subsequent_indent='    ....')

p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
    description=myfill(description),
    epilog=epilog)
p.add_argument('--foo', help=myfill(arg_help, width=50))
p.add_argument('bar', help='positional argument help')
print(p.format_help())

"""
1922:~/mypy/argdev/arggit$ ../python3 wrap_sample.py
usage: wrap_sample.py [-h] [--foo FOO] bar

This description help text with long lines.  Note the space and
backslash to continue lines.

1. Points work
2. 2nd point
    1. Indented points as well
    2. but be wary of wrapping

It is simpler if we avoid the use of leading spaces.

positional arguments:
  bar         positional argument help

optional arguments:
  -h, --help  show this help message and exit
  --foo FOO   Help text may also be wrapped
              - be extra carefull about wrapping
              - with the narrow help text

    Epilog can also be wrapped in a
    ....custom way.
        a) point one
        b) point two

"""