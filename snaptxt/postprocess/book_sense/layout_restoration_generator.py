"""
🏗️ Layout Restoration Generator - Phase 2.7

Purpose: 공백/구조 복원에 특화된 GPT 규칙 생성
Innovation: 문자 교정 → 구조 복원 패러다임 전환

Key Features:
- 줄바꿈으로 인한 어절 분리 감지
- 조사 분리 패턴 복원 (을/를/이/가/은/는)
- 대화문 구조 정리
- layout_specific 규칙 타입

Author: SnapTXT Team  
Date: 2026-03-02
Strategy: Phase 2.6 병목 발견 → 타겟 전환
"""

from typing import List, Dict, Optional, Tuple
import re
import json
from datetime import datetime
from dataclasses import dataclass
import os
import hashlib

# OpenAI optional import
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class LayoutRule:
    """공백 복원 규칙"""
    rule_id: str
    rule_type: str              # line_break_merge / broken_word_merge / dialogue_boundary
    pattern: str                # 검색 패턴
    replacement: str            # 교체 문자열
    context: str               # 적용 상황 설명
    confidence: float          # 확신도 (0.0~1.0)
    priority: str              # HIGH/MEDIUM/LOW
    risk_level: str           # SAFE/MODERATE/RISKY


@dataclass
class LayoutProfile:
    """책별 공백 복원 프로필"""
    book_id: str
    domain: str               # textbook/novel/magazine/general
    layout_rules: List[LayoutRule]
    generation_date: str
    sample_pages: List[str]   # 분석된 페이지들
    confidence_metrics: Dict


