"""
🤖 GPT Book Correction Standard Generator - Phase 2 Book Sense Engine

Purpose: Book Fingerprint를 활용해 GPT 1회 호출로 책별 맞춤형 교정 기준 생성
Innovation: 사후학습(reactive) → 사전기준생성(proactive) 패러다임의 핵심

Core Philosophy:
- Cost Zero: GPT 1번만 호출하여 비용 최소화
- Local Evolution: 생성된 기준을 로컬에서 점진적 개선
- User Control: 사용자가 교정 기준을 검토하고 수정 가능
- Safety First: 위험할 수 있는 교정은 사용자 승인 필요

Author: SnapTXT Team
Date: 2026-03-02
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import json
import hashlib
from enum import Enum
import logging
import re

from .book_fingerprint import BookFingerprint, BookDomain, LanguageStyle

logger = logging.getLogger(__name__)


class CorrectionType(Enum):
    """교정 유형 분류"""
    FONT_SPECIFIC = "font_specific"        # 폰트 특화 교정 (rn→m, cl→d)
    LANGUAGE_SPECIFIC = "language_specific" # 언어 특화 교정 (되엇→되었)
    DOMAIN_SPECIFIC = "domain_specific"    # 도메인 특화 교정 (학술용어 등)
    FORMATTING = "formatting"             # 서식 교정 (공백, 문단 등)
    CONTEXTUAL = "contextual"             # 문맥 기반 교정


class CorrectionScope(Enum):
    """교정 적용 범위"""
    BOOK_ONLY = "book_only"              # 해당 책에만 적용
    BOOK_SERIES = "book_series"          # 동일 시리즈/출판사
    DOMAIN_WIDE = "domain_wide"          # 동일 도메인 전반
    UNIVERSAL = "universal"              # 모든 책에 적용 가능


@dataclass 
class CorrectionRule:
    """개별 교정 규칙"""
    pattern: str                         # 교정 패턴 (정규식 또는 문자열)
    replacement: str                     # 교체할 내용
    correction_type: CorrectionType      # 교정 유형
    scope: CorrectionScope              # 적용 범위
    confidence: float                    # 확신도 (0.0~1.0)
    explanation: str                     # 교정 이유 설명
    examples: List[str]                  # 적용 예시들
    risk_level: str                      # 위험도 (low/medium/high)
    requires_approval: bool              # 사용자 승인 필요 여부
    
    def to_dict(self) -> Dict:
        """딕셔너리 직렬화"""
        return {
            'pattern': self.pattern,
            'replacement': self.replacement,
            'correction_type': self.correction_type.value,
            'scope': self.scope.value,
            'confidence': self.confidence,
            'explanation': self.explanation,
            'examples': self.examples,
            'risk_level': self.risk_level,
            'requires_approval': self.requires_approval
        }


@dataclass
class BookCorrectionStandard:
    """책별 종합적인 교정 기준"""
    book_id: str                         # Book Fingerprint의 book_id와 매칭
    book_title: str                      # 추정 책 제목
    generated_at: str                    # 생성 시점
    gpt_prompt_used: str                 # 사용된 GPT 프롬프트
    gpt_response_raw: str                # GPT 원본 응답
    correction_rules: List[CorrectionRule] # 교정 규칙들
    priority_levels: Dict[str, List[int]]  # 우선순위별 규칙 인덱스
    metadata: Dict[str, Any]             # 추가 메타데이터
    confidence_score: float              # 전체 신뢰도
    user_approved: bool                  # 사용자 승인 여부
    
    def to_dict(self) -> Dict:
        """딕셔너리 직렬화"""
        return {
            'book_id': self.book_id,
            'book_title': self.book_title,
            'generated_at': self.generated_at,
            'gpt_prompt_used': self.gpt_prompt_used,
            'gpt_response_raw': self.gpt_response_raw,
            'correction_rules': [rule.to_dict() for rule in self.correction_rules],
            'priority_levels': self.priority_levels,
            'metadata': self.metadata,
            'confidence_score': self.confidence_score,
            'user_approved': self.user_approved
        }


class GPTCorrectionStandardGenerator:
    """GPT를 활용한 책별 교정 기준 생성기"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        """초기화"""
        self.api_key = api_key  # 실제 구현에서는 환경변수에서 로드
        self.model = model
        self.prompt_templates = self._initialize_prompt_templates()
        
    def generate_standard(self, fingerprint: BookFingerprint, sample_texts: List[str]) -> BookCorrectionStandard:
        """Book Fingerprint를 기반으로 교정 기준 생성"""
        
        # 1. Fingerprint 기반 맞춤형 프롬프트 생성
        prompt = self._create_targeted_prompt(fingerprint, sample_texts)
        
        # 2. GPT 1회 호출 (핵심!)
        gpt_response = self._call_gpt_once(prompt)
        
        # 3. 응답 파싱하여 교정 규칙 추출
        correction_rules = self._parse_gpt_response(gpt_response, fingerprint)
        
        # 4. 우선순위 및 안전성 분석
        priority_levels = self._analyze_priorities(correction_rules, fingerprint)
        
        # 5. 종합적인 교정 기준 생성
        standard = self._create_correction_standard(
            fingerprint, prompt, gpt_response, correction_rules, priority_levels
        )
        
        return standard
    
    def _initialize_prompt_templates(self) -> Dict[str, str]:
        """도메인별 프롬프트 템플릿 초기화"""
        return {
            'textbook': """
