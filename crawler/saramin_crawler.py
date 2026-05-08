import sys
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import re
from datetime import datetime

from core import BaseCrawler


class SaraminCrawler(BaseCrawler):
    def __init__(self):
        super().__init__()

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

        self.location_codes = {
            '서울': '101000', '경기': '102000', '경기도': '102000',
            '인천': '108000', '부산': '103000', '대구': '104000',
            '대전': '106000', '광주': '105000', '울산': '107000',
            '세종': '118000', '강원': '109000', '충북': '110000',
            '충남': '111000', '전북': '112000', '전남': '113000',
            '경북': '114000', '경남': '115000', '제주': '116000'
        }

        self.career_codes = {
            '신입': '1', '경력없음': '1', '경력무관': '3', '경력': '2'
        }

        self.sort_codes = {
            'recent': 'reg_dt', '최신순': 'reg_dt',
            'relation': 'relation', '관련도순': 'relation'
        }

    def search_jobs(self, keyword=None, sort='relation', limit=None, **filters):
        """실제 api 엔드포인트 사용한 검색"""

        jobs = []
        api_url = "https://www.saramin.co.kr/zf_user/search/get-recruit-list"

        sort_param = self.sort_codes.get(sort, sort)
        career_types = filters.pop('career_types', None)

        params = {
            'searchType': 'search',
            'recruitPage': 1,
            'recruitSort': sort_param,
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

            print(f"총 {total_count:,}개 공고 발견! 최대 {max_pages}페이지 크롤링")

            for page in range(1, max_pages + 1):
                if limit and len(jobs) >= limit:
                    break

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

                        for item in json_items:
                            if limit and len(jobs) >= limit:
                                break
                            job_data = self.extract_job_info_from_api(item, keyword or '전체')
                            if job_data and self._career_matches(job_data.get('career', ''), career_types):
                                jobs.append(job_data)

                        print(f"└─ 현재까지 {len(jobs)}개 수집{'(목표 달성)' if limit and len(jobs) >= limit else ''}")
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

    def _career_matches(self, career_field, career_types):
        """경력 조건 클라이언트 사이드 필터"""
        if not career_types:
            return True
        career_stripped = career_field.strip()
        for ct in career_types:
            if ct == '신입' and ('신입' in career_stripped):
                return True
            if ct in ('경력없음', '경력무관') and career_stripped == '경력무관':
                return True
        return False

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

        if 'locations' in filters:
            loc_list = [self.location_codes[l] for l in filters['locations'] if l in self.location_codes]
            if loc_list:
                params['loc_mcd'] = ','.join(loc_list)

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

    def _extract_job_images(self, soup) -> list:
        """사람인 상세 페이지에서 이미지 URL 추출"""
        for selector in ['.jv_detail img', '.wrap_jv_cont img', '.recruitment_img img', 'div img']:
            imgs = soup.select(selector)
            urls = [img['src'] for img in imgs if img.get('src')]
            if urls:
                return urls
        return []

    def fetch_job_detail(self, rec_idx, force_ocr=False):
        """상세 페이지에서 추가 정보 수집 (AJAX 엔드포인트 사용)"""
        if not rec_idx:
            return {}

        ajax_headers = {
            **self.headers,
            'Referer': f'https://www.saramin.co.kr/zf_user/jobs/relay/view?isMypage=no&rec_idx={rec_idx}',
            'X-Requested-With': 'XMLHttpRequest'
        }

        detail = {}

        try:
            time.sleep(0.5)

            r = requests.get(
                'https://www.saramin.co.kr/zf_user/jobs/relay/view-ajax',
                params={'rec_idx': rec_idx},
                headers=ajax_headers
            )
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')

            summary_cont = soup.select_one('div.jv_summary div.cont')
            if summary_cont:
                detail['요약정보'] = summary_cont.get_text(separator='\n', strip=True)

            benefit = soup.select_one('div.jv_benefit')
            if benefit:
                detail['복리후생'] = benefit.get_text(separator='\n', strip=True)

            tags = [t.get_text(strip=True) for t in soup.select('div.tags .cont a')]
            if tags:
                detail['기술스택'] = tags

            if soup.select_one('div.jv_detail iframe'):
                time.sleep(0.3)
                r2 = requests.get(
                    'https://www.saramin.co.kr/zf_user/jobs/relay/view-detail',
                    params={'rec_idx': rec_idx, 'rec_seq': '0'},
                    headers=self.headers
                )
                r2.raise_for_status()
                soup2 = BeautifulSoup(r2.text, 'html.parser')
                detail['직무내용'] = soup2.get_text(separator='\n', strip=True)
                if force_ocr:
                    detail['직무내용'] = ''

                api_key = os.environ.get('LLM_API_KEY', '')
                if api_key and self._is_image_content(detail['직무내용']):
                    image_urls = self._extract_job_images(soup2)
                    if image_urls:
                        print(f"  🖼️  이미지 기반 공고 감지 — OCR 시도 ({len(image_urls)}개)")
                        ocr_text = self._ocr_images(image_urls, api_key)
                        if ocr_text.strip():
                            detail['직무내용'] = ocr_text
                            detail['직무내용_출처'] = 'OCR'

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

    def fetch_job_by_url(self, url: str, force_ocr: bool = False):
        """URL로부터 단일 공고 수집"""
        match = re.search(r'rec_idx=(\d+)', url)
        if not match:
            print(f"❌ URL에서 rec_idx를 찾을 수 없습니다: {url}")
            return None
        rec_idx = match.group(1)

        try:
            r = requests.get(url, headers=self.headers)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')

            title_el = soup.select_one('h1.tit_job')
            title = title_el.get_text(strip=True) if title_el else '제목 없음'

            header_el = soup.select_one('.wrap_jv_header')
            deadline = ''
            if header_el:
                header_text = header_el.get_text()
                date_match = re.search(r'\d{2}/\d{2}', header_text)
                if date_match:
                    deadline = date_match.group(0)
                elif '상시' in header_text:
                    deadline = '상시채용'

            ajax_headers = {
                **self.headers,
                'Referer': f'https://www.saramin.co.kr/zf_user/jobs/relay/view?isMypage=no&rec_idx={rec_idx}',
                'X-Requested-With': 'XMLHttpRequest'
            }
            time.sleep(0.5)
            r2 = requests.get(
                'https://www.saramin.co.kr/zf_user/jobs/relay/view-ajax',
                params={'rec_idx': rec_idx},
                headers=ajax_headers
            )
            r2.raise_for_status()
            soup2 = BeautifulSoup(r2.text, 'html.parser')

            company_el = soup2.select_one('.company_name')
            company = company_el.get_text(strip=True) if company_el else '회사 없음'

            conditions = {}
            for dl in soup2.select('div.jv_summary dl'):
                parts = [t for t in dl.get_text(separator='|', strip=True).split('|') if t]
                if len(parts) >= 2:
                    conditions[parts[0]] = parts[1]

            job = {
                'keyword': '링크 직접 수집',
                'title': title,
                'company': company,
                'location': conditions.get('근무지역', '정보 없음'),
                'career': conditions.get('경력', '정보 없음'),
                'education': conditions.get('학력', '정보 없음'),
                'work_type': conditions.get('근무형태', '정보 없음'),
                'deadline': deadline,
                'link': url,
                'rec_idx': rec_idx,
                'crawled_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            job.update(self.fetch_job_detail(rec_idx, force_ocr=force_ocr))
            return job

        except Exception as e:
            print(f"❌ 공고 수집 실패: {e}")
            return None

    def run_advanced_crawler(self, searches, output_dir, sort='relation', limit=None):
        """config에서 읽은 검색 조건으로 크롤링 후 MD 생성"""
        print("🚀 크롤링 시작!")

        all_jobs = []

        for search in searches:
            search = search.copy()
            keyword = search.pop('keyword', '')
            print(f"\n📋 '{keyword}' 검색 중...")
            jobs = self.search_jobs(keyword=keyword, sort=sort, limit=limit, **search)
            all_jobs.extend(jobs)
            print(f"✅ {len(jobs)}개 공고 수집")

        unique_jobs = []
        seen = set()
        for job in all_jobs:
            key = job.get('rec_idx') or job.get('link')
            if key not in seen:
                unique_jobs.append(job)
                seen.add(key)

        print(f"\n🎉 총 {len(unique_jobs)}개 고유 공고 수집!")

        saved_count = 0
        for job in unique_jobs:
            result = self.save_to_md(job, output_dir)
            if result:
                saved_count += 1

        print(f"\n📝 {saved_count}개 MD 파일 생성 완료 → {output_dir}")

        if saved_count > 0:
            self.save_daily_summary(unique_jobs, output_dir)

        return unique_jobs


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, help='키워드당 최대 수집 건수 (config.yaml의 limit 덮어씀)')
    parser.add_argument('--link', type=str, help='특정 공고 URL (1건만 수집)')
    parser.add_argument('--image', action='store_true', help='이미지 기반 공고로 간주하고 OCR 강제 실행 (--link와 함께 사용)')
    args = parser.parse_args()

    crawler = SaraminCrawler()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config = crawler.load_config(os.path.join(script_dir, 'config.yaml'))

    output_dir_raw = config.get('output_dir', '../content/수집 공고')
    output_dir = os.path.normpath(os.path.join(script_dir, output_dir_raw))

    print(f"📁 출력 경로: {output_dir}")

    if args.link:
        print(f"🔗 링크 직접 수집: {args.link}")
        job = crawler.fetch_job_by_url(args.link, force_ocr=args.image)
        if job:
            result = crawler.save_to_md(job, output_dir)
            if result:
                print(f"✅ 저장 완료: {result}")
        sys.exit(0)

    sort = config.get('sort', 'relation')
    limit = args.limit if args.limit is not None else config.get('limit', None)

    crawler.run_advanced_crawler(
        searches=config['searches'],
        output_dir=output_dir,
        sort=sort,
        limit=limit,
    )