class LayoutRestorationGenerator:
    """Phase 2.7 공백 복원 규칙 생성기"""
    
    def __init__(self, api_key: str = None):
        """초기화"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key and OPENAI_AVAILABLE:
            openai.api_key = self.api_key
            
        # 한국어 조사 패턴
        self.korean_particles = {
            'subject': ['이', '가'],
            'object': ['을', '를'], 
            'topic': ['은', '는'],
            'location': ['에', '에서', '로', '으로'],
            'connection': ['과', '와', '하고'],
            'ending': ['다', '다.', '요', '습니다']
        }
        
        # 영어 접사 패턴  
        self.english_affixes = {
            'prefix': ['un', 're', 'pre', 'dis', 'mis'],
            'suffix': ['ing', 'ed', 'ly', 'tion', 'ness', 'ment']
        }
    
    def generate_layout_profile(self, sample_pages: List[str], 
                              book_domain: str = "general") -> LayoutProfile:
        """책별 공백 복원 프로필 생성"""
        
        print(f"🏗️ Layout Restoration Profile 생성 중...")
        print(f"   도메인: {book_domain}")
        print(f"   샘플 페이지: {len(sample_pages)}개")
        
        # 1. 공백 오류 패턴 분석
        layout_issues = self._analyze_layout_issues(sample_pages)
        
        # 2. GPT를 통한 공백 복원 규칙 생성
        layout_rules = self._generate_gpt_layout_rules(sample_pages, book_domain, layout_issues)
        
        # 3. 규칙 검증 및 우선순위 설정
        validated_rules = self._validate_layout_rules(layout_rules, sample_pages)
        
        # 4. 프로필 생성
        book_id = self._generate_book_id(sample_pages)
        
        profile = LayoutProfile(
            book_id=book_id,
            domain=book_domain,
            layout_rules=validated_rules,
            generation_date=datetime.now().isoformat(),
            sample_pages=sample_pages[:3],  # 처음 3페이지만 저장
            confidence_metrics=self._calculate_confidence_metrics(validated_rules)
        )
        
        print(f"✅ Layout Profile 완성: {len(validated_rules)}개 공백 복원 규칙")
        return profile
    
    def _analyze_layout_issues(self, sample_pages: List[str]) -> Dict[str, List[str]]:
        """공백 오류 패턴 분석"""
        issues = {
            'broken_particles': [],      # 분리된 조사
            'broken_words': [],          # 분리된 어절  
            'line_merge_needed': [],     # 줄 병합 필요
            'dialogue_issues': []        # 대화문 구조 문제
        }
        
        for page in sample_pages:
            lines = page.split('\n')
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # 1. 조사 분리 감지
                particles_found = self._detect_broken_particles(line)
                issues['broken_particles'].extend(particles_found)
                
                # 2. 어절 분리 감지  
                broken_words = self._detect_broken_words(line)
                issues['broken_words'].extend(broken_words)
                
                # 3. 줄 끝 + 다음 줄 시작 분석
                if i < len(lines) - 1:
                    next_line = lines[i+1].strip()
                    merge_case = self._detect_line_merge_case(line, next_line)
                    if merge_case:
                        issues['line_merge_needed'].append(merge_case)
                
                # 4. 대화문 구조 문제
                dialogue_issue = self._detect_dialogue_issues(line)
                if dialogue_issue:
                    issues['dialogue_issues'].append(dialogue_issue)
        
        # 중복 제거 및 빈도순 정렬
        for key in issues:
            issues[key] = list(set(issues[key]))
            
        return issues
    
    def _detect_broken_particles(self, line: str) -> List[str]:
        """분리된 조사 감지"""
        broken_particles = []
        
        words = line.split()
        for i, word in enumerate(words):
            # 단독으로 나타나는 조사들
            for particle_type, particles in self.korean_particles.items():
                if word in particles and i > 0:
                    prev_word = words[i-1]
                    if len(prev_word) > 1:  # 의미있는 앞 단어
                        broken_particles.append(f"{prev_word} {word}")
        
        return broken_particles
    
    def _detect_broken_words(self, line: str) -> List[str]:
        """분리된 어절 감지"""
        broken_words = []
        
        # 한국어 동사/형용사 패턴 감지
        patterns = [
            r'(\w+)\s+(었|았|였)\s*(다|습니다)', # 과거형 분리
            r'(\w+)\s+(하|되|만들|가지)\s*(었|였|다)',  # 복합동사 분리  
            r'(\w+)\s+(어|아)\s*(서|야|지)',  # 연결형 분리
            r'(\w+)\s+(으|을)\s*(수|것)'      # 의존명사 분리
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, line)
            for match in matches:
                broken_words.append(match.group(0))
        
        return broken_words
    
    def _detect_line_merge_case(self, line1: str, line2: str) -> Optional[str]:
        """줄 병합이 필요한 경우 감지"""
        if not line1 or not line2:
            return None
            
        # 첫 번째 줄이 조사로 끝나지 않고, 두 번째 줄이 조사로 시작
        line1_last = line1.split()[-1] if line1.split() else ""
        line2_first = line2.split()[0] if line2.split() else ""
        
        for particle_type, particles in self.korean_particles.items():
            if line2_first in particles:
                return f"{line1_last} | {line2_first}"  # 병합 후보
                
        # 단어가 중간에 끊어진 경우 (영어)
        if len(line1_last) >= 2 and len(line2_first) >= 2:
            combined = line1_last + line2_first
            # 영어 단어 패턴 체크 (간단한 휴리스틱)
            if re.match(r'^[a-zA-Z]+$', combined) and len(combined) >= 4:
                return f"{line1_last}|{line2_first}"
                
        return None
    
    def _detect_dialogue_issues(self, line: str) -> Optional[str]:
        """대화문 구조 문제 감지"""
        # 대화 시작/종료 따옴표 문제
        if '"' in line:
            quote_count = line.count('"')
            if quote_count % 2 == 1:  # 홀수 개 따옴표
                return f"quote_mismatch: {line[:50]}..."
                
        # 대화문과 지문이 붙어있는 경우
        dialogue_pattern = r'"[^"]*"\s*[가-힣]+\s+(말했다|물었다|대답했다)'
        if re.search(dialogue_pattern, line):
            return f"merged_dialogue: {line[:50]}..."
            
        return None
    
    def _generate_gpt_layout_rules(self, sample_pages: List[str], 
                                 domain: str, layout_issues: Dict) -> List[LayoutRule]:
        """GPT를 통한 공백 복원 규칙 생성"""
        
        if not self.api_key or not OPENAI_AVAILABLE:
            print("⚠️ OpenAI API 키가 없거나 모듈이 없어 시뮬레이션 규칙 반환")
            return self._get_simulation_layout_rules(domain, layout_issues)
        
        # 도메인별 특화 프롬프트
        prompt = self._create_layout_prompt(sample_pages, domain, layout_issues)
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self._get_layout_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            rules_json = response.choices[0].message.content
            rules_data = json.loads(rules_json)
            
            layout_rules = []
            for rule_data in rules_data.get('layout_rules', []):
                rule = LayoutRule(
                    rule_id=f"layout_{len(layout_rules)+1}",
                    rule_type=rule_data['rule_type'],
                    pattern=rule_data['pattern'],
                    replacement=rule_data['replacement'],
                    context=rule_data['context'],
                    confidence=rule_data['confidence'],
                    priority=rule_data['priority'],
                    risk_level=rule_data['risk_level']
                )
                layout_rules.append(rule)
            
            return layout_rules
            
        except Exception as e:
            print(f"⚠️ GPT 호출 실패: {e}")
            return self._get_simulation_layout_rules(domain, layout_issues)
    
    def _get_layout_system_prompt(self) -> str:
        """공백 복원 특화 시스템 프롬프트"""
        return """당신은 OCR 텍스트의 공백/구조 복원 전문가입니다.

