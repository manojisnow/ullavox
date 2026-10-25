#!/usr/bin/env python3
"""Validate publication events and derive explicit Docker/GitHub release metadata."""
import argparse
import re

REPOSITORY = 'dumanoj/ullavox'
NUMBER = r'(?:0|[1-9][0-9]*)'
VERSION = re.compile(rf'v(?P<major>{NUMBER})\.(?P<minor>{NUMBER})\.(?P<patch>{NUMBER})(?:-(?P<pre>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?')


def plan_release(tag, event, ref_type):
    """Fail closed for branch/manual events and unsupported version spellings."""
    if event != 'push' or ref_type != 'tag':
        raise ValueError('Publication requires a pushed version tag.')
    match = VERSION.fullmatch(tag)
    if not match:
        raise ValueError('Use vX.Y.Z or vX.Y.Z-prerelease; build metadata is unsupported.')
    version = tag[1:]
    if len(version) > 128:
        raise ValueError('The version exceeds Docker\'s 128-character tag limit.')
    prerelease = match['pre'] is not None
    if prerelease and any(part.isdigit() and len(part) > 1 and part.startswith('0')
                          for part in match['pre'].split('.')):
        raise ValueError('Numeric prerelease identifiers cannot have leading zeros.')
    minor = match['major'] + '.' + match['minor']
    tags = [REPOSITORY + ':' + version]
    if not prerelease:
        tags.extend([REPOSITORY + ':' + minor, REPOSITORY + ':latest'])
    return {'version': version, 'minor': minor,
            'prerelease': str(prerelease).lower(), 'stable': str(not prerelease).lower(),
            'tags': ','.join(tags)}


def validate_compose_image(plan, text):
    images = re.findall(r"^\s+image:\s*['\"]?dumanoj/ullavox:([A-Za-z0-9_.-]+)['\"]?\s*(?:#.*)?$", text, re.MULTILINE)
    if images != [plan['version']]:
        raise ValueError('The release Compose app image must match the exact version tag.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag')
    parser.add_argument('--event', required=True)
    parser.add_argument('--ref-type', required=True)
    parser.add_argument('--compose', help='Also validate the pinned release Compose image')
    args = parser.parse_args()
    try:
        plan = plan_release(args.tag, args.event, args.ref_type)
        if args.compose:
            from pathlib import Path
            validate_compose_image(plan, Path(args.compose).read_text())
    except ValueError as error:
        parser.exit(2, str(error) + '\n')
    for name, value in plan.items():
        print(name + '=' + value)


if __name__ == '__main__':
    main()
