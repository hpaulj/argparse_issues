import sys
from argparse import ArgumentParser, Normal, Pre, NoWrap, PreWrap, \
    PreLine, Py3FormatHelpFormatter

longtxt="""\
Body of the text.
1 - point one
2 - second point with
    contination
3 - third line

"""

description = '%(prog)s description'
description = PreLine('  %(prog)s Indented<br>\n\t<tab>more line<br>\n    with white    space')
epilog = Pre('Epilog: No wrap line %(prog)s<br>\n\tNext line\n \n')
usage = None

parser = ArgumentParser(prog='PROG', usage=usage,
    description=description, epilog=epilog,
    formatter_class=Py3FormatHelpFormatter
    )

parser.add_argument('-v', '--version', action='version', version='%(prog)s 0.0.1')
parser.add_argument('-t', '--test', action='store_true', help='test the white-space styles')

grp = parser.add_argument_group(title='Test Group',
    description=Pre('Group for testing<br>\n  the Pre indent')
    )

grp.add_argument('-l','--longversion', action='version', version=Pre(longtxt),
    help=Pre('writes to {prog:_^10} stderr,\n\tredirect with `2> temp.txt`'))
grp.add_argument('positional', help='short help line;\nignored nl, default: {default}', nargs='?',
    default=100)
grp.add_argument('--foo', default='DEFAULT', help='default: {%(default)s}')
grp.add_argument('--bar', default='DEFAULT', help='default: {{{default}}}')
grp.add_argument('--choice', choices=['one','two','three'],
    help='with choices: {%(choices)s}, default:%(default)s')
grp.add_argument('--prewrap', help=PreWrap("""\
This one very long line xxxxxxxxxxxxx xxxxxxxxxxxxxx xxxxxxxxxx  xxxxxxxx xxxxxxxx
Second line
"""))



formatter = parser._get_formatter()
formatter.add_text(Pre('test text'))
txt = formatter._root_section.format_help()
print(repr(txt))

args = parser.parse_args()

print(args)

text = ("""\
This is a line       after spaces.
Second line\tafter tab.
  1 - two
  2 - three %(numb)s
  3 - a format test {}

""")
if args.test:
    print('\n')
    print(repr(text))
    for fn in [Normal, Pre, NoWrap, PreWrap, PreLine]:
        text = fn(text).format('DATA')._str_format(dict(numb=300))
        print(type(text))
        print(fn.__name__, ':', Normal(fn.__doc__)._fill_text(80, ''))
        print(text._split_lines(width=30))
        newtext = text._fill_text(width=30, indent='.... ')
        print(type(newtext))
        print(newtext)

"""
http://bugs.python.org/issue12284 - examples in epilog, a good use for Pre
http://bugs.python.org/issue13023 - epilog w/br and add-defaults
     can do with subclass that inherits from 2 formatters
     zbybz: Yeah, adding a formatter instance seems overkill for the usual case of wanting to preserver formatting of the epilog.
http://bugs.python.org/issue9399 - 'write' license
     eg use version with a Pre text
http://bugs.python.org/issue13923
     It would be really nice to have a formatter for argparse that would respect explicit new lines while still wrapping lines otherwise.
     like white-space:pre-wrap?
http://bugs.python.org/issue12806 - hybrid formatter - i.e. apply wrap to lines
     but keep 'paragraph' breaks


"""