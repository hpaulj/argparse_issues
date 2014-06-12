"""
parser = argparse.ArgumentParser(description='Log archiver arguments.')
parser.add_argument('-process', action='store_true')
parser.add_argument('-upload',  action='store_true')
args = parser.parse_args()
The program is meaningless without at least one parameter. How can I configure
argparse to force at least one parameter to be chosen?
"""

import argparse

parser = argparse.ArgumentParser(prog='PROG', description='Log archiver arguments.')
group = parser.add_usage_group(kind='any', required=True,
    title='possible actions (at least one is required)')
group.add_argument('-p', '--process', action='store_true')
group.add_argument('-u', '--upload',  action='store_true')
args = parser.parse_args()
print(args)

"""
usage: PROG [-h] (-p | -u)
PROG: error: some of the arguments process upload is required
- error needs to bracket the choices

"""