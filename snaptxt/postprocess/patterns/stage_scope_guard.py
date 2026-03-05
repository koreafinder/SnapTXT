"""Stage2/Stage3 현상 기반 스코프 가드 - 패턴별 중복 방지"""
import re
import hashlib
from collections import Counter
from typing import Set, Optional
from dataclasses import dataclass, field

# Stage 식별자 상수 (오타 방지)
STAGE2 = "S2"
STAGE3 = "S3"

@dataclass
class StageCounter:
    """명확한 메트릭 분리"""
    rules_applied: int = 0
    chars_changed: int = 0  # len(output) - len(input)
    top_patterns: Counter = field(default_factory=Counter)

@dataclass
class StageMetadata:
    """패턴별 스코프 기반 중복 방지 (감독관 지시 5번 반영)"""
    applied_scope_keys: Set[str] = field(default_factory=set)  # 패턴별 중복 방지
    stage2_counter: StageCounter = field(default_factory=StageCounter)
    stage3_counter: StageCounter = field(default_factory=StageCounter)

def classify_phenomenon(pattern: str, replacement: str) -> str:
    """패턴을 현상 기준으로 분류"""
    
    # 어미 정규화 (Stage3 전담)
    if re.search(r'(니다|습니다|했습니다|합니다|ㅂ니다)', pattern + replacement):
        return "ending_normalization"
    
    # 띄어쓰기 문맥 (Stage3 전담)
    if " " in pattern and len(pattern) > 2:
        return "spacing_context"
    
    # 자모 깨짐 복원 (Stage2 전담)
    if len(pattern) == 1 and len(replacement) == 1:
        return "broken_jamo"
    
    # 공백 오삽입 (Stage2 전담)
    if " " in pattern and len(pattern) <= 2:
        return "broken_space"
    
    # 영숫자 혼동 (협력)
    if re.search(r'[0-9]', pattern) and re.search(r'[a-zA-Z]', pattern):
        return "alnum_confusion"
    
    # 일반 단어 교정 (협력)
    return "word_correction"

def generate_scope_key(pattern: str, replacement: str) -> str:
    """현상 + 패턴해시로 정밀한 scope key (감독관 지시 5번 완전 반영)"""
    phenomenon = classify_phenomenon(pattern, replacement)
    
    # 패턴→교체 해시로 개별 규칙 식별
    pattern_hash = hashlib.md5(f"{pattern}→{replacement}".encode()).hexdigest()[:6]
    
    return f"{phenomenon}:{pattern_hash}"

def get_scope_policy(phenomenon: str, stage: str) -> str:
    """현상 기반 스코프 정책"""
    
    STAGE2_EXCLUSIVE = {"broken_jamo", "broken_space"}
    STAGE3_EXCLUSIVE = {"ending_normalization", "spacing_context"}
    
    if phenomenon in STAGE2_EXCLUSIVE:
        return "stage2_only" if stage == STAGE2 else "forbidden"
    elif phenomenon in STAGE3_EXCLUSIVE:
        return "stage3_only" if stage == STAGE3 else "forbidden" 
    else:
        return "cooperative"  # alnum_confusion, word_correction

def should_apply_rule(stage: str, pattern: str, replacement: str, metadata: StageMetadata) -> bool:
    """패턴별 중복 방지 (현상레벨 차단 금지)"""
    scope_key = generate_scope_key(pattern, replacement)
    
    # 이미 동일 패턴이 적용되었는지 확인
    if scope_key in metadata.applied_scope_keys:
        return False
    
    phenomenon = classify_phenomenon(pattern, replacement)
    policy = get_scope_policy(phenomenon, stage)
    
    # 정확한 정책 매칭 (stage2_only, stage3_only, cooperative, forbidden)
    if policy == "stage2_only" and stage == STAGE2:
        return True
    elif policy == "stage3_only" and stage == STAGE3:
        return True
    elif policy == "cooperative":
        return True  # 협력 정책은 항상 허용
    elif policy == "forbidden":
        return False
    else:
        return False

def mark_rule_applied(stage: str, pattern: str, replacement: str, 
                     char_diff: int, metadata: StageMetadata):
    """규칙 적용 기록 (chars_changed==0도 rules_applied 증가 - 감독관 지시)"""
    scope_key = generate_scope_key(pattern, replacement)
    metadata.applied_scope_keys.add(scope_key)
    
    counter = metadata.stage2_counter if stage == STAGE2 else metadata.stage3_counter
    counter.rules_applied += 1  # char_diff==0이어도 적용 카운트
    counter.chars_changed += char_diff  # 별도 누적
    counter.top_patterns[pattern[:10]] += 1

def log_stage_summary(metadata: StageMetadata, logger):
    """Stage별 1줄 요약"""
    s2 = metadata.stage2_counter
    s3 = metadata.stage3_counter
    
    s2_top3 = [name for name, count in s2.top_patterns.most_common(3)]
    s3_top3 = [name for name, count in s3.top_patterns.most_common(3)]
    
    logger.info(f"📈 Stage2: rules={s2.rules_applied}, chars={s2.chars_changed:+d}, top3={s2_top3}")
    logger.info(f"📈 Stage3: rules={s3.rules_applied}, chars={s3.chars_changed:+d}, top3={s3_top3}")

# 테스트용 디버그 함수
def debug_scope_metadata(metadata: StageMetadata):
    """스코프 메타데이터 디버깅"""
    print(f"🔍 Applied Scope Keys: {len(metadata.applied_scope_keys)}")
    for key in list(metadata.applied_scope_keys)[:5]:  # 처음 5개만
        print(f"   - {key}")
    
    print(f"🔍 Stage2: {metadata.stage2_counter.rules_applied} rules, {metadata.stage2_counter.chars_changed:+d} chars")
    print(f"🔍 Stage3: {metadata.stage3_counter.rules_applied} rules, {metadata.stage3_counter.chars_changed:+d} chars")