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


def sanitize_filename(filename: str) -> str:
    return re.sub(r'[\[\]|#^]', '', filename)


def process(filename: str):
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_path = os.path.normpath(os.path.join(root_dir, 'content', '수집 공고', filename))
    dst_filename = sanitize_filename(filename)
    dst_path = os.path.normpath(os.path.join(root_dir, 'content', '진행 공고', dst_filename))

    if not os.path.exists(src_path):
        print(f"❌ 파일을 찾을 수 없습니다: {src_path}")
        sys.exit(1)

    with open(src_path, 'r', encoding='utf-8') as f:
        content = f.read()

    match = re.search(r'\*\*원문\*\*[^\n]*\n(.*)', content, re.DOTALL)
    if not match:
        print("❌ **원문** 섹션을 찾을 수 없습니다.")
        sys.exit(1)
    job_text = match.group(1).strip()

    print(f"🤖 LLM 요약 중... ({filename})")
    summary = summarize(job_text)
    if summary is None:
        sys.exit(1)

    updated = re.sub(
        r'(\*\*요약\*\*\n)\n(\n\*\*원문\*\*[^\n]*)',
        rf'\g<1>{summary}\n\g<2>',
        content
    )
    if updated == content:
        print("❌ **요약** 섹션을 찾을 수 없습니다. 파일 형식을 확인하세요.")
        sys.exit(1)
    content = re.sub(r'^---\ndraft: true\n---\n', '', updated)
    content = re.sub(r'\n\*\*원문\*\*[^\n]*\n.*', '', content, flags=re.DOTALL).rstrip() + '\n'

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, 'w', encoding='utf-8') as f:
        f.write(content)

    os.remove(src_path)
    print(f"✅ 완료: {filename} → 진행 공고/")


def process_all():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    staging_dir = os.path.normpath(os.path.join(root_dir, 'content', '수집 공고'))
    files = [f for f in os.listdir(staging_dir) if f.endswith('.md')]

    if not files:
        print("수집 공고에 파일이 없습니다.")
        return

    print(f"총 {len(files)}개 변환 시작\n")
    for filename in files:
        process(filename)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        process_all()
    else:
        process(sys.argv[1])
