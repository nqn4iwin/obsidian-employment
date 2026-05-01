# 채용공고 트래커

사람인 채용공고를 자동 수집하여 Obsidian/Quartz 기반 정적 사이트로 게시하는 개인 레포지토리입니다.

---

## 디렉토리 구성

```
quartz/
├── content/                  # 사이트 콘텐츠 (Markdown)
│   ├── 진행중인 공고/         # 크롤러가 자동 생성하는 공고 파일
│   ├── 마감 공고/             # 마감된 공고 보관
│   ├── 기업분석/              # 수동 작성 기업 분석 노트
│   └── index.md              # 메인 페이지
├── crawler/                  # 사람인 크롤러
│   ├── saramin_crawler.py    # 크롤러 메인 스크립트
│   ├── config.yaml           # 검색 조건 설정
│   └── requirements.txt      # Python 의존성
├── .github/workflows/
│   └── crawl.yml             # GitHub Actions 크롤링 워크플로우
├── quartz.config.ts          # Quartz 사이트 설정
└── quartz.layout.ts          # Quartz 레이아웃 설정
```

---

## 크롤러 검색 방식

`crawler/config.yaml`에서 검색 조건을 설정합니다.

```yaml
sort: "recent"   # recent(최신순) / relation(관련도순)
limit: 10        # 키워드당 최대 수집 건수

searches:
  - keyword: "NLP"
    career_types: ["신입", "경력없음"]   # 신입 / 경력없음(경력무관) / 신입·경력
    locations: ["서울", "경기도"]
```

| 옵션 | 설명 |
|------|------|
| `sort` | `recent` = 최신순, `relation` = 관련도순 |
| `limit` | 키워드당 최대 수집 건수 |
| `career_types` | `신입`, `경력없음`(경력무관), `경력무관`, `경력` |
| `locations` | 서울, 경기도, 인천, 부산 등 광역시/도 단위 |

- 위치 필터는 사람인 API 파라미터로 서버 사이드 적용
- 경력 필터는 수집 후 클라이언트 사이드에서 정확히 매칭 (신입 / 경력무관 / 신입·경력)
- 동일 공고 중복 수집 방지 (rec_idx 기준)
- 수집된 공고는 `content/진행중인 공고/`에 Markdown 파일로 저장

---

## 배포 방식

**Cloudflare Pages** + **GitHub Actions** 조합으로 운영합니다.

```
크롤러 실행 (수동 또는 스케줄)
    → content/진행중인 공고/ 에 MD 파일 추가
    → v4 브랜치에 자동 커밋/푸시
    → Cloudflare Pages가 감지하여 자동 빌드 & 배포
```

| 항목 | 내용 |
|------|------|
| 빌드 명령어 | `npx quartz build` |
| 빌드 출력 디렉토리 | `public` |
| 배포 브랜치 | `v4` |
| 크롤링 트리거 | GitHub Actions `workflow_dispatch` (수동 실행) |

**커밋 & 배포 명령어**

```bash
# 커밋 후 자동 배포까지 (콘텐츠 변경 시)
git add .
git commit -m "커밋 메시지"
git push origin v4

# 커밋/푸시만 하고 배포 제외 (코드·설정 변경 시)
git add .
git commit -m "커밋 메시지 [CF Pages Skip]"
git push origin v4
```
