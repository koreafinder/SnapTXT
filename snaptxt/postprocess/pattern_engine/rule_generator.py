"""규칙 생성기 - RuleGenerator

패턴 후보들을 YAML 규칙 형태로 변환하고,
승인된 규칙들을 실제 Stage2 규칙에 추가합니다.
"""

import yaml
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
import json

try:
    from .pattern_analyzer import PatternCandidate
except ImportError:
    # 타입 힌트용 임시
    PatternCandidate = object


class RuleGenerator:
    """패턴 후보를 YAML 규칙으로 변환"""
    
    def __init__(self, 
                 suggestions_path: str = "snaptxt/postprocess/patterns/auto_suggestions.yaml",
                 stage2_rules_path: str = "snaptxt/postprocess/patterns/stage2_rules.yaml"):
        
        self.suggestions_path = Path(suggestions_path)
        self.stage2_rules_path = Path(stage2_rules_path) 
        
        # 디렉토리 생성
        self.suggestions_path.parent.mkdir(parents=True, exist_ok=True)
        self.stage2_rules_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 설정
        self.auto_apply_threshold = 10   # 10회 이상은 자동 적용 제안
        self.high_confidence_threshold = 0.8  # 80% 이상은 고신뢰도
        
    def generate_rule_suggestions(self, candidates: List[PatternCandidate]) -> Dict:
        """패턴 후보들을 YAML 규칙 형태로 변환"""
        
        suggestions = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_candidates': len(candidates),
                'auto_apply_threshold': self.auto_apply_threshold,
                'high_confidence_threshold': self.high_confidence_threshold
            },
            'auto_apply': [],     # 자동 적용 추천 (고빈도 + 고신뢰도)
            'user_review': [],    # 사용자 검토 필요 (중간 신뢰도)
            'low_confidence': [], # 낮은 신뢰도 (참고용)
            'stage3_patterns': [] # Stage3에서 나온 패턴들 (Stage2 규칙화 고려용)
        }
        
        for i, candidate in enumerate(candidates):
            rule_entry = {
                'id': f"pattern_{i:03d}",  # 고유 ID
                'pattern': candidate.pattern,
                'replacement': candidate.replacement,
                'frequency': candidate.frequency,
                'confidence': round(candidate.confidence, 3),
                'examples': candidate.examples[:3],  # 최대 3개 예시
                'metadata': {
                    'first_seen': candidate.first_seen.isoformat(),
                    'last_seen': candidate.last_seen.isoformat(),
                    'source_stage': candidate.stage,
                    'source': 'auto_analysis',
                    'pattern_length': len(candidate.pattern)
                }
            }
            
            # 카테고리 분류
            if (candidate.frequency >= self.auto_apply_threshold and 
                candidate.confidence >= self.high_confidence_threshold):
                suggestions['auto_apply'].append(rule_entry)
                
            elif (candidate.frequency >= 5 and candidate.confidence >= 0.7):
                suggestions['user_review'].append(rule_entry)
                
            elif candidate.stage == 'stage3':
                # Stage3 패턴은 별도 카테고리 (Stage2 규칙 추가 고려용)
                suggestions['stage3_patterns'].append(rule_entry)
                
            else:
                suggestions['low_confidence'].append(rule_entry)
                
        # YAML 파일로 저장
        try:
            with open(self.suggestions_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(suggestions, f, allow_unicode=True, sort_keys=False, indent=2)
        except Exception as e:
            print(f"Warning: Could not save suggestions to {self.suggestions_path}: {e}")
            
        return suggestions
        
    def apply_approved_rules(self, approved_rule_ids: List[str]) -> bool:
        """승인된 규칙들을 실제 Stage2 규칙에 추가"""
        
        try:
            # 제안 규칙들 로드
            suggestions = self._load_suggestions()
            if not suggestions:
                return False
                
            # 기존 Stage2 규칙 로드
            existing_rules = self._load_stage2_rules()
            
            # 승인된 규칙들 찾아서 추가
            added_count = 0
            for rule_id in approved_rule_ids:
                rule_entry = self._find_rule_by_id(suggestions, rule_id)
                if rule_entry:
                    # Stage2 형식으로 변환하여 추가
                    stage2_rule = self._convert_to_stage2_format(rule_entry)
                    existing_rules['replacements'].append(stage2_rule)
                    added_count += 1
                    
            if added_count == 0:
                return False
                    
            # Stage2 규칙 파일 업데이트
            self._save_stage2_rules(existing_rules)
            
            # Hot reload 시도 (실패해도 무시)
            try:
                from ..patterns.stage2_rules import reload_replacements
                reload_replacements()
            except Exception:
                pass  # Hot reload 실패해도 파일은 저장됨
                
            # 적용된 규칙들을 제안 목록에서 제거 (선택적)
            self._mark_rules_as_applied(suggestions, approved_rule_ids)
            
            return True
            
        except Exception as e:
            print(f"Error applying rules: {e}")
            return False
            
    def _load_suggestions(self) -> Optional[Dict]:
        """저장된 제안 규칙들을 로드"""
        try:
            with open(self.suggestions_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}
        except Exception as e:
            print(f"Error loading suggestions: {e}")
            return {}
            
    def _load_stage2_rules(self) -> Dict:
        """기존 Stage2 규칙들을 로드"""
        try:
            with open(self.stage2_rules_path, 'r', encoding='utf-8') as f:
                rules = yaml.safe_load(f) or {}
                # 기본 구조 보장
                if 'replacements' not in rules:
                    rules['replacements'] = []
                return rules
        except FileNotFoundError:
            # 파일이 없으면 기본 구조 생성
            return {
                'metadata': {
                    'description': 'Stage 2 OCR 교정 규칙',
                    'created_at': datetime.now().isoformat()
                },
                'replacements': []
            }
        except Exception as e:
            print(f"Error loading Stage2 rules: {e}")
            return {'replacements': []}
            
    def _save_stage2_rules(self, rules: Dict) -> None:
        """Stage2 규칙들을 저장"""
        # 메타데이터 업데이트
        if 'metadata' not in rules:
            rules['metadata'] = {}
        rules['metadata']['last_updated'] = datetime.now().isoformat()
        
        with open(self.stage2_rules_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(rules, f, allow_unicode=True, sort_keys=False, indent=2)
            
    def _find_rule_by_id(self, suggestions: Dict, rule_id: str) -> Optional[Dict]:
        """규칙 ID로 규칙을 찾기"""
        for category in ['auto_apply', 'user_review', 'low_confidence', 'stage3_patterns']:
            for rule in suggestions.get(category, []):
                if rule.get('id') == rule_id:
                    return rule
        return None
        
    def _convert_to_stage2_format(self, rule_entry: Dict) -> Dict:
        """제안 규칙을 Stage2 형식으로 변환"""
        return {
            'pattern': rule_entry['pattern'],
            'replacement': rule_entry['replacement'],
            'metadata': {
                'source': 'auto_suggestion',
                'added_at': datetime.now().isoformat(),
                'original_frequency': rule_entry['frequency'],
                'original_confidence': rule_entry['confidence'],
                'rule_id': rule_entry['id']
            }
        }
        
    def _mark_rules_as_applied(self, suggestions: Dict, applied_rule_ids: List[str]) -> None:
        """적용된 규칙들을 표시 (선택적으로 제거하거나 표시)"""
        try:
            # applied_rules 섹션 추가
            if 'applied_rules' not in suggestions:
                suggestions['applied_rules'] = []
                
            # 적용된 규칙들을 applied_rules로 이동
            for rule_id in applied_rule_ids:
                for category in ['auto_apply', 'user_review', 'low_confidence', 'stage3_patterns']:
                    rules_list = suggestions.get(category, [])
                    for i, rule in enumerate(rules_list):
                        if rule.get('id') == rule_id:
                            # applied_rules로 이동
                            rule['applied_at'] = datetime.now().isoformat()
                            suggestions['applied_rules'].append(rule)
                            # 원래 카테고리에서 제거
                            rules_list.pop(i)
                            break
                            
            # 업데이트된 제안 규칙 저장
            with open(self.suggestions_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(suggestions, f, allow_unicode=True, sort_keys=False, indent=2)
                
        except Exception as e:
            print(f"Warning: Could not mark rules as applied: {e}")
            
    def get_suggestion_summary(self) -> Dict:
        """제안 규칙 요약 정보 반환"""
        suggestions = self._load_suggestions()
        
        if not suggestions:
            return {
                'total_suggestions': 0,
                'auto_apply': 0,
                'user_review': 0,
                'low_confidence': 0,
                'stage3_patterns': 0,
                'applied_rules': 0
            }
            
        return {
            'total_suggestions': sum(len(suggestions.get(cat, [])) 
                                   for cat in ['auto_apply', 'user_review', 'low_confidence', 'stage3_patterns']),
            'auto_apply': len(suggestions.get('auto_apply', [])),
            'user_review': len(suggestions.get('user_review', [])),
            'low_confidence': len(suggestions.get('low_confidence', [])),
            'stage3_patterns': len(suggestions.get('stage3_patterns', [])),
            'applied_rules': len(suggestions.get('applied_rules', [])),
            'last_generated': suggestions.get('metadata', {}).get('generated_at', 'Unknown')
        }