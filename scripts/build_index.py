import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import re

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTING_DIR = os.path.join(ROOT_DIR, 'content', '진행 공고')
INDEX_PATH = os.path.join(ROOT_DIR, 'content', 'index.md')

GITHUB_URL = 'https://github.com/nqn4iwin/obsidian-employment'


def parse_deadline(filename):
    stem = filename.removesuffix('.md')
    match = re.match(r'\((\d{4})\)', stem)
    if match:
        return match.group(1)  # MMDD
    return None


def build_index():
    files = [f for f in os.listdir(POSTING_DIR) if f.endswith('.md')]

    dated, ongoing = [], []
    for f in files:
        deadline = parse_deadline(f)
        if deadline:
            dated.append((deadline, f))
        else:
            ongoing.append(f)

    dated.sort(key=lambda x: x[0])
    ongoing.sort()

    lines = ['---', 'title: Job Description', '---', f'[GitHub]({GITHUB_URL})', '', '## 진행 공고', '']

    if dated:
        lines.append('#### 마감기한 있음')
        for _, f in dated:
            stem = f.removesuffix('.md')
            lines.append(f'- [[{stem}]]')
        lines.append('')

    if ongoing:
        lines.append('#### 상시공고')
        for f in ongoing:
            stem = f.removesuffix('.md')
            lines.append(f'- [[{stem}]]')
        lines.append('')

    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f'✅ index.md 생성 완료 (마감 {len(dated)}개, 상시 {len(ongoing)}개)')


if __name__ == '__main__':
    build_index()
