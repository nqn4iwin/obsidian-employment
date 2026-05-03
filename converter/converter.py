import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import re
from dotenv import load_dotenv
from openai import OpenAI
from prompt_template import SYSTEM_PROMPT

load_dotenv()

MODEL = 'solar-pro'


def summarize(job_text: str) -> str | None:
    api_key = os.environ.get('LLM_API_KEY')
    if not api_key:
        print("⚠️ LLM_API_KEY 환경변수가 설정되지 않았습니다.")
        return None
    client = OpenAI(api_key=api_key, base_url='https://api.upstage.ai/v1')
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': job_text},
        ]
    )
    return resp.choices[0].message.content


def process(filename: str):
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(root_dir, 'content', '진행중인 공고', filename)
    filepath = os.path.normpath(filepath)

    if not os.path.exists(filepath):
        print(f"❌ 파일을 찾을 수 없습니다: {filepath}")
        sys.exit(1)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    match = re.search(r'\*\*원문\*\*\n(.*)', content, re.DOTALL)
    if not match:
        print("❌ **원문** 섹션을 찾을 수 없습니다.")
        sys.exit(1)
    job_text = match.group(1).strip()

    print(f"🤖 LLM 요약 중... ({filename})")
    summary = summarize(job_text)
    if summary is None:
        sys.exit(1)

    content = re.sub(
        r'(\*\*요약\*\*\n)\n(\n\*\*원문\*\*)',
        rf'\g<1>{summary}\n\g<2>',
        content
    )
    content = re.sub(r'^---\ndraft: true\n---\n', '', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 완료: {filename}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: py converter/converter.py \"파일명.md\"")
        sys.exit(1)
    process(sys.argv[1])
