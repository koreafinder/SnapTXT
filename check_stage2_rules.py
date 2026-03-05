"""Stage2 SMOKE 규칙 추가 후 확인"""

from snaptxt.postprocess.patterns.stage2_rules import get_replacements

print('=== SMOKE 규칙 추가 후 확인 ===')
replacements = get_replacements(force_refresh=True)
print(f'총 규칙 수: {len(replacements)}')

# 스모크 규칙 확인
smoke_patterns = ['테스트입 니다', '입 니다', '했습 니다']
print('\n=== SMOKE 패턴 검색 ===')
for pattern in smoke_patterns:
    if pattern in replacements:
        print(f'FOUND: "{pattern}" -> "{replacements[pattern]}"')
    else:
        print(f'NOT FOUND: "{pattern}"')

print('\n=== overlay 파일 확인 ===')
from snaptxt.postprocess.patterns.stage2_overlay_loader import get_overlay_file_info
overlay_info = get_overlay_file_info()
print(f'현재 overlay: {overlay_info}')