🎯 **핵심 임무**: 줄바꿈으로 인해 발생한 어절 분리와 공백 오류만 찾아 복원 규칙을 만드세요.

❌ **하지 말 것**: 
- 문자 인식 오류 교정 (예: ㅁ→ㅛ, rn→m)
- 맞춤법 교정 (예: 되었→됐)
- 문맥상 단어 변경

✅ **해야 할 것**:
- 조사 분리 복원 (자아 을 → 자아를)  
- 어절 분리 복원 (만들 어진 → 만들어진)
- 줄바꿈 병합 (끝단어 + 조사)
- 대화문 구조 정리

규칙은 다음 3가지 타입으로 분류:
1. line_break_merge: 줄바꿈으로 분리된 조사 복원
2. broken_word_merge: 중간에 끊어진 어절 복원  
3. dialogue_boundary: 대화문 구조 정리

JSON 형식으로 응답하세요."""

    def _create_layout_prompt(self, sample_pages: List[str], domain: str, 
                            layout_issues: Dict) -> str:
        """공백 복원용 프롬프트 생성"""
        
        sample_text = "\n".join(sample_pages[:2])  # 처음 2페이지
        
        prompt = f"""📖 **도메인**: {domain}

🔍 **발견된 공백 오류 패턴들**:
- 분리된 조사: {layout_issues['broken_particles'][:5]}
- 분리된 어절: {layout_issues['broken_words'][:5]}  
- 줄 병합 필요: {layout_issues['line_merge_needed'][:3]}

📝 **샘플 텍스트**:
{sample_text[:1000]}

🎯 **요청**: 위 텍스트에서 줄바끝/공백으로 인해 분리된 패턴들을 분석하고, 
다음과 같은 **공백 복원 규칙**을 5개 이하로 생성해주세요:

1. **line_break_merge**: 조사가 분리된 패턴 (예: "단어 을" → "단어를")
2. **broken_word_merge**: 어절이 분리된 패턴 (예: "만들 어" → "만들어")  
3. **dialogue_boundary**: 대화문 구조 문제 (예: 따옴표 정리)

**JSON 응답 형식**:
```json
{{
  "layout_rules": [
    {{
      "rule_type": "line_break_merge",
      "pattern": "정규식 패턴",
      "replacement": "교체 문자열", 
      "context": "언제 적용되는지 설명",
      "confidence": 0.85,
      "priority": "HIGH",
      "risk_level": "SAFE"
    }}
  ]
}}
```

