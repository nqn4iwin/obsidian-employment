import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import re
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

class SaraminCrawler:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        self.salary_codes = {
            '2400만원~': '8', '2600만원~': '9', '2800만원~': '10', '3000만원~': '11',
            '3200만원~': '12', '3400만원~': '13', '3600만원~': '14', '3800만원~': '15',
            '4000만원~': '16', '5000만원~': '17', '6000만원~': '18', '7000만원~': '19',
            '8000만원~': '20', '9000만원~': '21', '1억원~': '22'
        }

        self.company_types = {
            '대기업': 'scale001', '중견기업': 'scale003', '중소기업': 'scale004',
            '스타트업': 'scale005', '외국계': 'foreign', '코스닥': 'kosdaq',
            '공사/공기업': 'public', '연구소': 'laboratory', '교육기관': 'school',
            '금융기업': 'banking-organ'
        }

        self.job_types = {
            '정규직': '1', '계약직': '2', '병역특례': '3', '인턴': '4',
            '아르바이트': '5', '파견직': '6', '해외취업': '7', '위촉직': '8',
            '프리랜서': '9', '교육생': '12', '파트타임': '14', '전임': '15'
        }

        self.work_days = {
            '주5일': 'wsh010', '주6일': 'wsh030', '주3일/격일': 'wsh040',
            '유연근무제': 'wsh050', '면접후결정': 'wsh090'
        }

    def load_config(self, config_path='config.yaml'):
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def search_jobs(self, keyword=None, **filters):
        """실제 api 엔드포인트 사용한 검색"""

        jobs = []
        api_url = "https://www.saramin.co.kr/zf_user/search/get-recruit-list"

        params = {
            'searchType': 'search',
            'recruitPage': 1,
            'recruitSort': 'relation',
            'recruitPageCount': 40,
            'search_optional_item': 'y',
            'search_done': 'y',
            'panel_count': 'y',
            'preview': 'y',
            'mainSearch': 'n'
        }

        if keyword:
            params['searchword'] = keyword

        self._apply_filters(params, filters)

        try:
            response = requests.get(api_url, params=params, headers=self.headers)
            response.raise_for_status()

            json_data = response.json()
            total_count = int(json_data.get('count', '0').replace(',', ''))
            max_pages = min((total_count + 39) // 40, 5)

            print(f"총 {total_count:,}개 공고 발견! {max_pages}페이지 크롤링 예정")

            for page in range(1, max_pages + 1):
                print(f"📄 {page}/{max_pages} 페이지 수집 중...")

                params['recruitPage'] = page

                try:
                    response = requests.get(api_url, params=params, headers=self.headers)
                    response.raise_for_status()
                    json_data = response.json()

                    if json_data.get('innerHTML'):
                        soup = BeautifulSoup(json_data['innerHTML'], 'html.parser')
                        json_items = soup.find_all('div', class_='item_recruit')

                        if not json_items:
                            print(f"페이지 {page}에서 공고를 찾을 수 없습니다.")
                            break

                        print(f"총 └─ {len(json_items)}개 수집")

                        for item in json_items:
                            job_data = self.extract_job_info_from_api(item, keyword or '전체')
                            if job_data:
                                jobs.append(job_data)
                    else:
                        print(f"페이지 {page}에서 데이터를 받지 못했습니다.")
                        break

                    time.sleep(1)

                except Exception as e:
                    print(f"❌ 페이지 {page} 크롤링 실패: {e}")
                    continue

        except Exception as e:
            print(f"❌ 초기 데이터 로딩 실패: {e}")
            return []

        print(f"✅ '{keyword or '전체'}' 총 {len(jobs)}개 공고 수집 완료!")
        return jobs

    def _apply_filters(self, params, filters):
        """필터들을 파라미터에 적용"""

        if 'salary_min' in filters:
            if filters['salary_min'] in self.salary_codes:
                params['sal_min'] = self.salary_codes[filters['salary_min']]

        if 'company_types' in filters:
            company_list = []
            for company_type in filters['company_types']:
                if company_type in self.company_types:
                    company_list.append(self.company_types[company_type])
            if company_list:
                params['company_type'] = ','.join(company_list)

        if 'job_types' in filters:
            job_type_list = []
            for job_type in filters['job_types']:
                if job_type in self.job_types:
                    job_type_list.append(self.job_types[job_type])
            if job_type_list:
                params['job_type'] = ','.join(job_type_list)

        if 'work_days' in filters:
            work_day_list = []
            for work_day in filters['work_days']:
                if work_day in self.work_days:
                    work_day_list.append(self.work_days[work_day])
            if work_day_list:
                params['work_day'] = ','.join(work_day_list)

        if filters.get('remote_work', False):
            params['work_type'] = '1'

        if 'exclude_keywords' in filters:
            params['exc_keyword'] = ','.join(filters['exclude_keywords'])


    def extract_job_info_from_api(self, item, keyword):
        """API에서 받은 HTML 구조에 맞게 정보 추출"""
        try:
            title_elem = item.select_one('div.area_job > h2.job_tit > a')
            title = title_elem.get_text(strip=True) if title_elem else None

            href = title_elem.get('href') if title_elem else ""
            link = f"https://www.saramin.co.kr{href}" if href else ""

            company_elem = item.select_one('div.area_corp > strong.corp_name > a')
            company = company_elem.get_text(strip=True) if company_elem else None

            deadline_elem = item.select_one('div.area_job > div.job_date > span.date')
            deadline = deadline_elem.get_text(strip=True) if deadline_elem else None

            condition_elem = item.select('div.area_job > div.job_condition > span')

            location = "지역 없음"
            career = "경력 없음"
            education = "학력 없음"
            work_type = "근무형태 없음"

            if len(condition_elem) > 0:
                location_elem = condition_elem[0].select('a')
                location_list = [loc.get_text(strip=True) for loc in location_elem]

                if len(location_list) >= 2:
                    location = " ".join(location_list)
                elif len(location_list) == 1:
                    location = location_list[0]
                else:
                    location = "지역 없음"

            if len(condition_elem) > 1:
                career = condition_elem[1].get_text(strip=True)

            if len(condition_elem) > 2:
                education = condition_elem[2].get_text(strip=True)

            if len(condition_elem) > 3:
                work_type = condition_elem[3].get_text(strip=True)

            rec_idx = item.get('value', '')

            job = {
                'keyword': keyword,
                'title': title,
                'company': company,
                'location': location,
                'career': career,
                'education': education,
                'work_type': work_type,
                'deadline': deadline,
                'link': link,
                'rec_idx': rec_idx,
                'crawled_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            job.update(self.fetch_job_detail(rec_idx))
            return job

        except Exception as e:
            print(f"⚠️ 공고 정보 추출 실패 : {e}")
            return None


    def fetch_job_detail(self, rec_idx):
        """상세 페이지에서 추가 정보 수집"""
        if not rec_idx:
            return {}

        url = f"https://www.saramin.co.kr/zf_user/jobs/relay/view?isMypage=no&rec_idx={rec_idx}"

        try:
            time.sleep(0.5)
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            detail = {}

            # 요약 테이블 (급여, 근무지, 직원수 등)
            for row in soup.select('div.jv_summary table tr'):
                th = row.select_one('th')
                td = row.select_one('td')
                if th and td:
                    detail[th.get_text(strip=True)] = td.get_text(strip=True)

            # 기술스택 태그
            tags = [t.get_text(strip=True) for t in soup.select('div.jv_summary .list_tag a')]
            if tags:
                detail['기술스택'] = tags

            # 직무 상세 내용 (담당업무, 자격요건, 우대사항, 복리후생 포함)
            jv_detail = soup.select_one('div.jv_detail')
            if jv_detail:
                detail['직무내용'] = jv_detail.get_text(separator='\n', strip=True)

            return detail

        except Exception as e:
            print(f"⚠️ 상세 페이지 수집 실패 ({rec_idx}): {e}")
            return {}

    def save_to_csv(self, jobs, filename=None):
        """결과를 csv로 저장"""
        if not jobs:
            print("저장할 데이터가 없습니다.")
            return

        if not filename:
            filename = f"사람인_공고_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        df = pd.DataFrame(jobs)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"{len(jobs)}개 공고를 {filename}에 저장하였습니다.")
        return filename

    def save_to_md(self, job, output_dir):
        """공고 하나를 Quartz 형식의 MD 파일로 저장"""
        os.makedirs(output_dir, exist_ok=True)

        # 마감일 파싱: "05/03(토)" → "0503", "상시채용" → "상시"
        deadline_raw = job.get('deadline') or ''
        match = re.search(r'(\d{2})/(\d{2})', deadline_raw)
        if match:
            deadline_code = match.group(1) + match.group(2)
        elif '상시' in deadline_raw:
            deadline_code = '상시'
        else:
            deadline_code = '미정'

        # 파일명 안전 처리 (Windows 금지 문자 제거)
        company = re.sub(r'[\\/:*?"<>|\n]', '', job.get('company') or '회사미상').strip()
        title = re.sub(r'[\\/:*?"<>|\n]', '', job.get('title') or '제목미상').strip()

        filename = f"({deadline_code}) {company} {title}.md"
        if len(filename) > 100:
            filename = filename[:96] + ".md"

        filepath = os.path.join(output_dir, filename)

        if os.path.exists(filepath):
            print(f"⏭️  스킵 (이미 존재): {filename}")
            return None

        base_fields = {
            'keyword', 'title', 'company', 'location', 'career', 'education',
            'work_type', 'deadline', 'link', 'rec_idx', 'crawled_at', '기술스택', '직무내용'
        }
        extra_lines = ''.join(
            f"- {k}: {v}\n" for k, v in job.items()
            if k not in base_fields and v
        )
        skills = job.get('기술스택', [])
        skills_str = f"- 기술스택: {', '.join(skills)}\n" if skills else ''
        detail_section = f"\n**직무 내용**\n{job['직무내용']}\n" if job.get('직무내용') else ''

        content = f"""**지원링크**
{job.get('link', '')}

**기본 정보**
- 회사: {job.get('company') or '정보 없음'}
- 위치: {job.get('location', '정보 없음')}
- 경력: {job.get('career', '정보 없음')}
- 학력: {job.get('education', '정보 없음')}
- 고용형태: {job.get('work_type', '정보 없음')}
- 마감일: {job.get('deadline') or '정보 없음'}
- 검색 키워드: {job.get('keyword', '')}
{extra_lines}{skills_str}{detail_section}
---
_사람인 자동 수집 — 상세 내용은 링크에서 확인_
"""

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ 생성: {filename}")
        return filepath

    def send_email_notification(self, jobs, email_config):
        """이메일로 공고 알림"""
        if not jobs:
            return

        subject = f"🔔 새 채용공고 {len(jobs)}개 발견! - {datetime.now().strftime('%m/%d')}"

        html_body = f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: 'Apple SD Gothic Neo', Arial, sans-serif; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white; padding: 20px; text-align: center; }}
                    .job-item {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px;
                            border-radius: 8px; background: #fafafa; }}
                    .job-title {{ font-size: 18px; font-weight: bold; color: #2c3e50; }}
                    .company {{ color: #e74c3c; font-weight: bold; margin: 5px 0; }}
                    .details {{ color: #7f8c8d; font-size: 14px; margin: 5px 0; }}
                    .btn {{ background: #3498db; color: white; padding: 8px 16px;
                        text-decoration: none; border-radius: 4px; display: inline-block; }}
                    .summary {{ background: #ecf0f1; padding: 15px; margin: 20px 0; border-radius: 8px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🎯 채용공고 자동 수집 결과</h1>
                    <p>{datetime.now().strftime('%Y년 %m월 %d일')} 수집 완료</p>
                </div>

                <div class="summary">
                    <h2>📊 수집 현황</h2>
                    <p>• <strong>총 {len(jobs)}개</strong> 공고 발견</p>
                    <p>• 키워드별 분포: {self._get_keyword_stats(jobs)}</p>
                    <p>• 📎 <strong>전체 데이터는 첨부된 CSV 파일을 확인하세요!</strong></p>
                </div>

                <h2>🔥 주요 공고 미리보기 (최대 10개)</h2>
        """

        for job in jobs[:10]:
            html_body += f"""
            <div class="job-item">
                <div class="job-title">{job['title']}</div>
                <div class="company">🏢 {job['company']}</div>
                <div class="details">
                    📍 {' '.join(job['location']) if isinstance(job['location'], list) else job['location']} |
                    👔 {job['career']} |
                    🎓 {job['education']} |
                    ⏰ {job['deadline']}
                </div>
                <a href="{job['link']}" class="btn" target="_blank">지원하기 →</a>
            </div>
            """

        if len(jobs) > 10:
            html_body += f"""
            <div style="text-align: center; padding: 20px; background: #fff3cd; border-radius: 8px; margin: 20px 0;">
                <h3>📋 나머지 {len(jobs)-10}개 공고</h3>
                <p>전체 공고는 <strong>첨부된 CSV 파일</strong>에서 확인하세요!</p>
            </div>
            """

        html_body += """
                <div style="text-align: center; margin-top: 30px; padding: 20px; background: #f8f9fa;">
                    <p>🤖 Python 자동화 시스템이 수집했습니다</p>
                    <p style="font-size: 12px; color: #6c757d;">
                        매일 오전 9시에 새로운 공고를 확인해드립니다
                    </p>
                </div>
            </body>
        </html>
        """

        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = email_config['sender_email']
            msg['To'] = email_config['receiver_email']
            msg['Subject'] = subject

            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)

            csv_filename = self.save_to_csv(jobs)
            if csv_filename and os.path.exists(csv_filename):
                with open(csv_filename, 'rb') as attachment:
                    part = MIMEApplication(attachment.read(), _subtype='csv')
                    part.add_header('Content-Disposition', 'attachment',
                                filename=f"채용공고_{datetime.now().strftime('%Y%m%d')}.csv")
                    msg.attach(part)

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(email_config['sender_email'], email_config['app_password'])
            server.send_message(msg)
            server.quit()

            print("📧 이메일 알림을 성공적으로 보냈습니다!")

        except Exception as e:
            print(f"❌ 이메일 전송 실패: {e}")

    def _get_keyword_stats(self, jobs):
        """키워드별 통계 생성"""
        keyword_counts = {}
        for job in jobs:
            keyword = job.get('keyword', '기타')
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

        stats = [f"{k}({v}개)" for k, v in keyword_counts.items()]
        return ", ".join(stats)

    def run_advanced_crawler(self, searches, output_dir, email_config=None):
        """config에서 읽은 검색 조건으로 크롤링 후 MD 생성"""
        print("🚀 크롤링 시작!")

        all_jobs = []

        for search in searches:
            search = search.copy()
            keyword = search.pop('keyword', '')
            print(f"\n📋 '{keyword}' 검색 중...")
            jobs = self.search_jobs(keyword=keyword, **search)
            all_jobs.extend(jobs)
            print(f"✅ {len(jobs)}개 공고 수집")

        # 중복 제거
        unique_jobs = []
        seen_links = set()
        for job in all_jobs:
            if job['link'] not in seen_links:
                unique_jobs.append(job)
                seen_links.add(job['link'])

        print(f"\n🎉 총 {len(unique_jobs)}개 고유 공고 수집!")

        # MD 파일 생성
        saved_count = 0
        for job in unique_jobs:
            result = self.save_to_md(job, output_dir)
            if result:
                saved_count += 1

        print(f"\n📝 {saved_count}개 MD 파일 생성 완료 → {output_dir}")

        if email_config and unique_jobs:
            self.send_email_notification(unique_jobs, email_config)

        return unique_jobs


if __name__ == "__main__":
    crawler = SaraminCrawler()
    config = crawler.load_config('config.yaml')

    # output_dir은 이 스크립트 위치 기준 상대경로로 해석
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir_raw = config.get('output_dir', '../content/진행중인 공고')
    output_dir = os.path.normpath(os.path.join(script_dir, output_dir_raw))

    print(f"📁 출력 경로: {output_dir}")

    email_config = None
    if os.environ.get('EMAIL_SENDER'):
        email_config = {
            'sender_email': os.environ.get('EMAIL_SENDER'),
            'receiver_email': os.environ.get('EMAIL_RECEIVER'),
            'app_password': os.environ.get('EMAIL_APP_PASSWORD')
        }

    crawler.run_advanced_crawler(
        searches=config['searches'],
        output_dir=output_dir,
        email_config=email_config
    )
