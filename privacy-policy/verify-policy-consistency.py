#!/usr/bin/env python3
"""StarGuardians 공개 개인정보·삭제 문서의 핵심 고지와 링크를 검증한다."""

from html.parser import HTMLParser
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent
FILES = {
    "ko": ROOT / "privacy-ko.html",
    "en": ROOT / "privacy-en.html",
    "delete": ROOT / "delete-account.html",
    "index": ROOT / "index.html",
    "sop": ROOT / "account-deletion-sop.md",
    "support": ROOT.parent / "starguardians" / "support.html",
}


class StructureParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in self.VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        return

    def handle_endtag(self, tag: str) -> None:
        if tag in self.VOID_TAGS:
            return
        if not self.stack:
            self.errors.append(f"닫는 태그 </{tag}> 앞에 열린 태그가 없음")
            return
        current = self.stack.pop()
        if current != tag:
            self.errors.append(f"태그 불일치: <{current}> 다음에 </{tag}>")

    def finish(self) -> None:
        if self.stack:
            self.errors.append(f"닫히지 않은 태그: {', '.join(self.stack)}")


def check(condition: bool, label: str, failures: list[str]) -> None:
    if condition:
        print(f"[PASS] {label}")
    else:
        print(f"[FAIL] {label}")
        failures.append(label)


def main() -> int:
    failures: list[str] = []
    texts: dict[str, str] = {}

    for key, path in FILES.items():
        check(path.is_file(), f"필수 파일 존재: {path.name}", failures)
        texts[key] = path.read_text(encoding="utf-8") if path.is_file() else ""

    required = {
        "ko": [
            "2026년 8월 13일", "StarGuardians Android 분석 안내", "Android 23.2.0", "자동 수집이 활성화",
            "Unity IAP 5.4", "IAP Insights", "unity-iap-contact@unity3d.com",
            "Firebase uid", "SSV", "프로필 및 소셜 정보", "친구 코드", "클랜",
            "카드 교환", "동의 및 환경설정", "지원 및 삭제 요청 정보", "퇴역한 경매",
            "TikTok for Business App Events SDK", "별도 명시 동의", "게임 실행 단위의 가명 이벤트 ID",
        ],
        "en": [
            "August 13, 2026", "StarGuardians Android analytics notice", "Android 23.2.0", "Automatic collection is enabled",
            "Unity IAP 5.4", "IAP Insights", "unity-iap-contact@unity3d.com",
            "Firebase uid", "SSV", "Profile and Social Information", "friend code", "clan",
            "card-trade", "Consent and Preferences", "Support and Deletion Request Information", "Retired Auction",
            "TikTok for Business App Events SDK", "separate explicit opt-in", "pseudonymous event IDs",
        ],
        "delete": [
            "July 20, 2026", "Firebase Analytics 23.2.0", "Unity IAP 5.4 IAP Insights",
            "unity-iap-contact@unity3d.com", "AdMob", "SSV", "Firebase uid", "친구 요청",
            "클랜", "카드 교환", "동의 상태", "퇴역 경매", "Our Operating Procedure",
        ],
        "sop": [
            "Firebase Analytics 23.2.0", "Unity IAP 5.4 IAP Insights", "unity-iap-contact@unity3d.com",
            "AdMob SSV", "친구", "클랜", "카드 교환", "퇴역 경매", "90일",
        ],
        "support": [
            "발신 이메일 주소", "처리 완료 후 지체 없이 삭제", "up to three years",
            "../privacy-policy/privacy-ko.html", "../privacy-policy/delete-account.html",
        ],
    }
    for key, needles in required.items():
        for needle in needles:
            check(needle in texts[key], f"{FILES[key].name}: {needle}", failures)

    forbidden = {
        "ko": ["PvP 랭킹 표시에만 사용", "PvP 및 이용자 간 경매 운영", "Firebase Analytics (Snackcade에만 해당)"],
        "en": ["used only for PvP ranking display", "player-to-player auctions", "Firebase Analytics (Snackcade only)"],
    }
    for key, needles in forbidden.items():
        for needle in needles:
            check(needle not in texts[key], f"{FILES[key].name}: 퇴역 문구 없음 ({needle})", failures)

    check(texts["ko"].count("<tr>") == texts["en"].count("<tr>"), "한·영 제3자 표 행 수 일치", failures)
    check(texts["ko"].count("<h2>") == texts["en"].count("<h2>"), "한·영 대단원 수 일치", failures)
    check(texts["ko"].count("<li>") == texts["en"].count("<li>"), "한·영 목록 항목 수 일치", failures)
    check("July 20, 2026" in texts["index"], "법적 문서 색인 갱신일 일치", failures)

    for key in ("ko", "en", "delete", "index", "support"):
        parser = StructureParser()
        parser.feed(texts[key])
        parser.close()
        parser.finish()
        check(not parser.errors, f"HTML 태그 구조: {FILES[key].name}", failures)
        for href in re.findall(r'href=["\']([^"\']+)["\']', texts[key]):
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = (FILES[key].parent / href.split("#", 1)[0].split("?", 1)[0]).resolve()
            if href.endswith("/") or href == "./":
                target = target / "index.html"
            check(target.exists(), f"내부 링크 존재: {FILES[key].name} -> {href}", failures)

    combined = "\n".join(texts.values())
    secret_markers = ["AIza", "-----BEGIN PRIVATE KEY-----", "Bearer eyJ", "firebase-adminsdk-"]
    for marker in secret_markers:
        check(marker not in combined, f"비밀정보 표식 없음: {marker}", failures)

    if failures:
        print(f"\n검증 실패: {len(failures)}건")
        return 1
    print("\n검증 완료: 전수 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
