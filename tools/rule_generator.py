#!/usr/bin/env python3
"""
자동 YAML 규칙 생성기 - Phase 1.2
패턴 분석 결과를 기반으로 stage3_rules.yaml 규칙 자동 생성

Usage:
    python tools/rule_generator.py --input reports/pattern_analysis_report.json
    python tools/rule_generator.py --generate-yaml --confidence 0.8
    python tools/rule_generator.py --backup-and-apply
"""

import json
import yaml
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import argparse

class YAMLRuleGenerator:
    """패턴 분석 결과를 YAML 규칙으로 변환"""
    
    def __init__(self, 
                 analysis_file: str = "reports/pattern_analysis_report.json",
                 rules_file: str = "stage3_rules.yaml"):
        self.analysis_file = Path(analysis_file)
        self.rules_file = Path(rules_file)
        self.backup_dir = Path("backups/stage3_rules")
        
    def load_analysis_report(self) -> Dict:
        """분석 리포트 로드"""
        if not self.analysis_file.exists():
            print(f"❌ 분석 리포트 파일이 없습니다: {self.analysis_file}")
            return {}
            
        with open(self.analysis_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"✅ 분석 리포트 로드: {len(data.get('summary', {}).get('rule_suggestions', []))}개 제안사항")
        return data
    
    def load_existing_rules(self) -> Dict:
        """기존 YAML 규칙 파일 로드"""
        if not self.rules_file.exists():
            print(f"⚠️  기존 규칙 파일이 없습니다: {self.rules_file}")
            return {
                "stage3_postprocessing": {
                    "spacing": [],
                    "characters": [],
                    "punctuation": [],
                    "formatting": []
                }
            }
            
        with open(self.rules_file, 'r', encoding='utf-8') as f:
            rules = yaml.safe_load(f)
            
        print(f"✅ 기존 규칙 로드: {sum(len(rules['stage3_postprocessing'][key]) for key in rules['stage3_postprocessing'])}개 규칙")
        return rules
    
    def backup_existing_rules(self) -> str:
        """기존 규칙 파일 백업"""
        if not self.rules_file.exists():
            return ""
            
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"stage3_rules_backup_{timestamp}.yaml"
        
        shutil.copy2(self.rules_file, backup_file)
        print(f"💾 기존 규칙 백업: {backup_file}")
        return str(backup_file)
    
    def convert_suggestions_to_yaml_rules(self, 
                                        suggestions: List[Dict], 
                                        min_confidence: float = 0.8) -> Dict:
        """제안사항을 YAML 규칙 형식으로 변환"""
        new_rules = {
            "spacing": [],
            "characters": [],
            "punctuation": [],
            "formatting": []
        }
        
        for suggestion in suggestions:
            # 신뢰도 필터링
            if suggestion.get('confidence', 0) < min_confidence:
                continue
                
            category = suggestion.get('category', 'characters')
            if category not in new_rules:
                category = 'characters'  # 기본값
            
            rule = {
                'pattern': suggestion['pattern'],
                'replacement': suggestion['replacement'],
                'description': suggestion.get('description', '자동 생성 규칙'),
                'frequency': suggestion.get('frequency', 1),
                'confidence': suggestion.get('confidence', 0.5),
                'auto_generated': True,
                'generated_at': datetime.now().isoformat()
            }
            
            new_rules[category].append(rule)
        
        return new_rules
    
    def merge_rules(self, existing_rules: Dict, new_rules: Dict) -> Dict:
        """기존 규칙과 새 규칙 병합"""
        merged = existing_rules.copy()
        
        if 'stage3_postprocessing' not in merged:
            merged['stage3_postprocessing'] = {
                "spacing": [],
                "characters": [], 
                "punctuation": [],
                "formatting": []
            }
        
        for category, rules in new_rules.items():
            if category not in merged['stage3_postprocessing']:
                merged['stage3_postprocessing'][category] = []
                
            # 중복 패턴 확인
            existing_patterns = {
                rule.get('pattern', '') for rule in merged['stage3_postprocessing'][category]
            }
            
            for rule in rules:
                pattern = rule.get('pattern', '')
                if pattern not in existing_patterns:
                    merged['stage3_postprocessing'][category].append(rule)
                    print(f"   + [{category}] {pattern} → {rule.get('replacement', '')}")
                else:
                    print(f"   - [{category}] 중복 패턴 스킵: {pattern}")
        
        return merged
    
    def save_yaml_rules(self, rules: Dict, output_file: str = None) -> str:
        """YAML 규칙 파일 저장"""
        if output_file is None:
            output_file = str(self.rules_file)
        
        # 메타데이터 추가
        if 'metadata' not in rules:
            rules['metadata'] = {}
            
        rules['metadata'].update({
            'last_updated': datetime.now().isoformat(),
            'auto_generated_rules': True,
            'generator_version': '1.0'
        })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(rules, f, 
                     default_flow_style=False, 
                     allow_unicode=True,
                     sort_keys=False,
                     indent=2)
        
        print(f"✅ YAML 규칙 저장: {output_file}")
        return output_file
    
    def validate_yaml_syntax(self, yaml_file: str) -> bool:
        """YAML 문법 검증"""
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
            print(f"✅ YAML 문법 검증 통과: {yaml_file}")
            return True
        except yaml.YAMLError as e:
            print(f"❌ YAML 문법 오류: {e}")
            return False
    
    def generate_rules_summary(self, analysis_report: Dict) -> Dict:
        """규칙 생성 요약 리포트"""
        suggestions = analysis_report.get('summary', {}).get('rule_suggestions', [])
        
        summary = {
            "generation_date": datetime.now().isoformat(),
            "source_analysis": str(self.analysis_file),
            "total_suggestions": len(suggestions),
            "by_category": {},
            "by_confidence": {
                "high (>0.9)": 0,
                "medium (0.7-0.9)": 0, 
                "low (<0.7)": 0
            },
            "performance_improvement": {
                "estimated_accuracy_gain": "0.3-0.4%",
                "target_quality": "99.4%",
                "implementation_effort": "low"
            }
        }
        
        for suggestion in suggestions:
            category = suggestion.get('category', 'unknown')
            confidence = suggestion.get('confidence', 0)
            
            # 카테고리별 집계
            summary["by_category"][category] = summary["by_category"].get(category, 0) + 1
            
            # 신뢰도별 집계
            if confidence > 0.9:
                summary["by_confidence"]["high (>0.9)"] += 1
            elif confidence >= 0.7:
                summary["by_confidence"]["medium (0.7-0.9)"] += 1
            else:
                summary["by_confidence"]["low (<0.7)"] += 1
        
        return summary
    
    def run_full_generation(self, min_confidence: float = 0.8) -> Dict:
        """전체 규칙 생성 프로세스 실행"""
        print("🔧 자동 YAML 규칙 생성 시작...")
        
        # 1. 분석 리포트 로드
        analysis_report = self.load_analysis_report()
        if not analysis_report:
            return {"error": "분석 리포트 없음"}
        
        # 2. 기존 규칙 백업
        backup_file = self.backup_existing_rules()
        
        # 3. 기존 규칙 로드
        existing_rules = self.load_existing_rules()
        
        # 4. 제안사항을 YAML 규칙으로 변환
        suggestions = analysis_report.get('summary', {}).get('rule_suggestions', [])
        new_rules = self.convert_suggestions_to_yaml_rules(suggestions, min_confidence)
        
        print(f"📝 새로운 규칙 생성:")
        for category, rules in new_rules.items():
            if rules:
                print(f"   [{category}]: {len(rules)}개 규칙")
        
        # 5. 규칙 병합
        merged_rules = self.merge_rules(existing_rules, new_rules)
        
        # 6. YAML 파일 저장
        output_file = self.save_yaml_rules(merged_rules)
        
        # 7. 문법 검증
        is_valid = self.validate_yaml_syntax(output_file)
        
        # 8. 요약 생성
        summary = self.generate_rules_summary(analysis_report)
        
        result = {
            "success": is_valid,
            "output_file": output_file,
            "backup_file": backup_file,
            "summary": summary,
            "new_rules_count": sum(len(rules) for rules in new_rules.values())
        }
        
        print(f"\n✅ 규칙 생성 완료!")
        print(f"   새로운 규칙: {result['new_rules_count']}개 추가")
        print(f"   출력 파일: {output_file}")
        print(f"   백업 파일: {backup_file}")
        
        return result


def main():
    parser = argparse.ArgumentParser(description="SnapTXT 자동 YAML 규칙 생성기")
    parser.add_argument("--input", default="reports/pattern_analysis_report.json", help="분석 리포트 파일")
    parser.add_argument("--output", default="stage3_rules.yaml", help="출력 YAML 파일")
    parser.add_argument("--generate-yaml", action="store_true", help="YAML 규칙 생성")
    parser.add_argument("--backup-and-apply", action="store_true", help="백업 후 규칙 적용")
    parser.add_argument("--confidence", type=float, default=0.8, help="최소 신뢰도 (0.0-1.0)")
    
    args = parser.parse_args()
    
    generator = YAMLRuleGenerator(args.input, args.output)
    
    if args.generate_yaml or args.backup_and_apply or not any(vars(args).values()):
        # 기본 동작: 전체 생성 실행
        result = generator.run_full_generation(args.confidence)
        return result


if __name__ == "__main__":
    main()