당신은 교육용 도서의 OCR 교정 전문가입니다. 
다음 책의 특성을 분석하여 맞춤형 교정 규칙을 생성해주세요.

책 특성:
- 도메인: 교육/학습서
- 내용 복잡도: {complexity}
- 기술 용어 수: {tech_terms}
- 평균 신뢰도: {confidence}

일반적인 교육서 OCR 문제:
1. 하이픈과 언더스코어 혼동
2. 코드 블록 내 문자 오인식  
3. 수식 기호 왜곡
4. 전문 용어 분절

샘플 텍스트들을 분석하여 이 책에서만 발생할 수 있는 특화된 교정 패턴을 찾아주세요.
""",
            'novel': """
당신은 소설 및 문학 작품의 OCR 교정 전문가입니다.
다음 소설의 특성을 분석하여 맞춤형 교정 규칙을 생성해주세요.

책 특성:
- 도메인: 문학/소설
- 언어 스타일: {language_style}
- 어휘 다양성: {vocab_diversity}
- 평균 신뢰도: {confidence}

일반적인 소설 OCR 문제:
1. 대화문 인용부호 오류
2. 감정 표현 문장부호 누락
3. 고유명사(인명, 지명) 오인식
4. 방언 및 구어체 표현 왜곡

이 소설에서만 나타날 수 있는 특징적인 교정 패턴을 찾아주세요.
""",
            'academic': """
당신은 학술 논문 및 전문서적의 OCR 교정 전문가입니다.
다음 학술서의 특성을 분석하여 맞춤형 교정 규칙을 생성해주세요.

책 특성:
- 도메인: 학술/연구
- 내용 복잡도: {complexity}
- 기술 용어 밀도: {tech_terms}
- 인용 패턴: 높음

일반적인 학술서 OCR 문제:
1. 참고문헌 링크 파손
2. 수학 공식 기호 오류
3. 라틴어/그리스어 용어 오인식
4. 표와 그래프 캡션 왜곡

이 학술서에서만 발생할 수 있는 전문적인 교정 패턴을 분석해주세요.
""",
            'general': """
당신은 일반 도서의 OCR 교정 전문가입니다.
다음 도서의 특성을 분석하여 맞춤형 교정 규칙을 생성해주세요.

책 특성:
- 도메인: 일반
- 언어 스타일: {language_style} 
- 타이포그래피: {typography}
- 평균 신뢰도: {confidence}

