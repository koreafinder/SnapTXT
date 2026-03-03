#!/usr/bin/env python3
"""
SnapTXT Production 최소 UI 통합
3개 핵심 버튼: Apply, Show Report, Rollback

메인 UI에서 2분 내 문제 복구 가능하도록 설계
"""

import json
import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# Production 모듈들
from phase_3_0_production_api import apply, get_production_instance
from phase_3_0_ruleset_version_manager import get_version_manager, rollback_last
from phase_3_0_deployment_checklist import PreDeploymentChecker

class ProductionUI:
    """Production SnapTXT 통합 UI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SnapTXT Production Control")
        self.root.geometry("800x600")
        
        # 상태 변수들
        self.last_report_path = None
        self.current_mode = "conservative"
        self.status_text = tk.StringVar()
        self.status_text.set("Ready")
        
        self.setup_ui()
        self.refresh_status()
        
    def setup_ui(self):
        """UI 구성"""
        
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 제목
        title_label = ttk.Label(main_frame, text="SnapTXT Production Control", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 상태 표시
        status_frame = ttk.LabelFrame(main_frame, text="현재 상태", padding="10")
        status_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.status_display = ttk.Label(status_frame, textvariable=self.status_text)
        self.status_display.grid(row=0, column=0, sticky=tk.W)
        
        # 핵심 3대 버튼
        button_frame = ttk.LabelFrame(main_frame, text="핵심 기능", padding="10")
        button_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 1. Apply (Production) 버튼
        self.apply_button = ttk.Button(button_frame, text="Apply (Production)", 
                                     command=self.apply_production, style="Apply.TButton")
        self.apply_button.grid(row=0, column=0, padx=(0, 10), pady=5, sticky=(tk.W, tk.E))
        
        # 2. Show Last Report 버튼  
        self.report_button = ttk.Button(button_frame, text="Show Last Report",
                                      command=self.show_last_report)
        self.report_button.grid(row=0, column=1, padx=(0, 10), pady=5, sticky=(tk.W, tk.E))
        
        # 3. Rollback 버튼
        self.rollback_button = ttk.Button(button_frame, text="Rollback", 
                                        command=self.emergency_rollback, style="Rollback.TButton")
        self.rollback_button.grid(row=0, column=2, pady=5, sticky=(tk.W, tk.E))
        
        # 텍스트 입력 영역
        input_frame = ttk.LabelFrame(main_frame, text="텍스트 처리", padding="10")
        input_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 입력 텍스트
        ttk.Label(input_frame, text="입력 텍스트:").grid(row=0, column=0, sticky=tk.W)
        self.input_text = scrolledtext.ScrolledText(input_frame, height=8, width=80)
        self.input_text.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 10))
        
        # 모드 선택
        mode_frame = ttk.Frame(input_frame)
        mode_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        
        ttk.Label(mode_frame, text="모드:").grid(row=0, column=0, padx=(0, 10))
        self.mode_var = tk.StringVar(value="conservative")
        mode_combo = ttk.Combobox(mode_frame, textvariable=self.mode_var, state="readonly",
                                values=["conservative", "standard", "aggressive"])
        mode_combo.grid(row=0, column=1, padx=(0, 20))
        
        # 도메인 선택
        ttk.Label(mode_frame, text="도메인:").grid(row=0, column=2, padx=(0, 10))
        self.domain_var = tk.StringVar(value="essay") 
        domain_combo = ttk.Combobox(mode_frame, textvariable=self.domain_var, state="readonly",
                                  values=["novel", "essay", "textbook"])
        domain_combo.grid(row=0, column=3)
        
        # 결과 표시 영역
        result_frame = ttk.LabelFrame(main_frame, text="처리 결과", padding="10")
        result_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.result_text = scrolledtext.ScrolledText(result_frame, height=8, width=80)
        self.result_text.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 고급 기능 (접기/펼치기 가능)
        advanced_frame = ttk.LabelFrame(main_frame, text="고급 기능", padding="10")
        advanced_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 진단 3종 세트 버튼
        diag_button = ttk.Button(advanced_frame, text="진단 3종 세트 생성", command=self.generate_diagnostic_set)
        diag_button.grid(row=0, column=0, padx=(0, 10), pady=5)
        
        # 배포 체크리스트 버튼
        checklist_button = ttk.Button(advanced_frame, text="배포 전 체크리스트", command=self.run_deployment_checklist)
        checklist_button.grid(row=0, column=1, padx=(0, 10), pady=5)
        
        # 버전 정보 버튼
        version_button = ttk.Button(advanced_frame, text="버전 정보", command=self.show_version_info)
        version_button.grid(row=0, column=2, pady=5)
        
        # 그리드 가중치 설정
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(1, weight=1)
        
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        
        # 버튼 스타일
        style = ttk.Style()
        style.configure("Apply.TButton", foreground="darkgreen")
        style.configure("Rollback.TButton", foreground="darkred")
        
    def refresh_status(self):
        """상태 정보 새로고침"""
        
        try:
            version_manager = get_version_manager()
            current_version = version_manager.current_active_version
            
            production = get_production_instance()
            current_mode = production.safety_system.current_mode
            
            status = f"활성 버전: {current_version or 'None'} | 모드: {current_mode}"
            self.status_text.set(status)
            
        except Exception as e:
            self.status_text.set(f"상태 로드 실패: {e}")
            
    def apply_production(self):
        """1. Apply (Production) 실행"""
        
        input_text = self.input_text.get(1.0, tk.END).strip()
        
        if not input_text:
            messagebox.showwarning("입력 필요", "처리할 텍스트를 입력하세요.")
            return
            
        try:
            # 컨텍스트 설정
            context = {
                "domain": self.domain_var.get(),
                "safety_mode": self.mode_var.get()
            }
            
            self.result_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] 처리 시작...\n")
            self.result_text.update()
            
            # Production API 호출
            fixed_text, report_path = apply(input_text, context)
            
            self.last_report_path = report_path
            
            # 결과 표시
            self.result_text.insert(tk.END, f"✅ 처리 완료\n")
            self.result_text.insert(tk.END, f"📄 리포트: {report_path}\n\n")
            self.result_text.insert(tk.END, f"[원본]\n{input_text[:100]}...\n\n")
            self.result_text.insert(tk.END, f"[처리됨]\n{fixed_text[:100]}...\n\n")
            self.result_text.insert(tk.END, "=" * 50 + "\n")
            
            # 자동 스크롤
            self.result_text.see(tk.END)
            
            messagebox.showinfo("처리 완료", "텍스트 처리가 완료되었습니다.")
            
        except Exception as e:
            self.result_text.insert(tk.END, f"❌ 오류: {e}\n\n")
            messagebox.showerror("처리 오류", f"텍스트 처리 중 오류가 발생했습니다:\n{e}")
            
    def show_last_report(self):
        """2. Show Last Report 실행"""
        
        if not self.last_report_path:
            # 가장 최근 리포트 찾기
            reports_dir = Path("production_reports")
            if reports_dir.exists():
                report_files = sorted(reports_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
                if report_files:
                    self.last_report_path = str(report_files[0])
                    
        if not self.last_report_path or not Path(self.last_report_path).exists():
            messagebox.showinfo("리포트 없음", "표시할 리포트가 없습니다.")
            return
            
        try:
            # 리포트 내용 읽기
            with open(self.last_report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
                
            # 새 창에서 리포트 표시
            self.show_report_window(report_data)
            
        except Exception as e:
            messagebox.showerror("리포트 오류", f"리포트를 읽을 수 없습니다:\n{e}")
            
    def emergency_rollback(self):
        """3. 긴급 Rollback 실행"""
        
        # 확인 다이얼로그
        if not messagebox.askyesno("롤백 확인", 
                                  "마지막 변경사항을 롤백하시겠습니까?\n"
                                  "이 작업은 되돌릴 수 없습니다."):
            return
            
        try:
            self.result_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] 롤백 시작...\n")
            self.result_text.update()
            
            # 롤백 실행
            rollback_success = rollback_last("UI 긴급 롤백")
            
            if rollback_success:
                self.result_text.insert(tk.END, "✅ 롤백 완료\n\n")
                messagebox.showinfo("롤백 완료", "마지막 변경사항이 성공적으로 롤백되었습니다.")
                self.refresh_status()  # 상태 새로고침
            else:
                self.result_text.insert(tk.END, "❌ 롤백 실패\n\n") 
                messagebox.showerror("롤백 실패", "롤백에 실패했습니다.")
                
        except Exception as e:
            self.result_text.insert(tk.END, f"❌ 롤백 오류: {e}\n\n")
            messagebox.showerror("롤백 오류", f"롤백 중 오류가 발생했습니다:\n{e}")
            
    def generate_diagnostic_set(self):
        """진단 3종 세트 생성"""
        
        try:
            # 1. 가장 최근 gate 결과 찾기
            gate_files = list(Path("production_reports").glob("gate_evaluation_*.json"))
            latest_gate = None
            if gate_files:
                latest_gate = max(gate_files, key=lambda x: x.stat().st_mtime)
                
            # 2. 가장 최근 적용 로그 찾기  
            log_files = list(Path("production_reports").glob("processing_report_*.json"))
            latest_log = None
            if log_files:
                latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
                
            # 3. 현재 환경 상태
            version_manager = get_version_manager()
            production = get_production_instance()
            
            current_state = {
                "timestamp": datetime.now().isoformat(),
                "active_ruleset_id": version_manager.current_active_version,
                "safety_mode": production.safety_system.current_mode,
                "available_versions": len(version_manager.versions),
                "rollback_available": len(version_manager.rollback_history) > 0
            }
            
            # 진단 세트 파일 생성
            diagnostic_set = {
                "generated_at": datetime.now().isoformat(),
                "gate_result_path": str(latest_gate) if latest_gate else None,
                "application_log_path": str(latest_log) if latest_log else None, 
                "system_state": current_state
            }
            
            # 저장
            diagnostic_path = Path(f"diagnostic_set_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(diagnostic_path, 'w', encoding='utf-8') as f:
                json.dump(diagnostic_set, f, indent=2, ensure_ascii=False)
                
            # 사용자에게 정보 표시
            info_text = f"📋 진단 3종 세트 생성됨: {diagnostic_path}\n\n"
            info_text += f"1️⃣ Gate 결과: {latest_gate.name if latest_gate else 'None'}\n"
            info_text += f"2️⃣ 적용 로그: {latest_log.name if latest_log else 'None'}\n"  
            info_text += f"3️⃣ 현재 상태: {current_state['active_ruleset_id']} ({current_state['safety_mode']})\n"
            
            messagebox.showinfo("진단 세트 생성", info_text)
            
        except Exception as e:
            messagebox.showerror("진단 세트 오류", f"진단 세트 생성 실패:\n{e}")
            
    def run_deployment_checklist(self):
        """배포 전 체크리스트 실행"""
        
        try:
            checker = PreDeploymentChecker()
            deployment_ready, report = checker.run_full_checklist()
            
            # 결과 메시지
            if deployment_ready:
                messagebox.showinfo("체크리스트 완료", 
                                   f"✅ 모든 배포 전 체크 통과!\n"
                                   f"Production 런칭 가능 상태입니다.")
            else:
                critical_count = len(report.get("critical_failures", []))
                messagebox.showwarning("체크리스트 실패",
                                     f"❌ {critical_count}개 Critical Issues 발견\n"
                                     f"배포 전 문제 해결이 필요합니다.")
                
        except Exception as e:
            messagebox.showerror("체크리스트 오류", f"체크리스트 실행 실패:\n{e}")
            
    def show_version_info(self):
        """버전 정보 표시"""
        
        try:
            version_manager = get_version_manager()
            versions = version_manager.list_available_versions()
            
            # 버전 정보 창
            version_window = tk.Toplevel(self.root)
            version_window.title("버전 정보")
            version_window.geometry("600x400")
            
            # 버전 목록
            version_text = scrolledtext.ScrolledText(version_window, wrap=tk.WORD)
            version_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            version_text.insert(tk.END, "📦 RuleSet 버전 정보\n")
            version_text.insert(tk.END, "=" * 50 + "\n\n")
            
            for version in versions:
                status_icon = "🟢" if version["is_active"] else "⚪"
                version_text.insert(tk.END, f"{status_icon} {version['version_id']}\n")
                version_text.insert(tk.END, f"   이름: {version['name']}\n")
                version_text.insert(tk.END, f"   규칙 수: {version['rule_count']}개\n")
                version_text.insert(tk.END, f"   상태: {version['status']}\n")
                version_text.insert(tk.END, f"   생성: {version['created_at'][:19]}\n\n")
                
        except Exception as e:
            messagebox.showerror("버전 정보 오류", f"버전 정보 조회 실패:\n{e}")
            
    def show_report_window(self, report_data):
        """리포트 내용을 새 창에서 표시"""
        
        report_window = tk.Toplevel(self.root)
        report_window.title("처리 리포트")
        report_window.geometry("700x500")
        
        report_text = scrolledtext.ScrolledText(report_window, wrap=tk.WORD)
        report_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # JSON을 읽기 쉬운 형태로 표시
        report_str = json.dumps(report_data, indent=2, ensure_ascii=False)
        report_text.insert(tk.END, report_str)
        
    def run(self):
        """UI 실행"""
        
        self.root.mainloop()

def main():
    """Production UI 실행"""
    
    print("🖥️ SnapTXT Production UI 시작...")
    
    try:
        app = ProductionUI()
        app.run()
    except Exception as e:
        print(f"❌ UI 실행 실패: {e}")

if __name__ == "__main__":
    main()