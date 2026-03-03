#!/usr/bin/env python3
"""
Phase 2.4: Book Profile Generation Engine
OCR Error Analyzer with 3-way diff and Error Event Schema

Purpose: 실제 OCR 오류 분석 → 유효한 교정 규칙 생성
Author: SnapTXT Team
"""

import re
import difflib
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

log = logging.getLogger(__name__)

@dataclass
class ErrorEvent:
    """OCR 오류 이벤트 - 규칙 생성에 바로 사용할 수 있는 형태"""
    bucket: str          # space/layout/punct/char
    before_span: str     # OCR 결과 스팬
    gt_span: str         # Ground Truth 스팬
    op: str              # insert/delete/replace
    context: str         # 앞뒤 10자 컨텍스트
    position_hint: dict  # line_idx, near_punct, near_digit 등
    stage_redundancy: str # redundant_with_stage2/3 or new_rule_candidate
    confidence: float    # 이 오류가 실제 오류일 확률
    frequency: int       # 같은 패턴이 발견된 횟수

class OCRErrorAnalyzer:
    """OCR 오류 분석 및 Stage 중복 감지 엔진"""
    
    def __init__(self):
        self.space_patterns = [
            r'(\w)\s+([은는이가을를에서의와과도로부터까지])',  # 조사 분리
            r'(\w)\s+(\w{1,2}[다요음니까])',                    # 어미 분리
            r'\s{2,}',                                          # 연속 공백
        ]
        
        self.punct_patterns = [
            r'["""]',      # 따옴표 정규화
            r"[''']",      # 어포스트로피
            r'[…․·]',      # 말줄임표/가운뎃점
        ]
        
        self.char_confusion = {
            # 자주 혼동되는 문자들 (OCR 특성상)
            'o': ['O', '0'],
            'l': ['I', '1'],
            'rn': 'm',
            # 한글 특화
            '온': '음',
            '읍': '음',
        }
    
    def analyze_errors(self, raw_ocr: str, after_stage2: str, 
                      after_stage3: str, gt_text: str) -> List[ErrorEvent]:
        """3-way diff를 통한 OCR 오류 분석"""
        
        log.info(f"🔍 OCR 오류 분석 시작")
        log.info(f"   📊 raw_ocr: {len(raw_ocr)}자")
        log.info(f"   📊 after_stage2: {len(after_stage2)}자") 
        log.info(f"   📊 after_stage3: {len(after_stage3)}자")
        log.info(f"   📊 gt_text: {len(gt_text)}자")
        
        error_events = []
        
        # 1. GT와 각 단계별 차이점 추출
        raw_diffs = self._get_text_diffs(raw_ocr, gt_text)
        stage2_diffs = self._get_text_diffs(after_stage2, gt_text) 
        stage3_diffs = self._get_text_diffs(after_stage3, gt_text)
        
        # 2. Stage 변화 추적
        stage2_changes = self._get_stage_changes(raw_ocr, after_stage2)
        stage3_changes = self._get_stage_changes(after_stage2, after_stage3)
        
        log.info(f"   📊 GT 차이: raw({len(raw_diffs)}), stage2({len(stage2_diffs)}), stage3({len(stage3_diffs)})")
        log.info(f"   📊 Stage 변화: stage2({len(stage2_changes)}), stage3({len(stage3_changes)})")
        
        # 3. 각 오류에 대해 Stage 중복성 검사 및 이벤트 생성
        for diff in raw_diffs:
            error_event = self._create_error_event(
                diff, raw_ocr, gt_text, stage2_changes, stage3_changes
            )
            if error_event:
                error_events.append(error_event)
        
        log.info(f"   ✅ {len(error_events)}개 에러 이벤트 생성")
        return error_events
    
    def _get_text_diffs(self, text1: str, text2: str) -> List[Dict]:
        """두 텍스트 간 차이점 추출"""
        diffs = []
        matcher = difflib.SequenceMatcher(None, text1, text2)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != 'equal':
                diffs.append({
                    'op': tag,  # 'replace', 'delete', 'insert'
                    'before': text1[i1:i2],
                    'after': text2[j1:j2],
                    'pos': (i1, i2, j1, j2),
                    'context': self._get_context(text1, i1, i2)
                })
        
        return diffs
    
    def _get_stage_changes(self, before: str, after: str) -> List[Dict]:
        """Stage 적용으로 인한 변화 추출"""
        return self._get_text_diffs(before, after)
    
    def _get_context(self, text: str, start: int, end: int, context_len: int = 10) -> str:
        """오류 위치 주변 컨텍스트 추출"""
        context_start = max(0, start - context_len)
        context_end = min(len(text), end + context_len)
        
        before_context = text[context_start:start]
        error_span = text[start:end]
        after_context = text[end:context_end]
        
        return f"{before_context}[{error_span}]{after_context}"
    
    def _detect_stage_redundancy(self, diff: Dict, stage2_changes: List[Dict], 
                                stage3_changes: List[Dict]) -> str:
        """Stage 중복성 검사 - 핵심 로직"""
        
        before_span = diff['before']
        after_span = diff['after']
        
        # Stage2에서 이미 이 패턴을 처리했는가?
        for stage2_change in stage2_changes:
            if (stage2_change['before'] == before_span and 
                stage2_change['after'] == after_span):
                return "redundant_with_stage2"
            
            # 부분 매칭도 체크 (공백 처리 등)
            if (before_span in stage2_change['before'] and 
                after_span in stage2_change['after']):
                return "redundant_with_stage2"
        
        # Stage3에서 이미 이 패턴을 처리했는가?
        for stage3_change in stage3_changes:
            if (stage3_change['before'] == before_span and 
                stage3_change['after'] == after_span):
                return "redundant_with_stage3"
                
            if (before_span in stage3_change['before'] and 
                after_span in stage3_change['after']):
                return "redundant_with_stage3"
        
        # 새로운 규칙 후보!
        return "new_rule_candidate"
    
    def _classify_error_bucket(self, before: str, after: str) -> str:
        """오류를 4개 버킷으로 분류"""
        
        # 공백 관련 오류
        if re.search(r'\s', before + after):
            if len(before.split()) != len(after.split()):
                return "space"
            if before.replace(' ', '') == after.replace(' ', ''):
                return "space"
        
        # 줄바꿈/레이아웃 오류
        if '\n' in before + after or '\r' in before + after:
            return "layout"
        
        # 구두점 오류
        punct_chars = set('.,!?;:""''()[]{}…․·-–—')
        if any(c in punct_chars for c in before + after):
            return "punct"
        
        # 문자 오류 (기본값)
        return "char"
    
    def _create_error_event(self, diff: Dict, raw_ocr: str, gt_text: str,
                           stage2_changes: List[Dict], stage3_changes: List[Dict]) -> Optional[ErrorEvent]:
        """Diff 정보로부터 ErrorEvent 생성"""
        
        before_span = diff['before']
        gt_span = diff['after']
        
        # 빈 span 무시
        if not before_span and not gt_span:
            return None
        
        # Stage 중복성 검사
        redundancy = self._detect_stage_redundancy(diff, stage2_changes, stage3_changes)
        
        # 오류 버킷 분류
        bucket = self._classify_error_bucket(before_span, gt_span)
        
        # 오퍼레이션 결정
        op = diff['op']  # 'replace', 'delete', 'insert'
        
        # 위치 힌트 생성
        pos = diff['pos']
        position_hint = {
            'start_pos': pos[0],
            'end_pos': pos[1], 
            'near_punct': self._has_nearby_punct(raw_ocr, pos[0], pos[1]),
            'line_break_nearby': self._has_nearby_linebreak(raw_ocr, pos[0], pos[1])
        }
        
        # 신뢰도 계산 (간단한 휴리스틱)
        confidence = self._calculate_confidence(before_span, gt_span, bucket)
        
        return ErrorEvent(
            bucket=bucket,
            before_span=before_span,
            gt_span=gt_span,
            op=op,
            context=diff['context'],
            position_hint=position_hint,
            stage_redundancy=redundancy,
            confidence=confidence,
            frequency=1  # 추후 클러스터링에서 계산
        )
    
    def _has_nearby_punct(self, text: str, start: int, end: int, radius: int = 5) -> bool:
        """주변에 구두점이 있는가?"""
        context_start = max(0, start - radius)
        context_end = min(len(text), end + radius)
        context = text[context_start:context_end]
        
        punct_chars = set('.,!?;:""''()[]{}')
        return any(c in punct_chars for c in context)
    
    def _has_nearby_linebreak(self, text: str, start: int, end: int, radius: int = 10) -> bool:
        """주변에 줄바꿈이 있는가?"""
        context_start = max(0, start - radius)
        context_end = min(len(text), end + radius)
        context = text[context_start:context_end]
        
        return '\n' in context or '\r' in context
    
    def _calculate_confidence(self, before: str, after: str, bucket: str) -> float:
        """오류 신뢰도 계산"""
        
        # 기본 신뢰도
        confidence = 0.5
        
        # 공백 오류는 신뢰도 높음
        if bucket == "space":
            confidence = 0.8
        
        # 길이 차이가 클수록 신뢰도 높음
        length_diff = abs(len(before) - len(after))
        confidence += min(0.3, length_diff * 0.1)
        
        # 특수 패턴 매칭
        if re.search(r'[은는이가을를에서의와과도로부터까지]', after):
            confidence += 0.2  # 조사 관련은 신뢰도 높음
        
        return min(1.0, confidence)
    
    def analyze_and_report(self, raw_ocr: str, after_stage2: str, 
                          after_stage3: str, gt_text: str) -> Dict:
        """분석 실행 및 보고서 생성"""
        
        log.info("🚀 Phase 2.4 OCR Error Analysis 시작")
        
        # 에러 이벤트 분석
        error_events = self.analyze_errors(raw_ocr, after_stage2, after_stage3, gt_text)
        
        # 통계 계산
        bucket_stats = {}
        redundancy_stats = {}
        
        for event in error_events:
            # Bucket별 통계
            if event.bucket not in bucket_stats:
                bucket_stats[event.bucket] = []
            bucket_stats[event.bucket].append(event)
            
            # 중복성별 통계
            if event.stage_redundancy not in redundancy_stats:
                redundancy_stats[event.stage_redundancy] = []
            redundancy_stats[event.stage_redundancy].append(event)
        
        # 새 규칙 후보 필터링
        new_rule_candidates = [e for e in error_events if e.stage_redundancy == "new_rule_candidate"]
        
        # 보고서 생성
        report = {
            'total_errors': len(error_events),
            'bucket_breakdown': {bucket: len(events) for bucket, events in bucket_stats.items()},
            'redundancy_breakdown': {red: len(events) for red, events in redundancy_stats.items()},
            'new_rule_candidates': len(new_rule_candidates),
            'bucket_details': bucket_stats,
            'redundancy_details': redundancy_stats,
            'top_candidates': sorted(new_rule_candidates, key=lambda x: x.confidence, reverse=True)[:10]
        }
        
        # 로그 출력
        log.info("📊 OCR Error Analysis 완료")
        log.info(f"   📊 총 오류: {report['total_errors']}개")
        log.info(f"   📊 버킷별: {report['bucket_breakdown']}")
        log.info(f"   📊 중복성: {report['redundancy_breakdown']}")  
        log.info(f"   🎯 새 규칙 후보: {report['new_rule_candidates']}개")
        
        if new_rule_candidates:
            log.info("   🔥 Top 새 규칙 후보:")
            for i, candidate in enumerate(report['top_candidates'][:5]):
                log.info(f"      {i+1}. [{candidate.bucket}] '{candidate.before_span}' → '{candidate.gt_span}' (신뢰도: {candidate.confidence:.2f})")
        
        return report


