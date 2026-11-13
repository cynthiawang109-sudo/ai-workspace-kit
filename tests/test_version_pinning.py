"""Local-repository integration checks for the Bash and PowerShell pinning scripts.

Run with: python -m unittest discover -s tests -v
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which('bash')
if os.name == 'nt' and Path('C:/Program Files/Git/bin/bash.exe').exists():
    BASH = 'C:/Program Files/Git/bin/bash.exe'
POWERSHELL = shutil.which('pwsh') or shutil.which('powershell')


class PinningTests(unittest.TestCase):
    def command(self, args, cwd=None, expected=0):
        result = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def git(self, *args, cwd=None):
        return self.command(['git', *args], cwd=cwd).strip()

    def sync(self, update=False, only=None, expected=0):
        args = [self.shell, 'sync.sh'] if self.kind == 'bash' else [
            self.shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'sync.ps1']
        if update:
            args += ['--update-pins' if self.kind == 'bash' else '-UpdatePins']
        if only:
            args += [only] if self.kind == 'bash' else ['-Only', only]
        return self.command(args, cwd=self.work, expected=expected)

    def doctor(self):
        args = [self.shell, 'doctor.sh'] if self.kind == 'bash' else [
            self.shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'doctor.ps1']
        # Other machine-health checks are intentionally unavailable in the fixture.
        result = subprocess.run(args, cwd=self.work, text=True, capture_output=True)
        return '\n'.join(line for line in result.stdout.splitlines()
                         if 'pin/' in line or 'git/' in line or 'pinned versions -' in line)

    def manifest(self, alpha, beta=None):
        self.versions.write_bytes((
            '# Fixture pins\r\nalpha ' + alpha + '\r\nbeta ' + (beta or self.tip) + '\r\n'
        ).encode())

    def exercise(self, kind, shell):
        self.kind, self.shell = kind, shell
        with tempfile.TemporaryDirectory(prefix='tf-110-tests-') as temporary:
            base = Path(temporary)
            origin = base / 'origin'
            self.git('init', '-b', 'main', str(origin))
            self.git('config', 'user.name', 'Fixture', cwd=origin)
            self.git('config', 'user.email', 'fixture@example.invalid', cwd=origin)
            (origin / 'data.txt').write_text('first\n')
            self.git('add', '.', cwd=origin)
            self.git('commit', '-m', 'first', cwd=origin)
            old = self.git('rev-parse', 'HEAD', cwd=origin)
            (origin / 'data.txt').write_text('second\n')
            self.git('commit', '-am', 'second', cwd=origin)
            self.tip = self.git('rev-parse', 'HEAD', cwd=origin)
            self.work = base / 'workspace'
            self.work.mkdir()
            for name in ('sync.sh', 'sync.ps1', 'doctor.sh', 'doctor.ps1'):
                shutil.copyfile(ROOT / name, self.work / name)
            (self.work / 'repos.txt').write_text(
                f'alpha {origin.as_posix()}\nbeta {origin.as_posix()}\n')
            self.versions = self.work / 'versions.txt'
            self.manifest(old)

            # Updating a missing checkout uses a bare fetch, never a working tree.
            self.assertIn('1 changed pin(s)', self.sync(update=True, only='alpha'))
            self.assertFalse((self.work / 'projects').exists())
            self.assertIn(f'alpha {self.tip}', self.versions.read_text())
            self.assertEqual(self.versions.read_bytes(), (
                f'# Fixture pins\r\nalpha {self.tip}\r\nbeta {self.tip}\r\n').encode())
            self.manifest(old)
            self.sync(only='alpha')
            alpha = self.work / 'projects/alpha'
            self.assertFalse((self.work / 'projects/beta').exists())
            self.assertEqual(self.git('rev-parse', 'HEAD', cwd=alpha), old)
            self.assertEqual(self.git('rev-parse', '--abbrev-ref', 'HEAD', cwd=alpha), 'HEAD')
            self.sync()
            self.assertIn('[ok]   git/alpha - detached at pin', self.doctor())

            # Dirty trees are skipped before fetch; updates may fetch but never move HEAD.
            dirty = alpha / 'local.txt'
            dirty.write_bytes(b'local work\x00\xff')
            fetch_before = (alpha / '.git/FETCH_HEAD').read_bytes()
            self.assertIn('uncommitted changes', self.sync())
            self.assertEqual((alpha / '.git/FETCH_HEAD').read_bytes(), fetch_before)
            self.assertEqual(dirty.read_bytes(), b'local work\x00\xff')
            self.assertIn('1 changed pin(s)', self.sync(update=True, only='alpha'))
            self.assertEqual(self.git('rev-parse', 'HEAD', cwd=alpha), old)
            before = self.versions.read_bytes()
            self.assertIn('0 changed pin(s)', self.sync(update=True))
            self.assertEqual(self.versions.read_bytes(), before)
            dirty.unlink()
            self.sync()
            self.assertEqual(self.git('rev-parse', '--abbrev-ref', 'HEAD', cwd=alpha), 'main')

            # A local main ahead of the pin must not be reported as synchronized.
            self.git('config', 'user.name', 'Fixture', cwd=alpha)
            self.git('config', 'user.email', 'fixture@example.invalid', cwd=alpha)
            self.git('commit', '--allow-empty', '-m', 'local work', cwd=alpha)
            local = self.git('rev-parse', 'HEAD', cwd=alpha)
            self.assertIn('local commits beyond pin', self.sync(only='alpha', expected=1))
            self.assertEqual(self.git('rev-parse', 'HEAD', cwd=alpha), local)
            # Preserve the commit on a feature branch and restore main for later cases.
            self.git('checkout', '-b', 'local-work', cwd=alpha)
            self.git('branch', '-f', 'main', self.tip, cwd=alpha)
            self.sync(only='alpha')
            self.git('checkout', '--detach', self.tip, cwd=alpha)
            self.sync()
            self.assertEqual(self.git('rev-parse', '--abbrev-ref', 'HEAD', cwd=alpha), 'main')

            # Doctor distinguishes feature work from main/detached drift.
            self.manifest(old)
            output = self.doctor()
            self.assertIn(f'[fail] pin/alpha - HEAD {self.tip[:7]}, pin {old[:7]} - run ./sync.sh', output)
            self.git('checkout', '-b', 'feature', cwd=alpha)
            self.assertIn('[warn] pin/alpha', self.doctor())
            self.git('checkout', '--detach', self.tip, cwd=alpha)
            self.assertIn('[fail] pin/alpha', self.doctor())
            self.sync()
            self.assertIn('[ok]   pin/alpha', self.doctor())

            # Missing and unresolvable pins fail, including under the filter.
            self.manifest('0' * 40)
            self.sync(only='alpha', expected=1)
            self.versions.write_text(f'beta {self.tip}\n')
            self.sync(only='alpha', expected=1)
            self.assertIn('[fail] pin/alpha', self.doctor())
            self.versions.unlink()
            self.sync(expected=1)
            self.assertIn('[fail] pinned versions', self.doctor())

    @unittest.skipUnless(BASH, 'Bash unavailable')
    def test_bash(self):
        self.exercise('bash', BASH)

    @unittest.skipUnless(POWERSHELL, 'PowerShell unavailable')
    def test_powershell(self):
        self.exercise('powershell', POWERSHELL)


if __name__ == '__main__':
    unittest.main()
