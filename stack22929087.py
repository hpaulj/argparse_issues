import argparse

parser = argparse.ArgumentParser()
sp = parser.add_subparsers()#dest='cmd')
sp.required = True
spp = sp.add_parser('cmd1')
act_g = spp.add_argument('-g')
act_wid = spp.add_argument('--wid')
act_w1 = spp.add_argument('--w1')
act_w2 = spp.add_argument('--w2')

grp2 = spp.add_nested_group(kind='mxg', required=True)  # 'exc'
grp2.add_argument(act_wid)

grp1 = grp2.add_nested_group(kind='inc', dest='w1&w2')
grp1.add_argument(act_w1)
grp1.add_argument(act_w2)
# don't know how to express the not -g test with groups

"""
desired behavior
-w1 and -w2 always appear together
-wid and (-w1 -w2) are mutually exclusive, but one or the other is required
-g is optional; if it is not specified only (-w1 -w2) can appear, but not -wid


inc1 = inclusive(act_w1, act_w2)
required exclsive(act_wid, inc1)
exclusive(not act_g, act_wid)
"""
'''
@spp.crosstest
def test1(spp, seen_actions, *args):
    if 1==len({act_w1, act_w2}.intersection(seen_actions)):
        parser.error('-w1 and -w2 always appear together')
@spp.crosstest
def test2(spp, seen_actions, *args):
    if act_wid in seen_actions:
        if act_w1 in seen_actions or act_w2 in seen_actions:
            parser.error('-wid and (-w1 -w2) are mutually exclusive')
    elif act_w1 not in seen_actions:
        parser.error('wid or (w1 and w2) required')
@spp.crosstest
def test3(spp, seen_actions, *args):
    if act_g not in seen_actions and act_wid in seen_actions:
        parser.error('not g, so not wid')
'''
args = parser.parse_args()
print(args)

"""
with [], error is
usage: stack22929087.py [-h] {cmd1} ...
stack22929087.py: error: the following arguments are required: cmd
should that be the dest, or the choices {cmd1}?
choices are given if dest is not specified
that doesn't see quite right

how to represent group in error msg: '', dest, usage?

what order should groups be tested? can it be controlled

with wid AND w1, error msg the inclusive group
but i'd give priority to the excl - ie. wid with anything else

"""