if __name__ == "__main__":
    # 간단한 테스트
    logging.basicConfig(level=logging.INFO)
    
    analyzer = OCRErrorAnalyzer()
    
    # 테스트 데이터 (IMG_4990 터미널 로그 기반)
    raw_ocr = "인식하게 되니다: 두려웅이 생겨나고 안팎의 갈등은 일상이 덥니다' 존재와의 연결을 방해하는 가장 근 결림돌은 마음과 자"
    after_stage2 = "인식하게 되니다: 두려웅이 생겨나고 안팎의 갈등은 일상이 덥니다' 존재와의 연결을 방해하는 가장 근 결림돌은 마음과 자" 
    after_stage3 = "인식하게 되니다: 두려웅이 생겨나고 안팎의 갈등은 일상이 덥니다' 존재와의 연결을 방해하는 가장 근 결림돌은 마음과 자"
    gt_text = "인식하게 됩니다: 두려움이 생겨나고 안팎의 갈등은 일상이 됩니다. 존재와의 연결을 방해하는 가장 큰 걸림돌은 마음과 자"
    
    # 분석 실행
    report = analyzer.analyze_and_report(raw_ocr, after_stage2, after_stage3, gt_text)
    
    print("\n🎯 Phase 2.4 OCR Error Analysis 결과:")
    print(f"   새 규칙 후보: {report['new_rule_candidates']}개")
    print(f"   Stage 중복 제거: {report['redundancy_breakdown']}")