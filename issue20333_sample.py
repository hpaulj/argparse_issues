import argparse

# need to test subparser usage with a MXG in main


# create the top-level parser
parser = argparse.ArgumentParser(prog='PROG')
parser.add_argument('XXX')
parser.add_argument('--file', help='A filename', required=True)
parser.add_argument('--foo', help='Optional optional')
subparsers = parser.add_subparsers(help='sub-command help',
    #prog='PROG --file PHAIL' # define usage prefix
    )

# create the parser for the "a" command
parser_a = subparsers.add_parser('a', help='a help',
    prog='PROG [-h] --file FILE a' # usage prefix for this specific command
    )
parser_a.add_argument('bar', type=int, help='bar help')

# create the parser for the "b" command
parser_b = subparsers.add_parser('b', help='b help')
parser_b.add_argument('--baz', choices='XYZ', help='baz help')

parser.add_argument('--post')


print('prog_prefix:', subparsers._prog_prefix)
print('a prog:', parser_a.prog)
print('b prog:', parser_b.prog)

print(parser.format_help())
print(parser_a.format_help())
print(parser_b.format_help())
"""
prog_prefix: PROG --file FILE XXX
a prog: PROG [-h] --file FILE a
b prog: PROG --file FILE XXX b


"""
#parser.parse_args()
"""
3 possible fixes:

- define the usage prefix, 'prog' in the 'add_subparses' command
- define the usage 'prog' in the individual subparser definitions
- modify 'add_subparsers' to include 'required' optionals when it
    generates the usage prefix.  Currently it just uses 'positionals'.

Note that 'parser' arguments defined after the 'add_subparsers' command
do not appear in the subparse usage.

test_argparse does not exercise this feature very much

Sample output from this script:

1331:~/mypy/argdev/issue20333$ ../python3 sample.py
usage: PROG [-h] --file FILE [--foo FOO] [--post POST] XXX {a,b} ...

positional arguments:
  XXX
  {a,b}        sub-command help
    a          a help
    b          b help

optional arguments:
  -h, --help   show this help message and exit
  --file FILE  A filename
  --foo FOO    Optional optional
  --post POST

usage: PROG [-h] --file FILE a [-h] bar

positional arguments:
  bar         bar help

optional arguments:
  -h, --help  show this help message and exit

usage: PROG --file FILE XXX b [-h] [--baz {X,Y,Z}]

optional arguments:
  -h, --help     show this help message and exit
  --baz {X,Y,Z}  baz help

"""