여러 도메인에서 공통적으로 나타날 수 있는 교정 패턴을 포함하되,
이 책의 고유한 특성을 반영한 맞춤형 규칙을 우선 제시해주세요.
"""
        }
    
    def _create_targeted_prompt(self, fingerprint: BookFingerprint, sample_texts: List[str]) -> str:
        """Fingerprint 기반 맞춤형 프롬프트 생성"""
        
        # 도메인별 기본 템플릿 선택
        if fingerprint.content.domain == BookDomain.TEXTBOOK:
            base_template = self.prompt_templates['textbook']
        elif fingerprint.content.domain == BookDomain.NOVEL:
            base_template = self.prompt_templates['novel']
        elif fingerprint.content.domain == BookDomain.ACADEMIC:
            base_template = self.prompt_templates['academic']
        else:
            base_template = self.prompt_templates['general']
            
        # Fingerprint 데이터 삽입
        formatted_template = base_template.format(
            complexity=fingerprint.content.complexity_score,
            tech_terms=fingerprint.content.technical_terms_count,
            confidence=fingerprint.quality.avg_confidence,
            language_style=fingerprint.content.language_style.value,
            vocab_diversity=fingerprint.content.vocabulary_diversity,
            typography=fingerprint.typography.formatting_style
        )
        
        # 샘플 텍스트 첨부
        samples_text = "\n".join([f"샘플 {i+1}: {text}" for i, text in enumerate(sample_texts[:5])])
        
        # 일관된 오류 패턴 정보 추가
        error_patterns = ""
        if fingerprint.quality.consistent_errors:
            error_patterns = f"\n감지된 일관된 오류: {fingerprint.quality.consistent_errors}"
        
        # 최종 프롬프트 조합
        final_prompt = f"""
{formatted_template}

=== 분석할 샘플 텍스트 ===
{samples_text}

{error_patterns}

=== 요청사항 ===
위 정보를 종합하여 다음 형식으로 교정 규칙들을 제안해주세요:

1. 패턴: [오류 패턴]
   교체: [올바른 형태]
   유형: [font_specific|language_specific|domain_specific|formatting|contextual]
   범위: [book_only|book_series|domain_wide|universal]
   확신도: [0.0-1.0]
   설명: [왜 이런 교정이 필요한지]
   예시: [적용 예시 3가지]
   위험도: [low|medium|high]

최대 10개의 가장 효과적인 교정 규칙만 제안해주세요.
일반적인 OCR 오류보다는 이 책의 특성에 맞는 맞춤형 교정에 집중해주세요.
"""
        
        return final_prompt.strip()
    
    def _call_gpt_once(self, prompt: str) -> str:
        """GPT 1회 호출 (실제 구현에서는 OpenAI API 사용)"""
        
        # 현재는 시뮬레이션 - 실제로는 OpenAI API 호출
        simulated_response = """
1. 패턴: Python
   교체: Python
   유형: domain_specific
   범위: book_only  
   확신도: 0.95
   설명: 'Python' 단어는 프로그래밍 언어명으로 대소문자가 중요함
   예시: python 프로그래밍 → Python 프로그래밍
   위험도: low

2. 패턴: def\\s+
   교체: def 
   유형: font_specific
   범위: book_only
   확신도: 0.88
   설명: 코드 블록에서 'def' 키워드 뒤 공백이 불규칙하게 인식됨
   예시: def함수 → def 함수, def  func → def func
   위험도: medium

3. 패턴: 함수는
   교체: 함수는
   유형: language_specific  
   범위: domain_wide
   확신도: 0.92
   설명: '함수는' 표현에서 조사 '는'이 누락되는 OCR 오류 빈발
   예시: 함수 코드의 → 함수는 코드의
   위험도: low

