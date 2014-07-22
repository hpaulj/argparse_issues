import sys
from argparse import ArgumentParser, SUPPRESS, Action
from argparse import RawDescriptionHelpFormatter

class WriteAction(Action):

    def __init__(self,
                 option_strings,
                 message,
                 file=None,
                 dest=SUPPRESS,
                 default=SUPPRESS,
                 help='show %(prog)s message'):
        super(WriteAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)
        self.message = message
        self.file = file

    def __call__(self, parser, namespace, values, option_string=None):
        file = (self.file if self.file is not None else sys.stdout)
        print(self.message, file=self.file) # eric.araujo
        # an alternative is to pass message through the formatter
        # making it just like _VersionAction (except for the file choice)
        parser.exit()

# simpler action adapted from documentation Foo
class SimpleAction(Action):

    def __call__(self, parser, namespace, values, option_string=None):
        print('Custom message for %s: %s'%(parser.prog, self.const))
        parser.exit()

class CallableAction(Action):

    def __init__(self,
                 option_strings,
                 dest,
                 callback,
                 nargs = 0,
                 **kwargs):
        super(CallableAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            **kwargs)
        if not callable(callback):
            raise ValueError('%r is not callable' % (callback,))
        self.func = callback

    def __call__(self, *args, **kwargs):
        # should this insulate func from all the normal arguments?
        self.func()


bsdlicense="""\
Copyright (c) <year>, <copyright holder>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:
   This product includes software developed by the <organization>.
4. Neither the name of the <organization> nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

"""
def makeRaw():
    parser.formatter_class=RawDescriptionHelpFormatter

parser = ArgumentParser(prog='PROG')
parser.register('action', 'write', WriteAction)

parser.add_argument('--raw', action=CallableAction,
    callback=makeRaw,
    help='change formatter class to RAW; turns off version wrapping')
# --raw -i  displays license without wrapping

parser.add_argument('-v', '--version', action='version', version='%(prog)s 0.0.1')

parser.add_argument('-l', "--license", action="write", message=bsdlicense,
    help="show %(prog)s license and exit")

parser.add_argument('-m', '--message', action=WriteAction, message=bsdlicense)

parser.add_argument('-s', '--simple', nargs=0, action=SimpleAction, const=bsdlicense)

parser.add_argument('-r', '--repeat', action='count', default=0,
    help='may repeat option to get more detailed information')

parser.add_argument('-i','--info', action='version', version=bsdlicense,
    help='writes to stderr, redirect with `2> temp.txt`')

parser.add_argument('-c','--call', action=CallableAction,
    callback=lambda: sys.stdout.write(bsdlicense),
    help='option with a simple, no argument, callback')

args = parser.parse_args()

if args.repeat:
    print('%s: repeat count was %s'%(parser.prog, args.repeat))
    if args.repeat==2:
        formatter = parser._get_formatter()
        formatter.add_text(bsdlicense)
        wrappedtext = formatter.format_help()
        parser.exit(wrappedtext)
    elif args.repeat>2:
        parser.exit(message=bsdlicense)
