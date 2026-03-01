#!/usr/bin/env python3
"""SnapTXT 기획서 생성 도구 - 템플릿 기반으로 새 기획서 자동 생성"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path
from typing import Dict, Optional

# 프로젝트 루트 및 문서 경로
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = PROJECT_ROOT / "docs"

# 기획서 템플릿들
TEMPLATES = {
    "plans": {
        "description": "실행 계획/기능 기획",
        "template": """# {title}

> **작성일**: {date}  
> **상태**: 설계 중  
> **우선순위**: P2 (일반)  
> **예상 소요**: TBD  

## 📋 1. 프로젝트 개요

### 1.1 해결하려는 문제
- 

### 1.2 목표
- 

### 1.3 성공 기준
- [ ] 
- [ ] 
- [ ] 

## 🏗️ 2. 구현 계획

### 2.1 Phase 1 (1일차)
- [ ] 

### 2.2 Phase 2 (2일차)  
- [ ] 

### 2.3 Phase 3 (검증)
- [ ] 

## 🛠️ 3. 기술적 세부사항

### 3.1 구현할 기능
- 

### 3.2 사용할 기술/도구
- 

### 3.3 고려사항
- 

## 📊 4. 예상 결과

### 4.1 핵심 산출물
- 

### 4.2 성능 목표
- 

## ⚡ 5. 실행 로드맵

### 우선순위 1 (즉시)
1. 
2. 
3. 

### 우선순위 2 (이후)
4. 
5. 

### 검증 (최종)
6. 전체 시스템 테스트
7. 문서 업데이트

## 💡 6. 참고사항

### 6.1 관련 문서
- 

### 6.2 참고 자료
- 

---

## 🎉 결론

이 기획서가 완성되면 __기대 효과__ 를 달성할 수 있을 것입니다.
"""
    },
    
    "reference": {
        "description": "매뉴얼/가이드/참고자료",  
        "template": """# {title}

> **작성일**: {date}  
> **문서 유형**: 참고자료  
> **대상 독자**: 개발자/사용자  
> **최종 검토**: TBD  

## 📚 1. overview

### 1.1 이 문서의 목적
- 

### 1.2 대상 독자
- **개발자**: 
- **사용자**: 

### 1.3 사전 요구사항
- 

## 🚀 2. 시작하기

### 2.1 설치/설정
```bash
# 설치 명령어
```

### 2.2 기본 사용법
```python
# 예제 코드
```

## 🔧 3. 상세 가이드

### 3.1 핵심 기능
#### 기능 1
- **설명**: 
- **사용법**: 
- **예제**: 

#### 기능 2  
- **설명**: 
- **사용법**:
- **예제**: 

### 3.2 고급 기능
#### 고급 기능 1
- **설명**: 
- **사용 시나리오**: 
- **주의사항**: 

## 💡 4. 팁과 모범 사례

### 4.1 권장사항
- 

### 4.2 피해야 할 것들
- 

### 4.3 문제해결
#### 자주 발생하는 문제 1
- **증상**: 
- **원인**: 
- **해결법**: 

## 📖 5. 참고자료

### 5.1 관련 문서
- 

### 5.2 외부 자료
- 

---

## 🎯 요약

이 문서를 통해 __핵심 기능__ 을 효과적으로 활용할 수 있습니다.
"""
    },
    
    "analysis": {
        "description": "분석/연구/실험 보고서",
        "template": """# {title}

> **분석일**: {date}  
> **분석 대상**: TBD  
> **분석 방법**: TBD  
> **결론**: TBD  

## 📊 1. 분석 개요

### 1.1 분석 목적
- 

### 1.2 분석 범위
- **대상**: 
- **기간**: 
- **도구**: 

### 1.3 가설
- 

## 🔍 2. 분석 방법

### 2.1 데이터 수집
- **수집 방법**: 
- **데이터 종류**: 
- **수집 기간**: 

### 2.2 분석 도구
- 

### 2.3 분석 절차
1. 
2. 
3. 

## 📈 3. 분석 결과

### 3.1 주요 발견사항
#### 발견사항 1
- **내용**: 
- **근거**: 
- **중요도**: 

#### 발견사항 2
- **내용**: 
- **근거**: 
- **중요도**: 

### 3.2 데이터 요약
| 지표 | 값 | 비고 |
|------|----|----- |
|      |    |      |

### 3.3 시각화 결과
- 

## 🎯 4. 결론 및 권장사항

### 4.1 핵심 결론
- 

### 4.2 권장사항
#### 즉시 조치
1. 
2. 

#### 중장기 개선
1. 
2. 

### 4.3 추가 분석 필요사항
- 

## 📝 5. 상세 데이터

### 5.1 원본 데이터
- 

### 5.2 분석 코드/스크립트
```python
# 분석에 사용된 코드
```

---

## 💡 분석 후기

