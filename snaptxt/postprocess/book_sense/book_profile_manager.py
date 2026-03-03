"""
📋 Book Profile Management System - Phase 2 Book Sense Engine 

Purpose: GPT 생성 교정 기준을 YAML로 저장/관리하는 시스템
Innovation: 사용자 친화적 + 버전 관리 + Pattern Scope Policy 연동

Core Features:
- YAML 형태로 가독성 높은 교정 기준 저장
- 사용자 검토/수정 가능한 구조
- 버전 관리 및 점진적 개선 지원
- Pattern Scope Policy와 연동한 안전한 적용
- 다중 책 프로파일 통합 관리

Author: SnapTXT Team  
Date: 2026-03-02
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Union
import yaml
import json
import os
import hashlib
from datetime import datetime
from pathlib import Path

from .gpt_standard_generator import BookCorrectionStandard, CorrectionRule
from .book_fingerprint import BookFingerprint


class BookProfileManager:
    """책별 프로파일을 YAML로 관리하는 시스템"""
    
    def __init__(self, profiles_dir: str = "book_profiles"):
        """초기화"""
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(exist_ok=True)
        
        # 프로파일 캐시
        self._profile_cache: Dict[str, Dict] = {}
        
        # YAML 설정
        self.yaml_config = {
            'default_flow_style': False,
            'allow_unicode': True,
            'indent': 2,
            'width': 100
        }
    
    def create_book_profile(self, fingerprint: BookFingerprint, 
                          standard: BookCorrectionStandard, 
                          user_title: Optional[str] = None) -> str:
        """Book Profile YAML 파일 생성"""
        
        # 사용자 지정 제목 또는 자동 생성
        book_title = user_title or self._generate_book_title(fingerprint, standard)
        
        # YAML 구조 생성
        profile_data = {
            'book_info': {
                'book_id': fingerprint.book_id,
                'title': book_title,
                'domain': fingerprint.content.domain.value,
                'language_style': fingerprint.content.language_style.value,
                'created_at': standard.generated_at,
                'fingerprint_hash': fingerprint.fingerprint_hash
            },
            'analysis_summary': {
                'total_rules': len(standard.correction_rules),
                'confidence_score': round(standard.confidence_score, 3),
                'avg_ocr_confidence': round(fingerprint.quality.avg_confidence, 3),
                'sample_count': fingerprint.sample_count,
                'approval_required_rules': len([r for r in standard.correction_rules if r.requires_approval])
            },
            'typography_profile': {
                'avg_line_length': round(fingerprint.typography.avg_line_length, 1),
                'paragraph_style': fingerprint.typography.paragraph_break_pattern,
                'formatting_style': fingerprint.typography.formatting_style,
                'punctuation_density': {k: round(v, 4) for k, v in fingerprint.typography.punctuation_density.items() if v > 0}
            },
            'correction_rules': self._format_correction_rules(standard),
            'priority_matrix': {
                'critical': self._get_rules_by_priority(standard, 'critical'),
                'high': self._get_rules_by_priority(standard, 'high'),
                'medium': self._get_rules_by_priority(standard, 'medium'),
                'low': self._get_rules_by_priority(standard, 'low')
            },
            'user_settings': {
                'profile_approved': False,
                'auto_apply_safe_rules': True,
                'require_confirmation_for': ['high_risk', 'domain_wide', 'universal'],
                'disabled_rules': [],
                'custom_rules': []
            },
            'version_info': {
                'version': '1.0.0',
                'last_updated': datetime.now().isoformat(),
                'gpt_model_used': 'gpt-4-simulation',
                'created_by': 'SnapTXT Book Sense Engine v2.0'
            },
            'usage_stats': {
                'applied_count': 0,
                'success_count': 0,
                'user_overrides': 0,
                'performance_score': 0.0
            }
        }
        
        # YAML 파일 생성
        profile_filename = f"book_{fingerprint.book_id}.yaml"
        profile_path = self.profiles_dir / profile_filename
        
        with open(profile_path, 'w', encoding='utf-8') as f:
            yaml.dump(profile_data, f, **self.yaml_config)
            
        # 캐시 업데이트
        self._profile_cache[fingerprint.book_id] = profile_data
        
        return str(profile_path)
    
    def load_book_profile(self, book_id: str) -> Optional[Dict]:
        """책 프로파일 로드"""
        
        # 캐시에서 먼저 확인
        if book_id in self._profile_cache:
            return self._profile_cache[book_id]
            
        # YAML 파일에서 로드
        profile_path = self.profiles_dir / f"book_{book_id}.yaml"
        
        if not profile_path.exists():
            return None
            
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile_data = yaml.safe_load(f)
                
            self._profile_cache[book_id] = profile_data
            return profile_data
            
        except Exception as e:
            print(f"프로파일 로드 실패 {book_id}: {e}")
            return None
    
    def update_profile_settings(self, book_id: str, settings: Dict) -> bool:
        """사용자 설정 업데이트"""
        
        profile = self.load_book_profile(book_id)
        if not profile:
            return False
            
        # 설정 업데이트
        profile['user_settings'].update(settings)
        profile['version_info']['last_updated'] = datetime.now().isoformat()
        
        # 버전 증가
        current_version = profile['version_info']['version']
        major, minor, patch = current_version.split('.')
        profile['version_info']['version'] = f"{major}.{minor}.{int(patch)+1}"
        
        # 파일 저장
        return self._save_profile(book_id, profile)
    
    def add_custom_rule(self, book_id: str, rule_dict: Dict) -> bool:
        """사용자 정의 교정 규칙 추가"""
        
        profile = self.load_book_profile(book_id)
        if not profile:
            return False
            
        # 사용자 정의 규칙 추가
        custom_rule = {
            'pattern': rule_dict['pattern'],
            'replacement': rule_dict['replacement'],
            'explanation': rule_dict.get('explanation', '사용자 정의 규칙'),
            'enabled': rule_dict.get('enabled', True),
            'added_at': datetime.now().isoformat()
        }
        
        profile['user_settings']['custom_rules'].append(custom_rule)
        profile['version_info']['last_updated'] = datetime.now().isoformat()
        
        return self._save_profile(book_id, profile)
    
    def disable_rule(self, book_id: str, rule_pattern: str) -> bool:
        """특정 교정 규칙 비활성화"""
        
        profile = self.load_book_profile(book_id)
        if not profile:
            return False
            
        if rule_pattern not in profile['user_settings']['disabled_rules']:
            profile['user_settings']['disabled_rules'].append(rule_pattern)
            profile['version_info']['last_updated'] = datetime.now().isoformat()
            return self._save_profile(book_id, profile)
            
        return True
    
    def update_usage_stats(self, book_id: str, applied: int, success: int, 
                         user_overrides: int = 0, performance_score: float = 0.0) -> bool:
        """사용 통계 업데이트"""
        
        profile = self.load_book_profile(book_id)
        if not profile:
            return False
            
        stats = profile['usage_stats']
        stats['applied_count'] += applied
        stats['success_count'] += success
        stats['user_overrides'] += user_overrides
        
        # 성능 점수 업데이트 (이동 평균)
        if stats['applied_count'] > 0:
            current_score = stats['success_count'] / stats['applied_count']
            if stats['performance_score'] == 0.0:
                stats['performance_score'] = current_score
            else:
                # 80% 기존, 20% 새로운 점수로 가중평균
                stats['performance_score'] = stats['performance_score'] * 0.8 + current_score * 0.2
                
        stats['performance_score'] = round(stats['performance_score'], 3)
        
        return self._save_profile(book_id, profile)
    
    def get_active_rules(self, book_id: str, priority_filter: Optional[List[str]] = None) -> List[Dict]:
        """활성화된 교정 규칙들 반환"""
        
        profile = self.load_book_profile(book_id) 
        if not profile:
            return []
            
        active_rules = []
        disabled_patterns = set(profile['user_settings']['disabled_rules'])
        
        # 기본 교정 규칙들
        for rule in profile['correction_rules']:
            if rule['pattern'] not in disabled_patterns:
                # 우선순위 필터 적용
                if priority_filter is None or rule.get('priority_level') in priority_filter:
                    active_rules.append(rule)
                    
        # 사용자 정의 규칙들
        for custom_rule in profile['user_settings']['custom_rules']:
            if custom_rule.get('enabled', True):
                active_rules.append({
                    'pattern': custom_rule['pattern'],
                    'replacement': custom_rule['replacement'],
                    'correction_type': 'custom',
                    'scope': 'book_only',
                    'confidence': 1.0,
                    'explanation': custom_rule['explanation'],
                    'risk_level': 'user_defined',
                    'priority_level': 'custom'
                })
                
        return active_rules
    
    def list_all_profiles(self) -> List[Dict]:
        """모든 프로파일 목록 반환"""
        
        profiles = []
        
        for yaml_file in self.profiles_dir.glob("book_*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    profile = yaml.safe_load(f)
                    
                summary = {
                    'book_id': profile['book_info']['book_id'],
                    'title': profile['book_info']['title'],
                    'domain': profile['book_info']['domain'],
                    'total_rules': profile['analysis_summary']['total_rules'],
                    'confidence_score': profile['analysis_summary']['confidence_score'],
                    'performance_score': profile['usage_stats']['performance_score'],
                    'approved': profile['user_settings']['profile_approved'],
                    'last_updated': profile['version_info']['last_updated']
                }
                
                profiles.append(summary)
                
            except Exception as e:
                print(f"프로파일 읽기 실패 {yaml_file}: {e}")
                continue
                
        return sorted(profiles, key=lambda x: x['last_updated'], reverse=True)
    
    def export_profile_json(self, book_id: str, output_path: Optional[str] = None) -> str:
        """프로파일을 JSON으로 내보내기"""
        
        profile = self.load_book_profile(book_id)
        if not profile:
            raise ValueError(f"프로파일을 찾을 수 없음: {book_id}")
            
        if output_path is None:
            output_path = self.profiles_dir / f"book_{book_id}.json"
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
            
        return str(output_path)
    
    # === Helper Methods ===
    
    def _generate_book_title(self, fingerprint: BookFingerprint, standard: BookCorrectionStandard) -> str:
        """책 제목 자동 생성"""
        domain_names = {
            'textbook': '교육서',
            'novel': '소설', 
            'academic': '학술서',
            'magazine': '잡지',
            'manual': '매뉴얼',
            'general': '일반서'
        }
        
        domain_name = domain_names.get(fingerprint.content.domain.value, '도서')
        return f"{domain_name}_{fingerprint.book_id[:8]}"
    
    def _format_correction_rules(self, standard: BookCorrectionStandard) -> List[Dict]:
        """교정 규칙을 YAML 친화적 형태로 변환"""
        
        formatted_rules = []
        
        for i, rule in enumerate(standard.correction_rules):
            # 우선순위 레벨 결정
            priority_level = 'medium'  # 기본값
            for level, indices in standard.priority_levels.items():
                if i in indices:
                    priority_level = level
                    break
                    
            formatted_rule = {
                'id': i + 1,
                'pattern': rule.pattern,
                'replacement': rule.replacement,
                'correction_type': rule.correction_type.value,
                'scope': rule.scope.value,
                'confidence': round(rule.confidence, 3),
                'explanation': rule.explanation,
                'examples': rule.examples,
                'risk_level': rule.risk_level,
                'priority_level': priority_level,
                'requires_approval': rule.requires_approval,
                'enabled': True
            }
            
            formatted_rules.append(formatted_rule)
            
        return formatted_rules
    
    def _get_rules_by_priority(self, standard: BookCorrectionStandard, priority: str) -> List[int]:
        """우선순위별 규칙 ID 목록 반환"""
        indices = standard.priority_levels.get(priority, [])
        return [idx + 1 for idx in indices]  # 1-based indexing
    
    def _save_profile(self, book_id: str, profile_data: Dict) -> bool:
        """프로파일 저장"""
        try:
            profile_path = self.profiles_dir / f"book_{book_id}.yaml"
            
            with open(profile_path, 'w', encoding='utf-8') as f:
                yaml.dump(profile_data, f, **self.yaml_config)
                
            # 캐시 업데이트
            self._profile_cache[book_id] = profile_data
            
            return True
            
        except Exception as e:
            print(f"프로파일 저장 실패 {book_id}: {e}")
            return False


# === 사용 예시와 테스트 코드 ===

if __name__ == "__main__":
    # 이전 단계에서 생성된 데이터 시뮬레이션
    from .book_fingerprint import BookFingerprintAnalyzer
    from gpt_standard_generator import GPTCorrectionStandardGenerator
    
    # 1. 테스트 데이터 준비
    sample_texts = [
        "이 책은 Python 프로그래밍의 기초를 다룹니다. def 함수():문법을 배웁니다.",
        "객체지향 프로그래밍은 현대 소프트웨어 개발의 핵심입니다.",
        "함수 정의할 때 def 키워드를 사용하며, 매개변수를 받을 수 있습니다."
    ]
    
    sample_ocr_results = [
        {'text': sample_texts[0], 'confidence': 0.88},
        {'text': sample_texts[1], 'confidence': 0.95},
        {'text': sample_texts[2], 'confidence': 0.91}
    ]
    
    # 2. Book Fingerprint 및 교정 기준 생성 
    fingerprint_analyzer = BookFingerprintAnalyzer()
    fingerprint = fingerprint_analyzer.generate_fingerprint(sample_texts, sample_ocr_results)
    
    gpt_generator = GPTCorrectionStandardGenerator()
    standard = gpt_generator.generate_standard(fingerprint, sample_texts)
    
    # 3. Book Profile 관리 시스템 테스트
    profile_manager = BookProfileManager()
    
    print("=" * 70)
    print("📋 Book Profile Management System Test")
    print("=" * 70)
    
    # 프로파일 생성
    profile_path = profile_manager.create_book_profile(
        fingerprint, 
        standard, 
        user_title="Python 프로그래밍 기초서"
    )
    print(f"✅ 프로파일 생성: {profile_path}")
    
    # 프로파일 로드 테스트
    loaded_profile = profile_manager.load_book_profile(fingerprint.book_id)
    print(f"📖 로드된 프로파일: {loaded_profile['book_info']['title']}")
    print(f"   총 {loaded_profile['analysis_summary']['total_rules']}개 규칙")
    print(f"   신뢰도: {loaded_profile['analysis_summary']['confidence_score']}")
    
    # 사용자 설정 업데이트
    settings_updated = profile_manager.update_profile_settings(
        fingerprint.book_id,
        {'profile_approved': True, 'auto_apply_safe_rules': True}
    )
    print(f"⚙️  사용자 설정 업데이트: {'성공' if settings_updated else '실패'}")
    
    # 사용자 정의 규칙 추가
    custom_rule_added = profile_manager.add_custom_rule(
        fingerprint.book_id,
        {
            'pattern': 'print(',
            'replacement': 'print(',
            'explanation': 'print 함수 호출 정규화'
        }
    )
    print(f"🔧 사용자 정의 규칙 추가: {'성공' if custom_rule_added else '실패'}")
    
    # 활성화된 규칙들 확인
    active_rules = profile_manager.get_active_rules(fingerprint.book_id)
    print(f"🎯 활성화된 규칙: {len(active_rules)}개")
    
    # 사용 통계 업데이트
    stats_updated = profile_manager.update_usage_stats(
        fingerprint.book_id,
        applied=10,
        success=9,
        user_overrides=1,
        performance_score=0.9
    )
    print(f"📊 사용 통계 업데이트: {'성공' if stats_updated else '실패'}")
    
    # 모든 프로파일 목록
    all_profiles = profile_manager.list_all_profiles()
    print(f"📚 전체 프로파일: {len(all_profiles)}개")
    
    for profile_summary in all_profiles:
        print(f"   - {profile_summary['title']} (성능: {profile_summary['performance_score']:.2f})")
    
    # JSON 내보내기
    json_path = profile_manager.export_profile_json(fingerprint.book_id)
    print(f"📤 JSON 내보내기: {json_path}")
    
    print("=" * 70)
    print("✅ Book Profile Management System 테스트 완료!")
    print("🎯 핵심 기능: YAML 저장, 사용자 설정, 통계 관리, 규칙 관리")
    print("🔄 Pattern Scope Policy 연동 준비 완료!")
    print("=" * 70)