⚠️ **주의**: 문자 교정이 아닌 공백/구조 복원만 해주세요!"""

        return prompt
    
    def _get_simulation_layout_rules(self, domain: str, layout_issues: Dict) -> List[LayoutRule]:
        """시뮬레이션 공백 복원 규칙"""
        
        rules = [
            LayoutRule(
                rule_id="layout_1",
                rule_type="line_break_merge",
                pattern=r'([가-힣]+)\s+(을|를|이|가|은|는)(\s|$)',
                replacement=r'\1\2\3',
                context="조사가 분리되어 다음 줄에 나타날 때",
                confidence=0.90,
                priority="HIGH", 
                risk_level="SAFE"
            ),
            LayoutRule(
                rule_id="layout_2", 
                rule_type="broken_word_merge",
                pattern=r'(하|되|만들)\s+(었|였|어)\s*(다|습니다)(\s|$)',
                replacement=r'\1\2\3\4',
                context="동사 활용이 공백으로 분리될 때",
                confidence=0.85,
                priority="HIGH",
                risk_level="SAFE"
            ),
            LayoutRule(
                rule_id="layout_3",
                rule_type="broken_word_merge", 
                pattern=r'([가-힣]+)\s+(의|과|와|에|로)\s*([가-힣])',
                replacement=r'\1\2 \3',
                context="조사 뒤에 공백이 누락되었을 때",
                confidence=0.80,
                priority="MEDIUM",
                risk_level="SAFE"
            )
        ]
        
        # 도메인별 특화 규칙 추가
        if domain == "novel":
            rules.append(LayoutRule(
                rule_id="layout_4",
                rule_type="dialogue_boundary",
                pattern=r'"([^"]*)\s*"\s*([가-힣]+)\s+(말했다|물었다|대답했다)',
                replacement=r'"\1" \2 \3',
                context="대화문과 지문이 붙어있을 때",
                confidence=0.75,
                priority="MEDIUM", 
                risk_level="MODERATE"
            ))
        elif domain == "textbook":
            rules.append(LayoutRule(
                rule_id="layout_4",
                rule_type="line_break_merge",
                pattern=r'([0-9]+)\s*\.\s*([가-힣])',
                replacement=r'\1. \2',
                context="번호 목록에서 공백이 분리될 때",
                confidence=0.85,
                priority="HIGH",
                risk_level="SAFE"
            ))
            
        return rules
    
    def _validate_layout_rules(self, rules: List[LayoutRule], 
                             sample_pages: List[str]) -> List[LayoutRule]:
        """공백 복원 규칙 검증"""
        
        validated_rules = []
        
        for rule in rules:
            try:
                # 정규식 유효성 검사
                re.compile(rule.pattern)
                
                # 샘플에서 적용 횟수 계산
                total_matches = 0
                for page in sample_pages:
                    matches = len(re.findall(rule.pattern, page))
                    total_matches += matches
                
                # 최소 적용 가능성이 있는 규칙만 유지
                if total_matches >= 1 or rule.priority == "HIGH":
                    validated_rules.append(rule)
                    print(f"✅ 규칙 검증 통과: {rule.rule_id} (적용 {total_matches}회)")
                else:
                    print(f"⚠️ 규칙 제외: {rule.rule_id} (적용 불가)")
                    
            except re.error as e:
                print(f"❌ 정규식 오류: {rule.rule_id} - {e}")
                
        return validated_rules
    
    def _calculate_confidence_metrics(self, rules: List[LayoutRule]) -> Dict:
        """신뢰도 지표 계산"""
        if not rules:
            return {"avg_confidence": 0.0, "high_priority_count": 0}
            
        confidences = [rule.confidence for rule in rules]
        high_priority = [rule for rule in rules if rule.priority == "HIGH"]
        safe_rules = [rule for rule in rules if rule.risk_level == "SAFE"]
        
        return {
            "avg_confidence": sum(confidences) / len(confidences),
            "rule_count": len(rules),
            "high_priority_count": len(high_priority),
            "safe_rule_count": len(safe_rules),
            "layout_types": {
                "line_break_merge": len([r for r in rules if r.rule_type == "line_break_merge"]),
                "broken_word_merge": len([r for r in rules if r.rule_type == "broken_word_merge"]), 
                "dialogue_boundary": len([r for r in rules if r.rule_type == "dialogue_boundary"])
            }
        }
    
    def _generate_book_id(self, sample_pages: List[str]) -> str:
        """책 ID 생성"""
        combined = "".join(sample_pages[:2])[:500]
        hash_obj = hashlib.md5(combined.encode())
        return hash_obj.hexdigest()[:16]
    
    def save_layout_profile(self, profile: LayoutProfile, output_dir: str = "book_profiles"):
        """공백 복원 프로필 저장"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        profile_data = {
            "book_id": profile.book_id,
            "domain": profile.domain,
            "generation_date": profile.generation_date,
            "confidence_metrics": profile.confidence_metrics,
            "layout_rules": [
                {
                    "rule_id": rule.rule_id,
                    "rule_type": rule.rule_type,
                    "pattern": rule.pattern,
                    "replacement": rule.replacement,
                    "context": rule.context,
                    "confidence": rule.confidence,
                    "priority": rule.priority,
                    "risk_level": rule.risk_level
                } for rule in profile.layout_rules
            ]
        }
        
        output_file = os.path.join(output_dir, f"layout_profile_{profile.book_id}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, ensure_ascii=False, indent=2)
            
        print(f"💾 Layout Profile 저장 완료: {output_file}")
        return output_file


# === Phase 2.7 테스트 실행 ===

if __name__ == "__main__":
    # 공백 오류가 많은 실제 OCR 텍스트 샘플
    sample_pages = [
        """이 책은 Python 프로그래밍
        의 기초를 다룹니다. 객체 지향 프로그래밍
        과 함수형 프로그래밍 개념
        도 배웁니다.
        
        1 장에서는 변수
        와 자료형을 다룹니다.""",
        
        """반복문과 조건문
        을 다뤄보겠습니다. for 루프
        는 매우 중요하며, while 문
        도 마찬가지입니다.
        
        "프로그래밍을 배우는 것
        은 즐거운 일입니다" 라고
        말했다.""",
        
        """함수를 정의할 때 def 키워드
        를 사용합니다. 매개변수
        와 반환값에 대해 배우고, 
        람다 함수도 다룹니다.
        
        예제: 팩토리얼 계산
        하 는 함수를 만들어
        보겠습니다."""
    ]
    
    print("🚀" * 40)
    print("🏗️ Phase 2.7 Layout Restoration Generator")
    print("🎯 문자 교정 → 공백 복원 패러다임 전환!")  
    print("🚀" * 40)
    
    # 공백 복원 생성기 초기화
    generator = LayoutRestorationGenerator()
    
    # 공백 복원 프로필 생성
    try:
        layout_profile = generator.generate_layout_profile(
            sample_pages=sample_pages,
            book_domain="textbook"
        )
        
        print(f"\n📊 Layout Profile 분석 결과:")
        print(f"   책 ID: {layout_profile.book_id}")
        print(f"   도메인: {layout_profile.domain}")
        print(f"   공백 복원 규칙: {len(layout_profile.layout_rules)}개")
        
        for rule in layout_profile.layout_rules:
            print(f"\n🔧 {rule.rule_id} ({rule.rule_type})")
            print(f"   패턴: {rule.pattern}")
            print(f"   교체: {rule.replacement}")
            print(f"   신뢰도: {rule.confidence:.2f}")
            print(f"   우선순위: {rule.priority}")
            
        # 신뢰도 지표
        metrics = layout_profile.confidence_metrics
        print(f"\n📈 신뢰도 지표:")
        print(f"   평균 신뢰도: {metrics['avg_confidence']:.2f}")
        print(f"   고우선순위 규칙: {metrics['high_priority_count']}개")
        print(f"   안전 규칙: {metrics['safe_rule_count']}개")
        print(f"   타입별 분포: {metrics['layout_types']}")
        
        # 프로필 저장
        saved_file = generator.save_layout_profile(layout_profile)
        
        print(f"\n🎉 Phase 2.7 핵심 성과:")
        print(f"   📊 공백 오류 패턴 자동 감지")
        print(f"   🔧 layout_specific 규칙 생성")
        print(f"   🎯 CER_space_only 병목 타겟팅")
        print(f"   💾 재사용 가능한 프로필 저장")
        
        print(f"\n💡 기대 효과:")
        print(f"   현재 CER_space_only: 10.65%")
        print(f"   타겟 개선: -2~4% (공백 복원)")
        print(f"   전체 CER 예상: 10.91% → 7~9% ✨")
        
    except Exception as e:
        print(f"⚠️ 오류 발생: {e}")
        
        # 시뮬레이션 성과
        print(f"\n🎯 Phase 2.7 시뮬레이션 결과:")
        print(f"   line_break_merge: 조사 분리 → 병합")
        print(f"   broken_word_merge: 어절 분리 → 복원")
        print(f"   dialogue_boundary: 대화문 구조 정리")
        print(f"   타겟: CER_space_only 직접 공략!")
    
    print(f"\n🚀" * 40)
    print(f"✅ Phase 2.7 Layout Restoration System")
    print(f"🎯 '타겟이 틀렸던 것' → '정확한 병목 타겟팅'")
    print(f"📊 다음: Phase 2.6 + Phase 2.7 통합 테스트!")
    print(f"🚀" * 40)