이 분석을 통해 __핵심 인사이트__ 를 얻을 수 있었습니다.
"""
    }
}

CATEGORY_PATHS = {
    "plans": "plans",
    "reference": "reference", 
    "status": "status",
    "analysis": "plans"  # 분석 문서는 plans 디렉터리에 저장
}


def create_planning_document(name: str, category: str, interactive: bool = False) -> Path:
    """새 기획서 생성"""
    
    # 카테고리 검증
    if category not in CATEGORY_PATHS:
        available = ", ".join(CATEGORY_PATHS.keys())
        raise ValueError(f"지원하지 않는 카테고리: {category}. 사용 가능: {available}")
    
    # 파일명 정규화 (snake_case)
    filename = name.lower().replace(" ", "_").replace("-", "_") + ".md"
    
    # 저장 경로
    category_dir = DOCS_ROOT / CATEGORY_PATHS[category]
    file_path = category_dir / filename
    
    # 디렉터리 생성
    category_dir.mkdir(parents=True, exist_ok=True)
    
    # 파일 중복 확인
    if file_path.exists():
        if interactive:
            response = input(f"파일이 이미 존재합니다: {file_path}\n덮어쓰시겠습니까? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("작업이 취소되었습니다.")
                return file_path
        else:
            # 백업 생성
            backup_path = file_path.with_suffix(f".backup_{int(dt.datetime.now().timestamp())}.md")
            file_path.rename(backup_path)
            print(f"기존 파일을 백업했습니다: {backup_path}")
    
    # 템플릿 선택
    template_type = category if category in TEMPLATES else "plans"
    template = TEMPLATES[template_type]["template"]
    
    # 템플릿 변수 치환
    current_date = dt.datetime.now().strftime("%Y-%m-%d")
    content = template.format(
        title=name,
        date=current_date
    )
    
    # 파일 생성
    file_path.write_text(content, encoding='utf-8')
    
    print(f"✅ 새 기획서가 생성되었습니다:")
    print(f"   📁 카테고리: {category} ({TEMPLATES[template_type]['description']})")
    print(f"   📄 파일: {file_path.relative_to(PROJECT_ROOT)}")
    print(f"   📊 크기: {file_path.stat().st_size} bytes")
    
    return file_path


def list_templates():
    """사용 가능한 템플릿 목록 표시"""
    print("🎨 사용 가능한 기획서 템플릿:")
    print()
    for template_name, info in TEMPLATES.items():
        print(f"  📝 {template_name:<12} : {info['description']}")
        print(f"     저장 위치     : docs/{CATEGORY_PATHS.get(template_name, template_name)}/")
        print()


def main():
    parser = argparse.ArgumentParser(description="SnapTXT 기획서 생성 도구")
    parser.add_argument("--name", type=str, help="기획서 이름")
    parser.add_argument("--type", choices=list(CATEGORY_PATHS.keys()), default="plans", 
                       help="기획서 카테고리")
    parser.add_argument("--interactive", action="store_true", 
                       help="대화형 모드로 실행")
    parser.add_argument("--list-templates", action="store_true",
                       help="사용 가능한 템플릿 목록 출력")
    
    args = parser.parse_args()
    
    if args.list_templates:
        list_templates()
        return
    
    # 대화형 모드
    if args.interactive or not args.name:
        print("📝 새 기획서 생성")
        print("=" * 40)
        
        if not args.name:
            name = input("기획서 이름 입력: ").strip()
            if not name:
                print("❌ 기획서 이름은 필수입니다.")
                sys.exit(1)
        else:
            name = args.name
            
        print(f"\n🎨 사용 가능한 카테고리:")
        for i, (cat_name, path) in enumerate(CATEGORY_PATHS.items(), 1):
            template_desc = TEMPLATES.get(cat_name, {}).get('description', '기본 템플릿')
            print(f"  {i}. {cat_name:<12} : {template_desc}")
        
        try:
            choice = int(input(f"\n카테고리 선택 (1-{len(CATEGORY_PATHS)}) [기본: 1]: ") or "1")
            category = list(CATEGORY_PATHS.keys())[choice - 1]
        except (ValueError, IndexError):
            category = args.type
            
        print(f"\n📄 생성할 기획서:")
        print(f"   이름: {name}")  
        print(f"   카테고리: {category}")
        print(f"   경로: docs/{CATEGORY_PATHS[category]}/{name.lower().replace(' ', '_')}.md")
        
        confirm = input("\n생성하시겠습니까? (Y/n): ").strip()
        if confirm.lower() in ['n', 'no']:
            print("작업이 취소되었습니다.")
            return
    else:
        name = args.name
        category = args.type
    
    try:
        created_path = create_planning_document(name, category, args.interactive)
        print(f"\n💡 다음 단계:")
        print(f"   1. 생성된 파일을 편집: code {created_path.relative_to(PROJECT_ROOT)}")
        print(f"   2. current_work.md에 링크 추가: python tools/update_current_work.py --add-planning-doc {name}")
        print(f"   3. 문서 시스템 검증: check_docs.bat optional")
        
    except Exception as e:
        print(f"❌ 오류: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()