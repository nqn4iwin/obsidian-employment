# 그룹바이(groupby) 채용공고 크롤러
#
# 구현 예정:
# - 키워드 검색 및 필터 적용 (경력, 직무, 지역 등)
# - 공고 상세 페이지 텍스트 추출
# - 이미지 기반 공고 OCR 처리 (core.BaseCrawler._ocr_images 사용)
# - content/수집 공고/ 에 MD 파일 저장 (core.BaseCrawler.save_to_md 사용)

from core import BaseCrawler


class GroupByCrawler(BaseCrawler):
    pass
