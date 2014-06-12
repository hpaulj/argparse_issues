import argparse
parser = argparse.ArgumentParser(
        #description='this is the description',
        #epilog="This is the epilog",
        #argument_default=argparse.SUPPRESS
        formatter_class=argparse.UsageGroupHelpFormatter
        )

parser.add_argument('-v', '--verbose', help='verbose', action='store_true', default=False)

root_group = parser.add_usage_group(kind='mxg')

group_list = root_group.add_usage_group(kind='mxg')
#group_list = root_group.add_argument_group('list')
group_list.add_argument('-m', help='list only modules', action='store_const', dest='list', const='modules', default='all')
group_list.add_argument('-p', help='list only ports', action='store_const', dest='list', const='ports', default='all')
group_list.add_argument('--list', help='list only module or ports', choices=['modules','ports'], metavar='<modules/ports>', default='all')

group_simulate = root_group.add_usage_group(kind='mxg')
#group_simulate = root_group.add_argument_group('simulate')
group_simulate.add_argument('-M', help='simulate module down', nargs=1, metavar='module_name', dest='simulate')
group_simulate.add_argument('-P', help='simulate FC port down', nargs=1, metavar='fc_port_name', dest='simulate')
group_simulate.add_argument('-I', help='simulate iSCSI port down', nargs=1, metavar='iSCSI_port_name', dest='simulate')
group_simulate.add_argument('--simulate', help='simulate module or port down', nargs=1, dest='simulate')

print(parser.format_help())
args = parser.parse_args()
print(args)

"""
nesting doesn't change testing
but implementing some sort of 'title' or argument_group abitility
would make the help better
ofcourse arguments could created in argument groups, and then added to
nested groups.

nesting groups like this doesn't do anything
group_simulate._container points to root_group
but parser._mutually_exclusive_groups is shared among all groups
i.e. root_group does not have a list of its nested groups

actions added to group_simulate are added to root_group
so all 7 actions are mutulally exclusive

in this corrected formatter, 'root_group' is formatted, but not theotherss
with the UsageGroup formatter, all 3 groups are formatted (but not nested)

http://stackoverflow.com/questions/14660876/python-dependencies-between-groups-using-argparse

"""