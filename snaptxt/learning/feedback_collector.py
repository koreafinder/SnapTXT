#!/usr/bin/env python3
"""
Phase 2: 사용자 피드백 수집 시스템

PC 앱에서 사용자가 OCR 결과를 수정할 때 피드백을 수집하여
새로운 후처리 패턴을 자동으로 학습하는 시스템
"""

import json
import os
import re
import time
import difflib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class UserFeedbackCollector:
    """사용자 피드백 수집 및 패턴 분석"""
    
    def __init__(self):
        self.feedback_dir = Path("feedback_data")
        self.feedback_dir.mkdir(exist_ok=True)
        
        self.patterns_file = self.feedback_dir / "learned_patterns.json"
        self.feedback_log = self.feedback_dir / "user_feedback.jsonl"
        
    def collect_user_correction(self, 
                               original_text: str, 
                               corrected_text: str,
                               image_source: str,
                               user_id: str = "default") -> Dict:
        """사용자 수정사항 수집 및 분석"""
        
        if original_text.strip() == corrected_text.strip():
            return {"feedback_type": "no_change", "patterns": []}
        
        # 차이점 분석
        differences = self._analyze_text_differences(original_text, corrected_text)
        
        # 패턴 추출
        patterns = self._extract_correction_patterns(differences)
        
        # 피드백 데이터 구성
        feedback_data = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "image_source": image_source,
            "original_text": original_text,
            "corrected_text": corrected_text,
            "differences": differences,
            "extracted_patterns": patterns,
            "text_length": len(original_text),
            "correction_count": len(differences)
        }
        
        # 로그 저장
        self._save_feedback_log(feedback_data)
        
        # 패턴 학습
        self._update_learned_patterns(patterns)
        
        print(f"📝 피드백 수집: {len(differences)}개 수정사항, {len(patterns)}개 패턴 추출")
        
        return feedback_data
    
    def _analyze_text_differences(self, original: str, corrected: str) -> List[Dict]:
        """텍스트 차이점 상세 분석"""
        differences = []
        
        # difflib를 사용한 차이점 분석
        differ = difflib.SequenceMatcher(None, original, corrected)
        
        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            if tag == 'replace':
                old_text = original[i1:i2]
                new_text = corrected[j1:j2]
                
                if old_text.strip() and new_text.strip():
                    difference = {
                        "type": "replacement",
                        "old_text": old_text,
                        "new_text": new_text,
                        "position": i1,
                        "context_before": original[max(0, i1-10):i1],
                        "context_after": original[i2:i2+10],
                        "correction_type": self._classify_correction_type(old_text, new_text)
                    }
                    differences.append(difference)
            
            elif tag == 'delete':
                deleted_text = original[i1:i2]
                if deleted_text.strip():
                    differences.append({
                        "type": "deletion", 
                        "old_text": deleted_text,
                        "new_text": "",
                        "position": i1,
                        "correction_type": "removal"
                    })
                    
            elif tag == 'insert':
                inserted_text = corrected[j1:j2]
                if inserted_text.strip():
                    differences.append({
                        "type": "insertion",
                        "old_text": "", 
                        "new_text": inserted_text,
                        "position": i1,
                        "correction_type": "addition"
                    })
        
        return differences
    
    def _classify_correction_type(self, old_text: str, new_text: str) -> str:
        """수정 유형 분류"""
        old = old_text.strip()
        new = new_text.strip()
        
        # 띄어쓰기 수정
        if old.replace(" ", "") == new.replace(" ", ""):
            if len(old.split()) < len(new.split()):
                return "spacing_split"  # 띄어쓰기 추가
            else:
                return "spacing_merge"  # 띄어쓰기 제거
        
        # 단어 교체 (길이 비슷)
        if abs(len(old) - len(new)) <= 2:
            return "word_replacement"
        
        # 문자 수정 
        if len(old) == len(new):
            return "character_replacement"
        
        # 어미/접사 수정
        if (old.endswith(new[:len(old)//2]) or 
            new.endswith(old[:len(new)//2])):
            return "suffix_correction"
            
        return "general_correction"
    
    def _extract_correction_patterns(self, differences: List[Dict]) -> List[Dict]:
        """수정사항에서 재사용 가능한 패턴 추출"""
        patterns = []
        
        for diff in differences:
            old_text = diff.get("old_text", "").strip()
            new_text = diff.get("new_text", "").strip()
            correction_type = diff.get("correction_type", "")
            
            if not old_text or not new_text:
                continue
                
            # 정규식 패턴 생성 시도
            regex_pattern = self._create_regex_pattern(old_text, correction_type)
            
            if regex_pattern:
                pattern = {
                    "pattern": regex_pattern,
                    "replacement": new_text,
                    "category": self._map_correction_to_category(correction_type),
                    "original_example": old_text,
                    "confidence": self._calculate_pattern_confidence(old_text, new_text),
                    "learned_at": datetime.now().isoformat(),
                    "frequency": 1,
                    "correction_type": correction_type
                }
                patterns.append(pattern)
        
        return patterns
    
    def _create_regex_pattern(self, text: str, correction_type: str) -> Optional[str]:
        """텍스트에서 정규식 패턴 생성"""
        
        if correction_type == "spacing_split":
            # 띄어쓰기가 필요한 패턴 - 공백을 \\s*로 대체
            return text.replace(" ", r"\s*")
            
        elif correction_type == "character_replacement":
            # 특정 문자 교체는 정확한 매치만
            return re.escape(text)
            
        elif correction_type == "word_replacement":
            # 단어 교체는 단어 경계 고려
            return rf"\b{re.escape(text)}\b"
            
        elif correction_type == "suffix_correction":
            # 어미 수정은 정확한 매치
            return re.escape(text)
            
        else:
            # 기타 경우는 정확한 매치
            return re.escape(text)
    
    def _map_correction_to_category(self, correction_type: str) -> str:
        """수정 유형을 stage3 카테고리로 매핑"""
        mapping = {
            "spacing_split": "spacing",
            "spacing_merge": "spacing", 
            "character_replacement": "characters",
            "word_replacement": "characters",
            "suffix_correction": "characters",
            "general_correction": "characters"
        }
        return mapping.get(correction_type, "characters")
    
    def _calculate_pattern_confidence(self, old_text: str, new_text: str) -> float:
        """패턴 신뢰도 계산"""
        base_confidence = 0.5
        
        # 확실한 패턴들에 대해 신뢰도 증가
        if len(old_text) >= 3 and len(new_text) >= 3:
            base_confidence += 0.2
            
        # 자주 발생하는 한국어 오류 패턴 감지
        korean_error_patterns = [
            ("드러워집니다", "드러납니다"),
            ("드러워습니다", "드러났습니다"),
            ("돌두", "몰두"),
            ("명 상", "명상"),
            ("마이 클", "마이클")
        ]
        
        for error_pattern, correct_pattern in korean_error_patterns:
            if error_pattern in old_text and correct_pattern in new_text:
                base_confidence += 0.3
                break
        
        return min(base_confidence, 0.95)  # 최대 95%
    
    def _save_feedback_log(self, feedback_data: Dict):
        """피드백 로그 저장"""
        with open(self.feedback_log, 'a', encoding='utf-8') as f:
            json.dump(feedback_data, f, ensure_ascii=False)
            f.write('\n')
    
    def _update_learned_patterns(self, patterns: List[Dict]):
        """학습된 패턴 업데이트"""
        # 기존 학습 패턴 로드
        existing_patterns = {}
        if self.patterns_file.exists():
            with open(self.patterns_file, 'r', encoding='utf-8') as f:
                existing_patterns = json.load(f)
        
        # 새 패턴 추가/업데이트
        for pattern in patterns:
            pattern_key = f"{pattern['pattern']}→{pattern['replacement']}"
            
            if pattern_key in existing_patterns:
                # 기존 패턴 빈도 증가
                existing_patterns[pattern_key]['frequency'] += 1
                # 신뢰도 점진적 증가
                current_conf = existing_patterns[pattern_key]['confidence']
                existing_patterns[pattern_key]['confidence'] = min(current_conf + 0.1, 0.95)
            else:
                # 새 패턴 추가
                existing_patterns[pattern_key] = pattern
        
        # 저장
        with open(self.patterns_file, 'w', encoding='utf-8') as f:
            json.dump(existing_patterns, f, ensure_ascii=False, indent=2)
    
    def get_high_confidence_patterns(self, min_confidence: float = 0.7, min_frequency: int = 2) -> List[Dict]:
        """높은 신뢰도의 학습된 패턴 반환"""
        if not self.patterns_file.exists():
            return []
            
        with open(self.patterns_file, 'r', encoding='utf-8') as f:
            all_patterns = json.load(f)
        
        high_confidence = []
        for pattern_data in all_patterns.values():
            if (pattern_data['confidence'] >= min_confidence and 
                pattern_data['frequency'] >= min_frequency):
                high_confidence.append(pattern_data)
        
        # 신뢰도 순으로 정렬
        high_confidence.sort(key=lambda x: x['confidence'], reverse=True)
        
        return high_confidence
    
    def generate_stage3_rules_update(self) -> Dict:
        """학습된 패턴을 stage3_rules.yaml 업데이트로 변환"""
        patterns = self.get_high_confidence_patterns()
        
        if not patterns:
            return {"message": "업데이트할 고신뢰도 패턴이 없습니다"}
        
        # 카테고리별로 분류
        rules_update = {
            "spacing": [],
            "characters": [],
            "punctuation": [],
            "formatting": []
        }
        
        for pattern in patterns:
            category = pattern.get('category', 'characters')
            
            rule = {
                "pattern": pattern['pattern'],
                "replacement": pattern['replacement'],
                "description": f"사용자 학습: {pattern['original_example']} → {pattern['replacement']}",
                "confidence": pattern['confidence'],
                "frequency": pattern['frequency'],
                "user_learned": True,
                "learned_at": pattern['learned_at']
            }
            
            if category in rules_update:
                rules_update[category].append(rule)
        
        total_rules = sum(len(rules_update[cat]) for cat in rules_update)
        
        return {
            "update_available": total_rules > 0,
            "total_new_rules": total_rules,
            "rules_by_category": rules_update,
            "summary": f"{total_rules}개 새로운 사용자 학습 규칙 준비됨"
        }


def main():
    """테스트 실행"""
    collector = UserFeedbackCollector()
    
    # 샘플 피드백 테스트
    original = "마이 클 싱 어는 유명한 명 상 가입니다. 연구 결과가 드러워습니다."
    corrected = "마이클 싱어는 유명한 명상가입니다. 연구 결과가 드러났습니다."
    
    feedback = collector.collect_user_correction(
        original, corrected, "sample_image.jpg"
    )
    
    print(f"수집된 피드백: {feedback['correction_count']}개 수정사항")
    
    # 학습된 패턴 확인
    patterns = collector.get_high_confidence_patterns(min_confidence=0.3, min_frequency=1)
    print(f"학습된 패턴: {len(patterns)}개")
    
    # Stage3 규칙 업데이트 생성
    update = collector.generate_stage3_rules_update()
    print(f"업데이트 준비: {update.get('summary', '없음')}")


if __name__ == "__main__":
    main()