import argparse

parser = argparse.ArgumentParser()

g1 = parser.add_mutually_exclusive_group()
g1.add_argument('--a11', action='store_true')
g1.add_argument('--a12', action='store_true')

g2 = parser.add_mutually_exclusive_group1(dest='ext_group', title='usage group 2',
    description='only one of this group is allowed')
g2.add_argument('--a21', action='store_true')
g2.add_argument('--a22', action='store_true')

g5 = g2.add_usage_group(kind='not', dest='not(g51)')
g5.add_argument('--a51', action='store_false')

g3 = parser.add_usage_group(kind='any', required=True, dest='any_group', title='usage group 3',
    description='at least one of this group is required')
g3.add_argument('--a31', action='store_true')
g3.add_argument('--a32', action='store_true')

g4 = g3.add_usage_group(kind='all', required=False, dest='all(g41,g42)')
g4.add_argument('--a41', action='store_true')
g4.add_argument('--a42', action='store_true')

parser.print_usage()
parser.formatter_class = argparse.UsageGroupHelpFormatter
parser.print_usage()


args = parser.parse_args()
print(args)

argparse.UsageGroup.tree(parser)
