"""실시간 텍스트 변화 수집기 - DiffCollector

Stage2/3 처리 과정에서 발생하는 텍스트 변화를 실시간으로 수집하여
패턴 분석을 위한 데이터로 저장합니다.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
from pathlib import Path
from difflib import SequenceMatcher
import re


@dataclass
class TextDiff:
    """텍스트 변화 정보 - 세션 컨텍스트 강화"""
    before: str
    after: str
    change_type: str  # "replace", "insert", "delete"
    position: int
    confidence: float
    timestamp: datetime
    stage: str  # "stage2" or "stage3"
    
    # Phase 1.5: Session Context 필드들
    book_session_id: Optional[str] = None    # "20260302_bookA_batch1" 
    device_id: Optional[str] = None          # "iphone12_user1"
    capture_batch_id: Optional[str] = None   # 연속 촬영 세션 ID
    book_domain: Optional[str] = None        # "novel", "textbook", "magazine"
    image_quality: Optional[float] = None    # 이미지 품질 지표 (0.0~1.0)
    
    
@dataclass 
class StageResult:
    """각 Stage 처리 결과 - 세션 컨텍스트 강화"""
    original_text: str
    stage2_result: str
    stage3_result: str
    stage2_time: float
    stage3_time: float
    total_changes: int
    
    # Phase 1.5: Session Context 필드들
    book_session_id: Optional[str] = None    # "20260302_bookA_batch1"
    device_id: Optional[str] = None          # "iphone12_user1"
    capture_batch_id: Optional[str] = None   # 연속 촬영 세션 ID
    book_domain: Optional[str] = None        # "novel", "textbook", "magazine" 
    image_quality: Optional[float] = None    # 이미지 품질 지표 (0.0~1.0)
    capture_batch_id: Optional[str] = None 
    book_domain: Optional[str] = None
    image_quality: Optional[float] = None


class DiffCollector:
    """실시간 텍스트 변화 수집기"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.log_path = self.log_dir / "pattern_collection.jsonl"
        
        # 필터링 설정 - 더 관대한 기준으로 조정
        self.min_change_length = 1  # 1글자 변화도 수집 (공백, 마침표 등)
        self.max_change_length = 50  # 최대 50글자까지만 (전체 재작성 방지)
        self.min_confidence = 0.1  # 더 낮은 신뢰도 임계값
        
    def collect_stage_diffs(self, stage_result: StageResult) -> List[TextDiff]:
        """Stage 처리 결과에서 의미있는 diff들을 추출"""
        
        diffs = []
        
        # Stage2 diff 수집 (Stage2에서만 규칙 추가하므로 중요)
        stage2_diffs = self._extract_diffs(
            stage_result.original_text, 
            stage_result.stage2_result,
            "stage2",
            stage_result
        )
        diffs.extend(stage2_diffs)
        
        # Stage3 diff 수집 (참고용)  
        stage3_diffs = self._extract_diffs(
            stage_result.stage2_result,
            stage_result.stage3_result, 
            "stage3",
            stage_result
        )
        diffs.extend(stage3_diffs)
        
        # 의미있는 diff들만 필터링
        meaningful_diffs = [d for d in diffs if d.confidence >= self.min_confidence]
        
        # 수집한 diff들을 로그에 저장
        if meaningful_diffs:
            self._save_diffs_to_log(meaningful_diffs, stage_result)
        
        return meaningful_diffs
        
    def _extract_diffs(self, before: str, after: str, stage: str, stage_result: StageResult) -> List[TextDiff]:
        """두 텍스트 간의 의미있는 차이점들을 추출"""
        
        if before == after:
            return []
            
        diffs = []
        matcher = SequenceMatcher(None, before, after)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                continue
                
            before_segment = before[i1:i2]
            after_segment = after[j1:j2]
            
            # 길이 필터링
            change_size = max(len(before_segment), len(after_segment))
            if change_size < self.min_change_length or change_size > self.max_change_length:
                continue
                
            # 의미없는 변화 필터링 (공백만 변경, 대소문자만 변경 등)
            if not self._is_meaningful_change(before_segment, after_segment):
                continue
                
            diff = TextDiff(
                before=before_segment,
                after=after_segment,
                change_type=tag,
                position=i1,
                confidence=self._calculate_confidence(before_segment, after_segment),
                timestamp=datetime.now(),
                stage=stage,
                # Session Context 추가
                book_session_id=stage_result.book_session_id,
                device_id=stage_result.device_id,
                capture_batch_id=stage_result.capture_batch_id,
                book_domain=stage_result.book_domain,
                image_quality=stage_result.image_quality
            )
            diffs.append(diff)
            
        return diffs
        
    def _is_meaningful_change(self, before: str, after: str) -> bool:
        """의미있는 변화인지 판단 - OCR 후처리에 유용한 변화들을 더 관대하게 판단"""
        
        # 동일한 경우 제외
        if before == after:
            return False
            
        # 공백 정리나 띄어쓰기 교정은 유용한 변화로 인정
        before_normalized = ' '.join(before.split())  # 다중 공백 제거
        after_normalized = ' '.join(after.split())
        if before != after and before_normalized != after_normalized:
            return True  # 공백 패턴 변화는 항상 유용
            
        # 앞뒤 공백 제거/추가는 유용한 변화
        if before.strip() != after.strip():
            return True
            
        # 문장부호 변화 (마침표, 쉼표 등)는 유용한 변화
        if any(c in '.,!?;:' for c in before + after):
            return True
            
        # 대소문자 변경 - 한글이 포함된 경우는 유용할 수 있음
        if before.lower() != after.lower():
            if any('가' <= c <= '힣' for c in before + after):
                return True  # 한글 포함된 경우 대소문자 변화도 유용
                
        # 완전히 다른 텍스트인 경우 (길이 차이가 큰 경우)
        length_ratio = len(after) / max(len(before), 1)
        if length_ratio < 0.3 or length_ratio > 3.0:
            return True  # 대폭 변경은 유용한 패턴일 가능성
            
        # 한글이나 영문자가 포함되면 유용한 변화로 판단
        if any('가' <= c <= '힣' or c.isalpha() for c in before + after):
            return True
            
        return False
        
    def _calculate_confidence(self, before: str, after: str) -> float:
        """변화의 신뢰도 계산 (0.0 ~ 1.0) - OCR 후처리 맥락에 맞게 조정"""
        
        # 빈 문자열 처리 - 삭제/추가 작업에 기본 신뢰도 부여
        if not before:  # 텍스트 추가
            return 0.4 if len(after) <= 10 else 0.2
        if not after:   # 텍스트 삭제  
            return 0.4 if len(before) <= 10 else 0.2
            
        # 문자 유사도 계산
        similarity = SequenceMatcher(None, before, after).ratio()
        
        # 길이 차이 패널티 - 너무 가혹하지 않게 조정
        length_diff = abs(len(before) - len(after))
        max_length = max(len(before), len(after))
        length_penalty = (length_diff / max_length) * 0.2 if max_length > 0 else 0
        
        # 한글 변화는 신뢰도 증가
        korean_bonus = 0.0
        if any('가' <= c <= '힣' for c in before + after):
            korean_bonus = 0.15
            
        # 공백/문장부호 정리는 유용한 패턴으로 인정
        formatting_bonus = 0.0
        if any(c in ' \t\n.,!?;:' for c in before + after):
            # 공백 정리나 문장부호 변화
            if before.strip() != after.strip() or any(c in '.,!?;:' for c in before + after):
                formatting_bonus = 0.2
            
        # 일반적인 오타 패턴인지 확인
        typo_bonus = self._check_common_typo_patterns(before, after)
        
        # 기본 신뢰도는 0.3으로 시작 (너무 낮지 않게)
        base_confidence = 0.3
        confidence = base_confidence + similarity * 0.4 - length_penalty + korean_bonus + formatting_bonus + typo_bonus
        
        return max(0.1, min(1.0, confidence))  # 최소 0.1 보장
        
    def _check_common_typo_patterns(self, before: str, after: str) -> float:
        """일반적인 오타 패턴인지 확인하여 보너스 점수 부여"""
        
        # 자주 발생하는 오타 패턴들
        common_patterns = [
            # 한글 오타
            ('ㅏ', '가'), ('ㅓ', '어'), ('ㅗ', '오'), ('ㅜ', '우'),
            # 띄어쓰기
            ('되었습니다.', '되었습니다. '), ('입니다.', '입니다. '),
            # 영문 오타  
            ('teh', 'the'), ('adn', 'and'),
        ]
        
        for wrong, correct in common_patterns:
            if wrong in before and correct in after:
                return 0.2
            if correct in before and wrong in after:  # 잘못 교정한 경우
                return -0.1
                
        return 0.0
        
    def _save_diffs_to_log(self, diffs: List[TextDiff], stage_result: StageResult):
        """수집된 diff들을 JSONL 형태로 저장"""
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "original_length": len(stage_result.original_text),
            "total_changes": len(diffs),
            "stage2_time": stage_result.stage2_time,
            "stage3_time": stage_result.stage3_time,
            "diffs": [
                {
                    "before": diff.before,
                    "after": diff.after,
                    "type": diff.change_type,
                    "position": diff.position,
                    "confidence": diff.confidence,
                    "stage": diff.stage,
                    # Phase 1.5: Session Context 정보 포함
                    "book_session_id": diff.book_session_id,
                    "device_id": diff.device_id,
                    "capture_batch_id": diff.capture_batch_id,
                    "book_domain": diff.book_domain,
                    "image_quality": diff.image_quality,
                    "timestamp": diff.timestamp.isoformat() if diff.timestamp else None
                }
                for diff in diffs
            ]
        }
        
        # JSONL 형태로 추가 저장
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            # 로그 저장 실패해도 메인 프로세스에는 영향 없도록
            print(f"Pattern collection log save failed: {e}")
            
    def get_recent_stats(self, days: int = 7) -> Dict:
        """최근 N일간의 수집 통계 반환"""
        
        if not self.log_path.exists():
            return {"total_sessions": 0, "total_diffs": 0, "avg_diffs_per_session": 0}
            
        cutoff_date = datetime.now() - timedelta(days=days)
        total_sessions = 0
        total_diffs = 0
        
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        entry_date = datetime.fromisoformat(entry['timestamp'])
                        
                        if entry_date >= cutoff_date:
                            total_sessions += 1
                            total_diffs += entry.get('total_changes', 0)
                            
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
                        
        except FileNotFoundError:
            pass
            
        avg_diffs = total_diffs / total_sessions if total_sessions > 0 else 0
        
        return {
            "total_sessions": total_sessions,
            "total_diffs": total_diffs, 
            "avg_diffs_per_session": round(avg_diffs, 1)
        }