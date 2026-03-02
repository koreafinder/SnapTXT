#!/usr/bin/env python3
"""
🚀 VS Code AI 개발 성능 최적화 도구
- 채팅창 랙 해결
- 메모리 사용량 최적화  
- Python/AI 개발 환경 튜닝
- 불필요한 확장 비활성화
"""

import json
import os
import sys
import shutil
import psutil
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import tempfile

class VSCodeAIOptimizer:
    def __init__(self):
        self.vscode_data_dir = self._find_vscode_data_dir()
        self.settings_file = self.vscode_data_dir / "User" / "settings.json"
        self.extensions_dir = self.vscode_data_dir / "extensions"
        
    def _find_vscode_data_dir(self) -> Path:
        """VS Code 데이터 디렉토리 찾기"""
        possible_paths = [
            Path(os.environ.get("APPDATA", "")) / "Code",
            Path(os.environ.get("USERPROFILE", "")) / ".vscode",
            Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Roaming" / "Code"
        ]
        
        for path in possible_paths:
            if path.exists() and (path / "User").exists():
                return path
                
        raise FileNotFoundError("VS Code 설정 디렉토리를 찾을 수 없습니다.")
    
    def backup_settings(self) -> str:
        """현재 설정 백업"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = f"vscode_settings_backup_{timestamp}.json"
        
        if self.settings_file.exists():
            shutil.copy2(self.settings_file, backup_file)
            print(f"✅ 설정 백업 완료: {backup_file}")
            return backup_file
        return ""
    
    def get_memory_usage(self) -> Dict:
        """현재 시스템 메모리 사용량 확인"""
        memory = psutil.virtual_memory()
        vscode_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                if 'code' in proc.info['name'].lower():
                    vscode_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'memory_mb': proc.info['memory_info'].rss / 1024 / 1024
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return {
            'total_gb': memory.total / 1024**3,
            'available_gb': memory.available / 1024**3,
            'used_percent': memory.percent,
            'vscode_processes': vscode_processes
        }
    
    def get_optimal_settings(self) -> Dict:
        """AI/Python 개발에 최적화된 VS Code 설정"""
        return {
            # 🧠 AI 채팅 성능 최적화
            "github.copilot.advanced": {
                "secret_key": "github.copilot.windowless_chat_location",
                "assignable_value": "chatView"
            },
            "github.copilot.chat.experimental.quickFixMode": False,
            "github.copilot.chat.experimental.codeActions": False,
            
            # ⚡ 메모리 관리
            "files.watcherExclude": {
                "**/.git/objects/**": True,
                "**/.git/subtree-cache/**": True,
                "**/node_modules/*/**": True,
                "**/__pycache__/**": True,
                "**/venv/**": True,
                "**/.venv/**": True,
                "**/env/**": True,
                "**/logs/**": True,
                "**/tmp/**": True,
                "**/temp/**": True,
                "**/*.pyc": True,
                "**/experiments/results/**": True
            },
            "files.exclude": {
                "**/__pycache__": True,
                "**/*.pyc": True,
                "**/node_modules": True,
                "**/.git": True,
                "**/venv": True,
                "**/.venv": True
            },
            "search.exclude": {
                "**/__pycache__": True,
                "**/venv": True,
                "**/.venv": True,
                "**/node_modules": True,
                "**/logs": True
            },
            
            # 🐍 Python 성능 최적화
            "python.analysis.memory.keepLibraryAst": False,
            "python.analysis.autoSearchPaths": True,
            "python.analysis.indexing": True,
            "python.analysis.packageIndexDepths": [
                {"name": "sklearn", "depth": 2},
                {"name": "matplotlib", "depth": 2},
                {"name": "pandas", "depth": 2},
                {"name": "numpy", "depth": 2},
                {"name": "", "depth": 5}
            ],
            
            # 💾 에디터 성능
            "editor.suggest.preview": True,
            "editor.suggest.maxVisibleSuggestions": 8,
            "editor.quickSuggestionsDelay": 10,
            "editor.hover.delay": 300,
            "editor.parameterHints.enabled": True,
            "editor.lightbulb.enabled": True,
            
            # 🔄 자동 저장/업데이트
            "files.autoSave": "afterDelay",
            "files.autoSaveDelay": 2000,
            "extensions.autoUpdate": False,
            "update.mode": "manual",
            
            # 📊 터미널 최적화 
            "terminal.integrated.gpuAcceleration": "auto",
            "terminal.integrated.persistentSessionReviveProcess": "never",
            "terminal.integrated.enableMultiLinePasteWarning": False,
            
            # 🎨 UI 최적화
            "workbench.editor.limit.enabled": True,
            "workbench.editor.limit.value": 8,
            "workbench.editor.limit.perEditorGroup": True,
            "workbench.startupEditor": "none",
            "workbench.tips.enabled": False,
            "workbench.editor.enablePreview": False,
            
            # 🔧 디버깅 최적화
            "debug.console.historySuggestions": False,
            "debug.internalConsoleOptions": "neverOpen",
            
            # 📝 Git 성능
            "git.decorations.enabled": True,
            "git.enableSmartCommit": True,
            "git.autofetch": False,
            "git.autoStash": False,
            
            # 🚫 불필요한 기능 비활성화
            "telemetry.telemetryLevel": "off",
            "workbench.enableExperiments": False,
            "workbench.settings.enableNaturalLanguageSearch": False,
            "extensions.ignoreRecommendations": True,
            
            # 📏 성능 모니터링
            "application.experimental.rendererProfiling": False,
            "window.profileStartup": False
        }
    
    def get_problematic_extensions(self) -> List[str]:
        """성능에 영향을 줄 수 있는 확장 목록"""
        return [
            # 무거운 확장들
            "ms-vscode.vscode-typescript-next",
            "streetsidesoftware.code-spell-checker",
            "ms-vscode.hexeditor",
            "ms-vscode.vscode-json",
            
            # 불필요할 수 있는 확장들
            "ms-vscode.references-view",
            "ms-vscode.outline-map",
            "redis.redis-for-vscode",
            
            # 테마/UI (성능 영향)
            "ms-vscode.theme-*",
            "PKief.material-icon-theme",
            "vscode-icons-team.vscode-icons"
        ]
    
    def optimize_settings(self):
        """VS Code 설정 최적화 실행"""
        print("🚀 VS Code AI 최적화 시작...")
        
        # 백업
        backup_file = self.backup_settings()
        
        # 현재 설정 로드
        current_settings = {}
        if self.settings_file.exists():
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                try:
                    current_settings = json.load(f)
                except json.JSONDecodeError:
                    print("⚠️ 기존 설정 파일이 손상되었습니다. 새로 생성합니다.")
                    current_settings = {}
        
        # 최적화 설정 적용
        optimal_settings = self.get_optimal_settings()
        current_settings.update(optimal_settings)
        
        # settings.json 저장
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(current_settings, f, indent=2, ensure_ascii=False)
            
        print(f"✅ 설정 최적화 완료: {self.settings_file}")
        return True
    
    def clean_cache(self):
        """VS Code 캐시 정리"""
        print("🧹 캐시 정리 중...")
        
        cache_dirs = [
            self.vscode_data_dir / "User" / "workspaceStorage",
            self.vscode_data_dir / "CachedExtensions",
            self.vscode_data_dir / "logs"
        ]
        
        cleaned_mb = 0
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                try:
                    # 크기 계산
                    size_before = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
                    
                    # 정리 (일부 파일만)
                    for file in cache_dir.rglob('*.log'):
                        if file.is_file() and file.stat().st_size > 10*1024*1024:  # 10MB 이상
                            file.unlink()
                    
                    for file in cache_dir.rglob('*.tmp'):
                        if file.is_file():
                            file.unlink()
                            
                    # 크기 재계산
                    size_after = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
                    cleaned_mb += (size_before - size_after) / 1024 / 1024
                    
                except Exception as e:
                    print(f"⚠️ 캐시 정리 오류 ({cache_dir.name}): {e}")
                    continue
        
        print(f"✅ 캐시 정리 완료: {cleaned_mb:.1f}MB 절약")
        return cleaned_mb
    
    def get_extension_recommendations(self) -> Dict:
        """AI/Python 개발에 필수적인 확장 vs 비활성화 권장"""
        return {
            'essential': [
                'ms-python.python',
                'ms-python.vscode-pylance', 
                'github.copilot',
                'github.copilot-chat',
                'ms-vscode.vscode-json'
            ],
            'recommended_disable': [
                'ms-vscode.hexeditor',
                'streetsidesoftware.code-spell-checker',
                'ms-vscode.references-view',
                'bradlc.vscode-tailwindcss'
            ]
        }
    
    def run_optimization(self):
        """전체 최적화 실행"""
        print("=" * 60)
        print("🤖 VS Code AI 개발 환경 최적화")
        print("=" * 60)
        
        # 1. 현재 상태 확인
        print("\n📊 현재 시스템 상태:")
        memory_info = self.get_memory_usage()
        print(f"   💾 메모리: {memory_info['used_percent']:.1f}% 사용중")
        print(f"   🔢 VS Code 프로세스: {len(memory_info['vscode_processes'])}개")
        
        total_vscode_memory = sum(proc['memory_mb'] for proc in memory_info['vscode_processes'])
        print(f"   📈 VS Code 메모리 사용량: {total_vscode_memory:.1f}MB")
        
        # 2. 설정 최적화
        print("\n⚙️ VS Code 설정 최적화...")
        self.optimize_settings()
        
        # 3. 캐시 정리
        print("\n🧹 캐시 및 임시파일 정리...")
        cleaned_mb = self.clean_cache()
        
        # 4. 확장 권장사항
        print("\n📦 확장 프로그램 권장사항:")
        recommendations = self.get_extension_recommendations()
        print("   ✅ 필수 확장:")
        for ext in recommendations['essential']:
            print(f"      - {ext}")
        print("   🔄 비활성화 권장:")
        for ext in recommendations['recommended_disable']:
            print(f"      - {ext}")
        
        # 5. 결과 요약
        print("\n" + "=" * 60)
        print("✅ 최적화 완료!")
        print("=" * 60)
        print("📋 적용된 최적화:")
        print("   🧠 AI 채팅 응답성 개선")
        print("   ⚡ 메모리 사용량 최적화")  
        print("   🐍 Python IntelliSense 성능 향상")
        print("   🔄 자동 저장/업데이트 조정")
        print(f"   💾 {cleaned_mb:.1f}MB 디스크 공간 확보")
        print("\n💡 VS Code를 재시작하면 설정이 완전히 적용됩니다.")
        print("💡 문제가 발생하면 백업된 설정으로 복구 가능합니다.")
        
        return True

def main():
    """메인 실행 함수"""
    try:
        optimizer = VSCodeAIOptimizer()
        optimizer.run_optimization()
        
        print("\n🔄 지금 VS Code를 재시작하시겠습니까? (y/N): ", end='')
        choice = input().strip().lower()
        
        if choice in ['y', 'yes']:
            print("🔄 VS Code 재시작 중...")
            # VS Code 프로세스 종료
            subprocess.run(['taskkill', '/f', '/im', 'Code.exe'], 
                         capture_output=True, shell=True)
            time.sleep(2)
            # VS Code 재실행
            subprocess.Popen(['code', '.'], shell=True)
            print("✅ VS Code가 재시작되었습니다!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("💡 VS Code를 관리자 권한으로 실행하거나 수동으로 재시작해보세요.")
        return False
        
    return True

if __name__ == "__main__":
    main()