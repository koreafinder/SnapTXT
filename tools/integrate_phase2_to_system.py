#!/usr/bin/env python3
"""
Phase 1 + Phase 2 통합 규칙을 실제 SnapTXT 시스템에 적용

learned_rules_advanced.yaml의 Phase 2 규칙들을
snaptxt/postprocess/patterns/stage3_rules.yaml에 통합
"""

import yaml
from pathlib import Path
import shutil
from datetime import datetime

class SnapTXTSystemIntegrator:
    """Phase 1 + Phase 2 통합 규칙을 실제 시스템에 적용"""
    
    def __init__(self):
        # 파일 경로들
        self.phase2_rules_file = Path("../learning_data/learned_rules_advanced.yaml")
        self.system_rules_file = Path("../snaptxt/postprocess/patterns/stage3_rules.yaml") 
        self.backup_dir = Path("../backups")
        self.backup_dir.mkdir(exist_ok=True)
        
    def backup_current_system_rules(self) -> str:
        """현재 시스템 규칙 파일 백업"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"system_stage3_rules_backup_{timestamp}.yaml"
        
        shutil.copy2(self.system_rules_file, backup_file)
        print(f"📁 시스템 규칙 백업: {backup_file}")
        
        return str(backup_file)
    
    def load_phase2_rules(self) -> dict:
        """Phase 2 학습 규칙 로드"""
        if not self.phase2_rules_file.exists():
            print(f"❌ Phase 2 규칙 파일 없음: {self.phase2_rules_file}")
            return {}
            
        with open(self.phase2_rules_file, 'r', encoding='utf-8') as f:
            phase2_data = yaml.safe_load(f)
        
        phase2_rules = phase2_data.get('stage3_postprocessing', {})
        characters = phase2_rules.get('characters', [])
        
        print(f"📚 Phase 2 규칙 로드: {len(characters)}개 문자 규칙")
        return phase2_rules
    
    def load_current_system_rules(self) -> dict:
        """현재 시스템 규칙 로드"""
        with open(self.system_rules_file, 'r', encoding='utf-8') as f:
            system_data = yaml.safe_load(f)
        
        print(f"🔧 현재 시스템 규칙 로드 완료")
        return system_data
    
    def convert_phase2_rules_to_system_format(self, phase2_rules: dict) -> dict:
        """Phase 2 규칙을 시스템 포맷으로 변환"""
        characters = phase2_rules.get('characters', [])
        
        # Phase 2 학습 규칙들을 replacements 형태로 변환
        new_replacements = {}
        
        for rule in characters:
            pattern = rule.get('pattern', '')
            replacement = rule.get('replacement', '')
            confidence = rule.get('confidence', 0.0)
            learned = rule.get('learned', False)
            
            if pattern and replacement and pattern != replacement and learned:
                # 높은 신뢰도 규칙만 적용 (80% 이상)
                if confidence >= 0.8:
                    new_replacements[pattern] = replacement
                    print(f"   ✅ {pattern} → {replacement} (신뢰도: {confidence:.0%})")
        
        print(f"🧠 Phase 2 변환 완료: {len(new_replacements)}개 규칙")
        return new_replacements
    
    def integrate_rules(self, system_data: dict, phase2_replacements: dict) -> dict:
        """시스템 규칙에 Phase 2 규칙 통합"""
        # characters.replacements에 Phase 2 규칙 추가
        if 'characters' not in system_data:
            system_data['characters'] = {}
        
        if 'replacements' not in system_data['characters']:
            system_data['characters']['replacements'] = {}
        
        current_replacements = system_data['characters']['replacements']
        original_count = len(current_replacements)
        
        # Phase 2 규칙들 추가 (기존 규칙과 중복되지 않는 것만)
        added_count = 0
        for pattern, replacement in phase2_replacements.items():
            if pattern not in current_replacements:
                current_replacements[pattern] = replacement
                added_count += 1
            else:
                print(f"   ⚠️ 중복 규칙 무시: {pattern} → {replacement}")
        
        print(f"🔄 통합 완료: {original_count}개 → {len(current_replacements)}개 (+{added_count}개)")
        
        # 메타데이터 업데이트
        if 'metadata' not in system_data:
            system_data['metadata'] = {}
        
        system_data['metadata'].update({
            'last_phase2_integration': datetime.now().isoformat(),
            'phase2_rules_added': added_count,
            'phase2_source': str(self.phase2_rules_file),
            'integration_version': '1.0'
        })
        
        return system_data
    
    def save_integrated_rules(self, integrated_data: dict) -> str:
        """통합된 규칙을 시스템 파일에 저장"""
        with open(self.system_rules_file, 'w', encoding='utf-8') as f:
            yaml.dump(integrated_data, f, allow_unicode=True, indent=2, sort_keys=False)
        
        print(f"💾 통합 규칙 저장: {self.system_rules_file}")
        return str(self.system_rules_file)
    
    def verify_integration(self) -> dict:
        """통합 결과 검증"""
        # 시스템 규칙 재로드
        with open(self.system_rules_file, 'r', encoding='utf-8') as f:
            verification_data = yaml.safe_load(f)
        
        characters = verification_data.get('characters', {})
        replacements = characters.get('replacements', {})
        metadata = verification_data.get('metadata', {})
        
        verification_result = {
            'total_character_rules': len(replacements),
            'phase2_integration_date': metadata.get('last_phase2_integration'),
            'phase2_rules_added': metadata.get('phase2_rules_added', 0),
            'integration_successful': True
        }
        
        print(f"✅ 검증 완료: {verification_result['total_character_rules']}개 문자 규칙")
        print(f"   Phase 2 통합: {verification_result['phase2_rules_added']}개 추가")
        
        return verification_result
    
    def run_complete_integration(self) -> dict:
        """전체 통합 과정 실행"""
        print("🚀 Phase 1 + Phase 2 → 실제 SnapTXT 시스템 통합 시작")
        
        # 1. 현재 시스템 규칙 백업
        backup_file = self.backup_current_system_rules()
        
        # 2. Phase 2 학습 규칙 로드
        phase2_rules = self.load_phase2_rules()
        
        if not phase2_rules:
            print("❌ Phase 2 규칙을 로드할 수 없습니다.")
            return {"success": False, "error": "No Phase 2 rules"}
        
        # 3. 현재 시스템 규칙 로드
        system_data = self.load_current_system_rules()
        
        # 4. Phase 2 규칙을 시스템 포맷으로 변환
        phase2_replacements = self.convert_phase2_rules_to_system_format(phase2_rules)
        
        if not phase2_replacements:
            print("❌ 변환할 Phase 2 규칙이 없습니다.")
            return {"success": False, "error": "No converted rules"}
        
        # 5. 규칙 통합
        integrated_data = self.integrate_rules(system_data, phase2_replacements)
        
        # 6. 통합된 규칙 저장
        output_file = self.save_integrated_rules(integrated_data)
        
        # 7. 통합 결과 검증
        verification = self.verify_integration()
        
        result = {
            "success": True,
            "backup_file": backup_file,
            "output_file": output_file,
            "verification": verification,
            "phase2_rules_source": str(self.phase2_rules_file),
            "integration_timestamp": datetime.now().isoformat()
        }
        
        print(f"\n🎉 통합 완료!")
        print(f"   백업 파일: {backup_file}")
        print(f"   통합 파일: {output_file}")
        print(f"   추가된 규칙: {verification['phase2_rules_added']}개")
        
        return result


def main():
    """메인 실행 함수"""
    integrator = SnapTXTSystemIntegrator()
    
    try:
        result = integrator.run_complete_integration()
        
        if result.get('success'):
            print("\n📢 이제 SnapTXT 프로그램을 실행하면 Phase 2 학습 규칙이 적용됩니다!")
            print("   29개 이미지 중 아무거나 OCR 테스트해보세요.")
        else:
            print(f"❌ 통합 실패: {result.get('error')}")
            
        return result
        
    except Exception as e:
        print(f"💥 오류 발생: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    main()