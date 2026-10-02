import functools
import http.server
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import threading
import tempfile
import unittest
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, 'LC_ALL': 'C'}


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class Patterns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('build', ROOT / 'scripts/build.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.builder = module
        module.build()
        cls.cases = json.loads((ROOT / 'tests/cases.json').read_text())
        cls.catalog = json.loads((ROOT / 'catalog.json').read_text())

    def grep(self, name, text):
        result = subprocess.run(['grep', '-E', '-f', str(ROOT / 'patterns' / name)],
                                input=text + '\n', text=True, capture_output=True, env=ENV, timeout=5)
        self.assertIn(result.returncode, (0, 1), result.stderr)
        return result

    def test_cases(self):
        self.assertEqual(set(self.cases), {entry['name'] for entry in self.catalog})
        self.assertEqual(set(self.cases), {p.name for p in (ROOT / 'patterns').iterdir()})
        for name, cases in self.cases.items():
            for expected, key in [(0, 'match'), (1, 'no_match')]:
                self.assertTrue(cases[key])
                for line in cases[key]:
                    with self.subTest(name=name, line=line):
                        result = self.grep(name, line)
                        self.assertEqual(result.returncode, expected)
                        self.assertEqual(result.stdout, line + '\n' if expected == 0 else '')

    def test_ipv4_octet_boundaries(self):
        # Exercise every octet value in all four positions, including overflow.
        for position in range(4):
            for number in range(300):
                octets = ['1'] * 4
                octets[position] = str(number)
                with self.subTest(position=position, number=number):
                    self.assertEqual(self.grep('ipv4', '.'.join(octets)).returncode,
                                     0 if number <= 255 else 1)

    def test_domain_label_lengths(self):
        for length, status in [(1, 0), (63, 0), (64, 1), (100, 1)]:
            self.assertEqual(self.grep('domains', 'x' * length + '.com').returncode, status)
        for length, status in [(1, 1), (2, 0), (63, 0), (64, 1)]:
            self.assertEqual(self.grep('domains', 'example.' + 'x' * length).returncode, status)

    def test_long_nonmatching_input(self):
        for name in self.cases:
            self.assertEqual(self.grep(name, 'a' * 20000).returncode, 1)

    def test_artifact(self):
        out = ROOT / '_site'
        self.assertNotIn('{{', (out / 'index.html').read_text())
        for entry in self.catalog:
            data = (ROOT / 'patterns' / entry['name']).read_bytes()
            for name in [entry['name'], *entry['aliases']]:
                self.assertEqual((out / name).read_bytes(), data)
        for private in ['scripts', 'tests', 'patterns', '.github']:
            self.assertFalse((out / private).exists())

    def test_site_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'site'
            for base in ['https://example.github.io/grep.love/', 'https://grep.love']:
                with self.subTest(base=base):
                    self.builder.build(site_url=base, output=output)
                    home = (output / 'index.html').read_text()
                    self.assertIn(f'curl -s {base.rstrip("/")}/ips', home)
                    error = (output / '404.html').read_text()
                    self.assertIn(f'href="{base.rstrip("/")}/"', error)
                    self.assertNotIn('{{', error)

    def test_http_and_shell_examples(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
            functools.partial(QuietHandler, directory=temporary.name))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}/grep.love'
        try:
            self.builder.build(site_url=base, output=Path(temporary.name) / 'grep.love')
            with urllib.request.urlopen(f'{base}/') as response:
                page = response.read().decode()
                self.assertIn(f'curl -s {base}/ips', page)
                self.assertNotIn('{{', page)
            for entry in self.catalog:
                for name in [entry['name'], *entry['aliases']]:
                    with urllib.request.urlopen(f'{base}/{name}') as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.read(), (ROOT / 'patterns' / entry['name']).read_bytes())
            result = subprocess.run(['bash', '-c',
                'grep -E -f <(curl -s "$1/ips")', 'test', base],
                input='connected to 192.0.2.42:443\nno address\n',
                text=True, capture_output=True, env=ENV, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, 'connected to 192.0.2.42:443\n')
            # Download-first example must stop before grep on an HTTP error.
            script = '''pattern_file=$(mktemp) || exit 1
trap 'rm -f "$pattern_file"' EXIT
curl -fsSL --connect-timeout 10 --max-time 30 "$1/missing" -o "$pattern_file" || exit 1
test -s "$pattern_file" || exit 1
echo GREP_WAS_REACHED'''
            result = subprocess.run(['bash', '-c', script, 'test', base],
                                    text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn('GREP_WAS_REACHED', result.stdout)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
