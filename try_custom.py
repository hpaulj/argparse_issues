import argparse

formatter = argparse.UsageGroupHelpFormatter
p = argparse.ArgumentParser(formatter_class=formatter)
g1 = p.add_usage_group(kind='xor', dest='g1')
g1.add_argument('--a1', action='store_true')

g2 = p.add_usage_group(kind='or', dest='g2')
g2.add_argument('--a2', action='store_false')
g2.add_usage_group(g1)

g3 = argparse.UsageGroup(p, kind='or', dest='g3')
g3.add_argument('--a3')
g1.add_argument_group(g3)
# a predefined group can be nested
# but the parser.add... does not accept a group
g4 = g1.add_usage_group(kind='and', dest='g4')
g4.add_argument('--a4')

class MyGroup(argparse._NotUsageGroup):
    pass
g5 = g4.add_usage_group(kind=MyGroup)
g5.add_argument('--a5')
print(p._usage_groups)

p.print_help()

# 'kind' is like 'action' and 'type' - an object or string for lookup in registries
# allows same sort of customization
# main diff is in 'testfn'
# curious custom test - that exactly 2 of the arg is given
# move the formatting to UG, with option of customization
# beyond the parens and joiner mechanism
# _format_group_usage  (biggish fn)


print()
argparse.UsageGroup.tree(p)

#