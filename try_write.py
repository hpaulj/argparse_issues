import argparse
import sys
NoWrap = argparse.NoWrap

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

# user defined write action
class WriteAction(argparse.Action):

    def __init__(self,
                 option_strings,
                 message,
                 file=sys.stdout,
                 dest=argparse.SUPPRESS,
                 default=argparse.SUPPRESS,
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
        self.file.write(self.message)
        self.file.write('\n')
        parser.exit()

# simpler action adapted from documentation Foo
class SimpleAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        print('Custom message for %s: %s'%(parser.prog, self.const))
        parser.exit()

description = '%(prog)s description'
epilog = NoWrap('Epilog: No wrap line %(prog)s\n\tNext line\n \n')

usage = 'This is a usage line with newlines\n\t'
usage += ' PROG [-h] [-l] [-v] [-m] [-n] [-c]'

parser = argparse.ArgumentParser(prog='PROG', usage=usage,
    description=description, epilog=epilog)

g = parser.add_argument_group(title='test group',
    description=NoWrap('This is group\n  testing indent'))

g.add_argument('-l', "--license", action="write", message=bsdlicense,
    help="show %(prog)s license and exit")

g.add_argument('-v', '--version', action='version', version='%(prog)s 0.0.1')

g.add_argument('-m', '--message', action=WriteAction, message=bsdlicense)

g.add_argument('-n', '--noise', action='count', default=0,
    help=NoWrap('repeatable counts\n\tsecond help line; default: %(default)s'))

g.add_argument('-s', '--simple', nargs=0, action=SimpleAction, const=bsdlicense)

parser.add_argument('-i','--info', action='version', version=NoWrap(bsdlicense))
# ../python3 try_write.py -i 2> temp.txt

parser.add_argument('-c','--call', action='call',
    callback=lambda: sys.stdout.write(bsdlicense))

args = parser.parse_args()

if args.noise:
    print('%s: message based on a count argument, %s'%(parser.prog, args.noise))
    if args.noise>2:
        parser.exit(message=bsdlicense)
