# 채용공고 트래커

사람인 채용공고를 수집하여 Obsidian/Quartz 기반 정적 사이트로 게시하는 개인 레포지토리입니다.

---

## 디렉토리 구성

```
quartz/
├── content/
│   ├── 수집 공고/         # 크롤러 수집 후 검토 대기 (미퍼블리시)
│   ├── 진행 공고/         # LLM 변환 완료, 사이트에 게시되는 공고
│   ├── 마감 공고/         # 마감된 공고 보관
│   ├── 기업분석/          # 수동 작성 기업 분석 노트
│   └── index.md
├── crawler/
│   ├── core.py            # 공통 베이스 클래스 (OCR, MD 저장 등)
│   ├── saramin_crawler.py
│   ├── jobkorea_crawler.py  # 구현 예정
│   ├── groupby_crawler.py   # 구현 예정
│   ├── config.yaml        # 검색 키워드·필터 설정
│   └── requirements.txt
├── converter/
│   ├── converter.py       # LLM 요약 변환기
│   └── prompt_template.py # Solar Pro 시스템 프롬프트
├── scripts/
│   └── build_index.py     # 만료 공고 이동 + index.md 자동 생성
└── .github/workflows/
    └── crawl.yml          # GitHub Actions 크롤링 워크플로우
```

---

## 개발 환경 (uv)

Python 의존성과 스크립트는 [uv](https://docs.astral.sh/uv/)로 관리합니다. 저장소 루트에서 한 번만 동기화하면 됩니다.

```bash
uv sync
```

환경 변수(`LLM_API_KEY` 등)는 프로젝트 루트의 `.env`에 두면 됩니다.

| 명령 | 설명 |
|------|------|
| `uv run crawl` | 사람인 크롤러 실행 |
| `uv run convert` | LLM 요약 변환 |
| `uv run index` | 만료 공고 이동 + index.md 생성 |

추가 인자는 `--` 뒤에 넘깁니다. 예: `uv run crawl -- --link <URL> --image`

---

## 운영 프로세스

### 1. 공고 수집

```bash
uv run crawl
```

`config.yaml`에 설정된 키워드로 사람인을 검색하여 `content/수집 공고/`에 MD 파일로 저장합니다.

특정 공고를 URL로 직접 수집할 수도 있습니다.

```bash
uv run crawl -- --link https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=12345678
```

채용공고 내용이 이미지로만 구성된 경우 `--image` 플래그를 추가하면 텍스트 추출을 건너뛰고 Upstage OCR로 이미지에서 직접 텍스트를 뽑습니다.

```bash
uv run crawl -- --link https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=12345678 --image
```

### 2. 검토 및 정리

`content/수집 공고/`에 생성된 파일을 직접 읽고, 지원하지 않을 공고는 삭제합니다.

### 3. LLM 변환

```bash
uv run convert
```

`수집 공고/`에 남은 파일 전체를 Solar Pro API로 요약하여 `진행 공고/`로 이동시킵니다. 원문은 제거되고 요약본만 저장됩니다.

### 4. 인덱스 재생성

```bash
uv run index
```

마감일이 지난 공고를 `진행 공고/`에서 `마감 공고/`로 자동 이동한 뒤, `content/index.md`를 재생성합니다.

### 5. 커밋 & 배포

```bash
git add content/
git commit -m "crawl: YYYY-MM-DD 공고 수집"
git push origin v4
```

푸시하면 Cloudflare Pages가 자동으로 빌드·배포합니다.

---

## 크롤러 설정

`crawler/config.yaml`에서 검색 조건을 설정합니다.

```yaml
output_dir: "../content/수집 공고"
sort: "recent"   # recent(최신순) / relation(관련도순)
limit: 10        # 키워드당 최대 수집 건수

searches:
  - keyword: "NLP"
    career_types: ["신입", "경력없음"]
    locations: ["서울", "경기도"]
```

| 옵션 | 설명 |
|------|------|
| `sort` | `recent` = 최신순, `relation` = 관련도순 |
| `limit` | 키워드당 최대 수집 건수 |
| `career_types` | `신입`, `경력없음`(경력무관), `경력무관`, `경력` |
| `locations` | 서울, 경기도, 인천, 부산 등 광역시/도 단위 |

- 동일 공고 중복 수집 방지 (rec_idx 기준)
- 경력 필터는 클라이언트 사이드에서 정확히 매칭

---

## 배포 설정

| 항목 | 내용 |
|------|------|
| 플랫폼 | Cloudflare Pages |
| 빌드 명령어 | `npx quartz build` |
| 빌드 출력 디렉토리 | `public` |
| 배포 브랜치 | `v4` |

코드·설정 변경 시 배포를 건너뛰려면 커밋 메시지에 `[CF Pages Skip]`을 추가합니다.
