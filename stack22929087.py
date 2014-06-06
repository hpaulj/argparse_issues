import argparse
from functools import partial

parser = argparse.ArgumentParser(formatter_class=argparse.MultiGroupHelpFormatter)
sp = parser.add_subparsers()#dest='cmd')
sp.required = True
spp = sp.add_parser('cmd1', formatter_class=argparse.MultiGroupHelpFormatter)
act_g = spp.add_argument('-g')
act_wid = spp.add_argument('--wid')
act_w1 = spp.add_argument('--w1')
act_w2 = spp.add_argument('--w2')

grp2 = spp.add_usage_group(kind='mxg', required=True)  # 'exc'
grp2.add_argument(act_wid)

grp1 = grp2.add_usage_group(kind='inc', dest='w1&w2')
grp1.add_argument(act_w1)
grp1.add_argument(act_w2)
# don't know how to express the not -g test with groups
# can still use decorated cross_test
def test_this_group(parser, seen_non_default_actions, *vargs, **kwargs):
    seen_actions = set(seen_non_default_actions)
    if act_g not in seen_actions and act_wid in seen_actions:
        parser.error('group3 error')

grp3 = spp.add_usage_group(testfn=test_this_group, usage='(if not -g then not -wid)')
print(grp3)
"""
grp3.add_argument(act_g)
grp3.add_argument(act_wid)
#grp3.add_argument(grp1)
grp3.add_usage_group(grp1)
if group testfn directly references the actions, and the usage is defined
then nothing needs to be added to the group

there isn't an easy way for such a fn to references the group's _group_actions
or for that matter to reference the group itself
it can't refer to the group before the group is created
"""

@spp.usagetest
def test3(spp, seen_actions, *args):
    if act_g not in seen_actions and act_wid in seen_actions:
        spp.error('not g, so not wid')

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
@spp.usagetest
def test1(spp, seen_actions, *args):
    if 1==len({act_w1, act_w2}.intersection(seen_actions)):
        parser.error('-w1 and -w2 always appear together')
@spp.usagetest
def test2(spp, seen_actions, *args):
    if act_wid in seen_actions:
        if act_w1 in seen_actions or act_w2 in seen_actions:
            parser.error('-wid and (-w1 -w2) are mutually exclusive')
    elif act_w1 not in seen_actions:
        parser.error('wid or (w1 and w2) required')
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