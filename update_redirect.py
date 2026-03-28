#!/usr/bin/env python3
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
README = ROOT / 'README.md'
PATTERN = re.compile(r'https://[a-z0-9]+\.lhr\.life')
JOURNAL_PATTERN = re.compile(r'https://([a-z0-9]+\.lhr\.life)')


def run(cmd, cwd=None, check=True):
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


def latest_tunnel_url():
    out = run([
        'journalctl', '--user', '-u', 'venture-console-tunnel.service', '-n', '200', '--no-pager'
    ]).stdout
    urls = JOURNAL_PATTERN.findall(out)
    if not urls:
        raise RuntimeError('No tunnel URL found in journal')
    return f'https://{urls[-1]}'


def current_redirect_url():
    text = INDEX.read_text(encoding='utf-8')
    m = PATTERN.search(text)
    if not m:
        raise RuntimeError('No existing redirect URL found in index.html')
    return m.group(0)


def replace_url(new_url):
    idx = INDEX.read_text(encoding='utf-8')
    idx = PATTERN.sub(new_url, idx)
    INDEX.write_text(idx, encoding='utf-8')

    if README.exists():
        rd = README.read_text(encoding='utf-8')
        if PATTERN.search(rd):
            rd = PATTERN.sub(new_url, rd)
        else:
            rd = rd.rstrip() + f'\n\nCurrent target: {new_url}\n'
        README.write_text(rd, encoding='utf-8')


def git_dirty():
    return bool(run(['git', 'status', '--porcelain'], cwd=ROOT).stdout.strip())


def main():
    new_url = latest_tunnel_url()
    old_url = current_redirect_url()
    if new_url == old_url:
        print(f'No change: {new_url}')
        return 0

    replace_url(new_url)
    if not git_dirty():
        print('No file changes after replacement')
        return 0

    run(['git', 'add', 'index.html', 'README.md'], cwd=ROOT)
    run(['git', 'commit', '-m', f'chore: update demo redirect to {new_url}'], cwd=ROOT)
    run(['git', 'push', 'origin', 'main'], cwd=ROOT)
    print(f'Updated redirect: {old_url} -> {new_url}')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f'ERROR: {e}', file=sys.stderr)
        raise SystemExit(1)
