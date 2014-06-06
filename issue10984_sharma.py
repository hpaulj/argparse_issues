import argparse
usage = 'prog [ --conflicter | [ --opt1 ] [ --opt2 ] ]'
parser = argparse.ArgumentParser(usage=usage)
conflicter = parser.add_argument("--conflicter", action='store_true')
opt1 = parser.add_argument("--opt1", action='store_true')
opt2 = parser.add_argument("--opt2", action='store_true')

@parser.usagetest
def test(parser, seen_actions, *args):
    if conflicter in seen_actions:
        # if 0<len(seen_actions.intersection([opt1, opt2])):
        if opt1 in seen_actions or opt2 in seen_actions:
            parser.error('--conflicter cannot be used with --opt1 or --opt2')
try:
    print(parser.parse_args())
except SystemExit:
    pass



parser = argparse.ArgumentParser(formatter_class=argparse.MultiGroupHelpFormatter)
g1 = parser.add_nested_group(kind='mxg')
conflicter = g1.add_argument("--conflicter", action='store_true')
g2 = g1.add_nested_group(kind='any', dest='(opt1 or opt2)',
    # parens=['or(',')'],
    joiner=' or ',
    )
opt1 = g2.add_argument("--opt1", action='store_true')
opt2 = g2.add_argument("--opt2", action='store_true')
print(parser.parse_args())