4. 패턴: \\n\\n\\n+
   교체: \\n\\n
   유형: formatting
   범위: book_only
   확신도: 0.85
   설명: 과도한 줄바꿈을 표준 문단 구분으로 정리
   예시: 줄1[3개개행]줄2 → 줄1[2개개행]줄2  
   위험도: low

5. 패턴: 객체지향
   교체: 객체지향
   유형: domain_specific
   범위: domain_wide
   확신도: 0.90
   설명: 프로그래밍 전문용어로 공백 없이 사용되어야 함
   예시: 객체 지향 → 객체지향
   위험도: low
"""
        
        logger.info(f"GPT 호출 시뮬레이션 완료 - 프롬프트 길이: {len(prompt)}")
        return simulated_response.strip()
    
    def _parse_gpt_response(self, response: str, fingerprint: BookFingerprint) -> List[CorrectionRule]:
        """GPT 응답을 파싱하여 교정 규칙 추출"""
        rules = []
        
        # 정규식으로 각 규칙 블록 추출
        pattern = r'(\d+)\.\s+패턴:\s*(.+?)\n\s+교체:\s*(.+?)\n\s+유형:\s*(.+?)\n\s+범위:\s*(.+?)\n\s+확신도:\s*(.+?)\n\s+설명:\s*(.+?)\n\s+예시:\s*(.+?)\n\s+위험도:\s*(.+?)(?=\n\n|\n\d+\.|\Z)'
        
        matches = re.findall(pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                rule_num, pattern_str, replacement, correction_type, scope, confidence, explanation, examples, risk = match
                
                # Enum 변환
                try:
                    corr_type = CorrectionType(correction_type.strip())
                except:
                    corr_type = CorrectionType.CONTEXTUAL
                    
                try:
                    corr_scope = CorrectionScope(scope.strip())
                except:
                    corr_scope = CorrectionScope.BOOK_ONLY
                
                # 확신도 파싱
                try:
                    conf_value = float(confidence.strip())
                except:
                    conf_value = 0.5
                    
                # 예시 분리
                examples_list = [ex.strip() for ex in examples.split('→') if ex.strip()]
                if len(examples_list) < 2:
                    examples_list = [examples.strip()]
                
                # 위험도에 따른 승인 필요 여부
                requires_approval = risk.strip().lower() in ['high', 'medium']
                
                rule = CorrectionRule(
                    pattern=pattern_str.strip(),
                    replacement=replacement.strip(),
                    correction_type=corr_type,
                    scope=corr_scope,
                    confidence=conf_value,
                    explanation=explanation.strip(),
                    examples=examples_list,
                    risk_level=risk.strip().lower(),
                    requires_approval=requires_approval
                )
                
                rules.append(rule)
                
            except Exception as e:
                logger.warning(f"교정 규칙 파싱 실패: {e}")
                continue
                
        logger.info(f"총 {len(rules)}개 교정 규칙 추출 완료")
        return rules
    
    def _analyze_priorities(self, rules: List[CorrectionRule], fingerprint: BookFingerprint) -> Dict[str, List[int]]:
        """교정 규칙의 우선순위 분석"""
        
        priorities = {
            'critical': [],     # 즉시 적용 필요
            'high': [],        # 높은 우선순위  
            'medium': [],      # 보통 우선순위
            'low': []          # 낮은 우선순위
        }
        
        for i, rule in enumerate(rules):
            # 우선순위 결정 로직
            score = 0
            
            # 확신도 가중치
            score += rule.confidence * 40
            
            # 유형별 가중치
            if rule.correction_type == CorrectionType.FONT_SPECIFIC:
                score += 25
            elif rule.correction_type == CorrectionType.DOMAIN_SPECIFIC:
                score += 20
            elif rule.correction_type == CorrectionType.LANGUAGE_SPECIFIC:
                score += 15
                
            # 위험도 페널티
            if rule.risk_level == 'high':
                score -= 20
            elif rule.risk_level == 'medium':
                score -= 10
                
            # 범위별 가중치 
            if rule.scope == CorrectionScope.BOOK_ONLY:
                score += 15
            elif rule.scope == CorrectionScope.DOMAIN_WIDE:
                score += 10
                
            # 우선순위 분류
            if score >= 80:
                priorities['critical'].append(i)
            elif score >= 65:
                priorities['high'].append(i)
            elif score >= 45:
                priorities['medium'].append(i)
            else:
                priorities['low'].append(i)
                
        return priorities
    
    def _create_correction_standard(self, fingerprint: BookFingerprint, prompt: str, 
                                  response: str, rules: List[CorrectionRule], 
                                  priorities: Dict[str, List[int]]) -> BookCorrectionStandard:
        """종합적인 교정 기준 생성"""
        
        # 전체 신뢰도 계산
        if rules:
            confidence_score = sum(rule.confidence for rule in rules) / len(rules)
        else:
            confidence_score = 0.0
            
        # 추정 제목 생성 (샘플 텍스트 첫 문장에서)
        book_title = f"Book_{fingerprint.book_id[:8]}"  # 기본값
        
        # 메타데이터 수집
        metadata = {
            'domain': fingerprint.content.domain.value,
            'language_style': fingerprint.content.language_style.value,
            'avg_ocr_confidence': fingerprint.quality.avg_confidence,
            'total_rules': len(rules),
            'high_priority_rules': len(priorities.get('critical', []) + priorities.get('high', [])),
            'approval_required_rules': len([r for r in rules if r.requires_approval])
        }
        
        from datetime import datetime
        
        return BookCorrectionStandard(
            book_id=fingerprint.book_id,
            book_title=book_title,
            generated_at=datetime.now().isoformat(),
            gpt_prompt_used=prompt,
            gpt_response_raw=response,
            correction_rules=rules,
            priority_levels=priorities,
            metadata=metadata,
            confidence_score=confidence_score,
            user_approved=False  # 초기에는 미승인
        )


# === 사용 예시와 테스트 코드 ===

if __name__ == "__main__":
    # BookFingerprint 시뮬레이션 (실제로는 이전 단계에서 생성됨)
    from .book_fingerprint import BookFingerprintAnalyzer
    
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
    
    # 1. Book Fingerprint 생성
    fingerprint_analyzer = BookFingerprintAnalyzer()
    fingerprint = fingerprint_analyzer.generate_fingerprint(sample_texts, sample_ocr_results)
    
    # 2. GPT 교정 기준 생성
    gpt_generator = GPTCorrectionStandardGenerator()
    standard = gpt_generator.generate_standard(fingerprint, sample_texts)
    
    print("=" * 60)
    print("🤖 GPT Book Correction Standard Generation Result")
    print("=" * 60)
    print(f"Book ID: {standard.book_id}")
    print(f"총 교정 규칙: {len(standard.correction_rules)}개")
    print(f"전체 신뢰도: {standard.confidence_score:.2f}")
    print(f"승인 필요 규칙: {standard.metadata['approval_required_rules']}개")
    
    print("\n📋 우선순위별 규칙 분포:")
    for priority, indices in standard.priority_levels.items():
        print(f"  {priority.upper()}: {len(indices)}개")
    
    print("\n🔧 주요 교정 규칙들:")
    for i, rule in enumerate(standard.correction_rules[:3]):
        print(f"  {i+1}. {rule.pattern} → {rule.replacement}")
        print(f"     유형: {rule.correction_type.value}, 확신도: {rule.confidence:.2f}")
        print(f"     설명: {rule.explanation}")
        print()
    
    print("=" * 60)
    print("✅ GPT 1회 호출로 책별 맞춤형 교정 기준 생성 완료!")
    print("💰 비용 최적화: 동일 책 재인식 시 기존 기준 재활용")
    print("🛡️ 안전성: 위험도 높은 교정은 사용자 승인 필요")
    print("=" * 60)