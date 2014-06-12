import argparse
usage = 'PROG [-h] (-o FILE | (-O DIR & (-p PATTERN | -s SUFFIX)))'
#usage = None
parser = argparse.ArgumentParser(prog='PROG', usage=usage)
g1 = parser.add_usage_group(dest='FILE or DIR', kind='mxg', required=True)
a_file= g1.add_argument("-o", "--outfile", metavar='FILE')
g2 = g1.add_usage_group(dest='DIR and PS', kind='inc')
a_dir = g2.add_argument("-O", "--outdir", metavar='DIR')
g3 = g2.add_usage_group(dest='P or S',
    kind='mxg',
    parens='()',
    # joiner=' || ',
    )
a_pat = g3.add_argument("-p", "--outpattern", metavar='PATTERN')
a_suf = g3.add_argument("-s", "--outsuffix", metavar='SUFFIX')

# parser.print_help() - error because nesting group does not have help
# testing for group.help is not SUPPRESS
parser.print_usage()


for test in [['-o FILE', ''],
             ['-O DIR -p PAT', ''],
             ['-O DIR -s SUF', ''],
             ['', 'require FILE or DIR'],
             ['-O DIR', 'DIR requires'],
             ['-o FILE -p PAT', 'FILE cannot'],
             ['-O DIR -o FILE', 'FILE cannot'],
             ['-O DIR -p PAT -s SUF', 'cannot have both'],
             # ['-o FILE1 -o FILE2', 'only one'],
             ['-o FILE -O DIR -s SUF', 'only one of'],
             ]:
    print(test[0])
    try:
        print(parser.parse_args(test[0].split()))
    except SystemExit:
        assert len(test[1])>0
        pass
    print()

parser.formatter_class=argparse.UsageGroupHelpFormatter
parser.print_usage()
parser.usage =None
parser.print_usage()

# error msg should include group name (dest)
# maybe a custom error string