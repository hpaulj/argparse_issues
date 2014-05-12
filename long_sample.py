import argparse

parser = argparse.ArgumentParser(prog='LongName',
    prefix_chars='-+',
    formatter_class=argparse.ListProgHelpFormatter)
parser.add_argument('--foobar', nargs=6, required=True)
parser.add_argument('positional', nargs='+', metavar='FOO')
parser.add_argument('--testing', nargs='*', metavar=('A','B'), required=True)

print('subparsers')
sp = parser.add_subparsers()
print(sp.parser_args)
sp_a = sp.add_parser('cmda',
    formatter_class=argparse.ListProgHelpFormatter)
# should subparsers inherit formatter_class?
sp_a.add_argument('--cmdafoo')
sp_a.add_argument('cmdpos', nargs='+')
sp_b = sp.add_parser('cmdb', prog='cmdb usage')
sp_c = sp.add_parser('cmdc')
print(sp._prog_prefix)
print(sp_a.prog, type(sp_a.prog))
print('main')
parser.print_usage()
print('cmda')
sp_a.print_usage()
print('cmdb')
sp_b.print_usage()
print('cmdc')
print(sp_c.formatter_class)
parser.parse_args(['xx','cmdc','-h'])
