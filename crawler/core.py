import sys
sys.stdout.reconfigure(encoding='utf-8')

import requests
import os
import re
import yaml
from datetime import datetime


class BaseCrawler:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def load_config(self, config_path='config.yaml'):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _is_image_content(self, text: str) -> bool:
        """이미지 기반 채용공고 여부 감지"""
        return len(text.strip()) < 200

    def _extract_job_images(self, soup) -> list:
        """채용공고 상세 페이지에서 이미지 URL 추출 (사이트별 오버라이드 필요)"""
        return []

    def _ocr_images(self, image_urls: list, api_key: str) -> str:
        """Upstage Document OCR API로 이미지에서 텍스트 추출"""
        texts = []
        for url in image_urls:
            try:
                if url.startswith('//'):
                    url = 'https:' + url
                img_resp = requests.get(url, headers=self.headers, timeout=15)
                img_resp.raise_for_status()
                resp = requests.post(
                    'https://api.upstage.ai/v1/document-ai/ocr',
                    headers={'Authorization': f'Bearer {api_key}'},
                    files={'document': ('image.jpg', img_resp.content, 'image/jpeg')},
                    timeout=60
                )
                resp.raise_for_status()
                text = resp.json().get('text', '')
                if text.strip():
                    texts.append(text)
            except Exception as e:
                print(f"⚠️ OCR 실패 ({url[:60]}): {e}")
        return '\n'.join(texts)

    def _safe_filename(self, job) -> str:
        """save_to_md와 동일한 파일명 생성"""
        deadline_raw = job.get('deadline') or ''
        match = re.search(r'(\d{2})/(\d{2})', deadline_raw)
        if match:
            deadline_code = match.group(1) + match.group(2)
        elif '상시' in deadline_raw:
            deadline_code = '상시'
        else:
            deadline_code = '채용시마감'
        company = re.sub(r'[\\/:*?"<>|\n]', '', job.get('company') or '회사미상').strip()
        title = re.sub(r'[\\/:*?"<>|\n]', '', job.get('title') or '제목미상').strip()
        filename = f"({deadline_code}) {company} {title}.md"
        return filename[:96] + ".md" if len(filename) > 100 else filename

    def save_to_md(self, job, output_dir):
        """공고 하나를 Quartz 형식의 MD 파일로 저장"""
        os.makedirs(output_dir, exist_ok=True)

        filename = self._safe_filename(job)
        filepath = os.path.join(output_dir, filename)

        content_dir = os.path.dirname(output_dir)
        active_path = os.path.join(content_dir, '진행 공고', filename)

        if os.path.exists(filepath) or os.path.exists(active_path):
            print(f"⏭️  스킵 (이미 존재): {filename}")
            return None

        content = f"""---
draft: true
---
링크: {job.get('link', '')}

**기본 정보**
- 회사: {job.get('company') or '정보 없음'}
- 위치: {job.get('location', '정보 없음')}
- 경력: {job.get('career', '정보 없음')}
- 학력: {job.get('education', '정보 없음')}
- 고용형태: {job.get('work_type', '정보 없음')}
- 마감일: {job.get('deadline') or '정보 없음'}
- 검색 키워드: {job.get('keyword', '')}

**요약**


**원문**{' (OCR 추출)' if job.get('직무내용_출처') == 'OCR' else ''}
{job.get('직무내용', '정보 없음')}
"""

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ 생성: {filename}")
        return filepath

    def save_daily_summary(self, jobs, output_dir):
        """오늘의 공고 요약 MD 생성 (content/ 루트에 저장)"""
        content_dir = os.path.dirname(output_dir)
        filepath = os.path.join(content_dir, '오늘의 공고.md')

        rows = '\n'.join(
            f"| {job.get('company') or '?'} | {re.sub(r'[|]', '', job.get('title') or '?')} | {job.get('deadline') or '?'} | {self._safe_filename(job)} |"
            for job in jobs
        )

        content = f"""---
draft: true
---
# 오늘의 수집 공고 ({datetime.now().strftime('%Y-%m-%d')})

| 회사 | 직무 | 마감일 | 파일명 |
|------|------|--------|--------|
{rows}
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"📋 오늘의 공고.md 업데이트 완료 ({len(jobs)}건)")
