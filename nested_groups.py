import argparse

parser = argparse.ArgumentParser(prog="MXG", formatter_class=argparse.UsageGroupHelpFormatter)
g1 = parser.add_argument_group('group1')
g2 = parser.add_argument_group('group2')
g1x1 = g1.add_mutually_exclusive_group()
g1x1.add_argument('--f1')
g1x1.add_argument('--g1')

g2x1 = g2.add_mutually_exclusive_group()
g2x1.add_argument('--f2')
g2x1.add_argument('--g2')

print(parser.format_help())
#print(parser._mutually_exclusive_groups)
#print(g1._mutually_exclusive_groups)
#print(g2._mutually_exclusive_groups)
print(parser.parse_args([]))
print('')

print('nesting behaving like mxg')
parser = argparse.ArgumentParser(prog="NG", formatter_class=argparse.UsageGroupHelpFormatter)
g1x1 = parser.add_usage_group(kind='inc')
f1Action = g1x1.add_argument('--f1')
g1x1.add_argument('--g1')

g2x1 = parser.add_usage_group(kind='mxg', required=True)
f2Action = g2x1.add_argument('--f2')
g2x1.add_argument('--g2')
#g1x1.add_argument(f2Action)
parser.print_usage()
print(parser.parse_args(['--g2','bar']))
print(parser.parse_args('--f1 foo --g2 bar --g1 baz'.split()))
print('')

expected_usage = """EXPECT [-h]  [group11] [--f1 F1 | foo | [--f2 F2 & --g2 G2] | [--f3 F3 | --g3 G3]]"""
parser = argparse.ArgumentParser(prog="Nesting", formatter_class=argparse.UsageGroupHelpFormatter)
g1 = parser.add_usage_group(kind='mxg', dest='nest1')
g1x1 = g1.add_argument('--f1')
g1x2 = g1.add_argument('foo', nargs='?')
"""
g11 = parser.add_usage_group(dest='nest2') # another at 1st level
g11.add_argument('-a')
g11.add_argument('-b')
"""
g2 = g1.add_usage_group(kind='inc', dest='inc2')
g2x1 = g2.add_argument('--f2')
g2x2 = g2.add_argument('--g2')
g3 = g1.add_usage_group(kind='mxg', dest='mxg3',title='test')
g3x1 = g3.add_argument('--f3')
g3x2 = g3.add_argument('--g3')
#g3x2 = g3.add_argument(g2x2) # works but produces conflict
print(expected_usage)
parser.print_help()
print(parser._registries['usage_tests'].keys())
print(parser.parse_args(['foo']))
print(parser.parse_args('--f2 bar --g2 foo'.split()))
if g2.kind=='any':
    g2.required = True
    print(parser.parse_args('--f2 bar'.split()))

# testing - rewrite M_x_g to nesting and run test_argparse
#   working

# do the add_argument(action) trick to MXG's (alt to adding actions during creation; issue?)
# move the DelayedValue call to end of parse_known_args (out of _p_k_a)

# make nest groups usage formatting work

# groups should specify parens as well as joiner

