"""Publication regressions: stable aliases must never escape to prereleases."""
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_policy import plan_release, validate_compose_image


class ReleasePolicyTests(unittest.TestCase):
    def plan(self, tag):
        return plan_release(tag, 'push', 'tag')

    def test_stable_publishes_exact_minor_and_latest(self):
        for tag in ['v1.8.0', 'v1.8.1', 'v0.0.0']:
            with self.subTest(tag=tag):
                plan = self.plan(tag)
                version = tag[1:]
                minor = '.'.join(version.split('.')[:2])
                self.assertEqual(plan['tags'].split(','), [f'dumanoj/ullavox:{version}', f'dumanoj/ullavox:{minor}', 'dumanoj/ullavox:latest'])
                self.assertEqual(plan['stable'], 'true')
                self.assertEqual(plan['prerelease'], 'false')

    def test_prereleases_never_publish_stable_aliases(self):
        for tag in ['v1.8.0-rc.1', 'v2.0.0-beta', 'v1.8.1-0', 'v1.8.0-0alpha', 'v1.8.0-dev-build.2']:
            with self.subTest(tag=tag):
                plan = self.plan(tag)
                self.assertEqual(plan['tags'], 'dumanoj/ullavox:' + tag[1:])
                self.assertEqual(plan['stable'], 'false')
                self.assertEqual(plan['prerelease'], 'true')

    def test_manual_and_branch_events_cannot_publish(self):
        for event, ref in [('workflow_dispatch', 'branch'), ('workflow_dispatch', 'tag'), ('push', 'branch'), ('pull_request', 'tag')]:
            with self.subTest(event=event, ref=ref):
                with self.assertRaises(ValueError):
                    plan_release('v1.8.0', event, ref)

    def test_rejects_ambiguous_invalid_or_unsafe_tags(self):
        for tag in ['1.8.0', 'v01.8.0', 'v1.08.0', 'v1.8.00', 'v1.8', 'v1.8.0-', 'v1.8.0-rc..1', 'v1.8.0-01', 'v1.8.0-rc.01', 'v1.8.0+build.1', 'v1.8.0/rc', 'v1.8.0\n', 'v1.8.0\nstable=true', 'v1.8.0-$(id)', 'v1.8.0-\u03b1']:
            with self.subTest(tag=tag):
                with self.assertRaises(ValueError):
                    self.plan(tag)

    def test_docker_tag_length_boundary(self):
        self.plan('v1.8.0-' + 'a' * 122)
        with self.assertRaises(ValueError):
            self.plan('v1.8.0-' + 'a' * 123)

    def test_compose_must_pin_exact_prerelease_or_stable_version(self):
        for tag in ['v1.8.0', 'v1.8.0-rc.1']:
            with self.subTest(tag=tag):
                plan = self.plan(tag)
                validate_compose_image(plan, '    image: dumanoj/ullavox:' + tag[1:])
                with self.assertRaises(ValueError):
                    validate_compose_image(plan, '    image: dumanoj/ullavox:latest')
                with self.assertRaises(ValueError):
                    validate_compose_image(plan, '    image: dumanoj/ullavox:1.7.0')
        with self.assertRaises(ValueError):
            validate_compose_image(self.plan('v1.8.0'), '')

    def test_cli_invalid_event_emits_no_publication_outputs(self):
        script = Path(__file__).resolve().parents[1] / 'release_policy.py'
        result = subprocess.run([sys.executable, str(script), 'v1.8.0', '--event', 'workflow_dispatch', '--ref-type', 'branch'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')

    def test_cli_valid_prerelease_outputs(self):
        script = Path(__file__).resolve().parents[1] / 'release_policy.py'
        result = subprocess.run([sys.executable, str(script), 'v1.8.0-rc.1', '--event', 'push', '--ref-type', 'tag'], capture_output=True, text=True, check=True)
        values = dict(line.split('=', 1) for line in result.stdout.splitlines())
        self.assertEqual(values['tags'], 'dumanoj/ullavox:1.8.0-rc.1')
        self.assertEqual(values['prerelease'], 'true')
        self.assertEqual(values['stable'], 'false')


if __name__ == '__main__':
    unittest.main()
