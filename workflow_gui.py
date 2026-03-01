#!/usr/bin/env python3
"""SnapTXT AI 협업 워크플로우 GUI - 3-클릭으로 완벽한 프로젝트 관리"""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, scrolledtext
import subprocess
import threading
import sys
from pathlib import Path
import json
import datetime as dt

# 프로젝트 루트 및 도구 경로
PROJECT_ROOT = Path(__file__).resolve().parent
TOOLS_PATH = PROJECT_ROOT / "tools"


class WorkflowGUI:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        self.create_widgets()
        self.update_status()
        
    def setup_window(self):
        """윈도우 기본 설정"""
        self.root.title("SnapTXT AI 협업 워크플로우")
        self.root.geometry("600x700")
        self.root.resizable(True, True)
        
        # 아이콘 설정 (있다면)
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
            
        # 창 가운데 배치
        self.root.geometry("+%d+%d" % (
            (self.root.winfo_screenwidth() / 2 - 300),
            (self.root.winfo_screenheight() / 2 - 350)
        ))

    def create_widgets(self):
        """GUI 위젯들 생성"""
        
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 제목
        title_label = ttk.Label(main_frame, text="🤖 SnapTXT AI 협업 워크플로우", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 상태 표시 프레임
        self.create_status_frame(main_frame)
        
        # 메인 버튼들
        self.create_main_buttons(main_frame)
        
        # 결과 출력 영역
        self.create_output_area(main_frame)
        
        # 하단 정보
        self.create_bottom_info(main_frame)
        
        # 그리드 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

    def create_status_frame(self, parent):
        """현재 상태 표시 프레임"""
        status_frame = ttk.LabelFrame(parent, text="📊 현재 프로젝트 상태", padding="10")
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # 상태 레이블들
        self.project_label = ttk.Label(status_frame, text="프로젝트: SnapTXT")
        self.project_label.grid(row=0, column=0, sticky=tk.W)
        
        self.plans_label = ttk.Label(status_frame, text="활성 기획서: 로딩중...")
        self.plans_label.grid(row=1, column=0, sticky=tk.W)
        
        self.goals_label = ttk.Label(status_frame, text="메인 목표: 로딩중...")
        self.goals_label.grid(row=2, column=0, sticky=tk.W)
        
        self.git_label = ttk.Label(status_frame, text="Git 상태: 확인중...")
        self.git_label.grid(row=3, column=0, sticky=tk.W)

    def create_main_buttons(self, parent):
        """메인 워크플로우 버튼들"""
        buttons_frame = ttk.Frame(parent)
        buttons_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        # Start Work 버튼
        self.start_btn = ttk.Button(
            buttons_frame, 
            text="🚀 Start Work\n상황파악 + AI 컨텍스트",
            command=self.start_work,
            width=25,
            padding="10"
        )
        self.start_btn.grid(row=0, column=0, padx=10, pady=5)
        
        # Create Plan 버튼  
        self.create_btn = ttk.Button(
            buttons_frame,
            text="💡 Create Plan\n새 기획서 생성 + 자동연동",
            command=self.create_plan,
            width=25,
            padding="10"
        )
        self.create_btn.grid(row=0, column=1, padx=10, pady=5)
        
        # Finish Work 버튼
        self.finish_btn = ttk.Button(
            buttons_frame,
            text="🎉 Finish Work\n작업완료 + Git관리 + 검증",
            command=self.finish_work,
            width=25,
            padding="10"
        )
        self.finish_btn.grid(row=1, column=0, columnspan=2, padx=10, pady=15)

    def create_output_area(self, parent):
        """결과 출력 영역"""
        output_frame = ttk.LabelFrame(parent, text="📄 실행 결과", padding="10")
        output_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=20)
        
        # 스크롤 가능한 텍스트 영역
        self.output_text = scrolledtext.ScrolledText(
            output_frame, 
            height=15, 
            width=70,
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 출력 영역 확장 설정
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        parent.rowconfigure(3, weight=1)

    def create_bottom_info(self, parent):
        """하단 정보 표시"""
        bottom_frame = ttk.Frame(parent)
        bottom_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        
        # 새로고침 버튼
        refresh_btn = ttk.Button(bottom_frame, text="🔄 상태 새로고침", command=self.update_status)
        refresh_btn.grid(row=0, column=0, padx=(0, 20))
        
        # 도구들 바로가기
        tools_label = ttk.Label(bottom_frame, text="빠른 실행:")
        tools_label.grid(row=0, column=1, padx=(0, 10))
        
        docs_btn = ttk.Button(bottom_frame, text="📋 문서체크", 
                             command=lambda: self.run_command("check_docs.bat"))
        docs_btn.grid(row=0, column=2, padx=5)
        
        regression_btn = ttk.Button(bottom_frame, text="🧪 회귀테스트", 
                                   command=self.run_regression_test)
        regression_btn.grid(row=0, column=3, padx=5)

    def append_output(self, text):
        """출력 영역에 텍스트 추가"""
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)
        self.root.update()

    def clear_output(self):
        """출력 영역 지우기"""
        self.output_text.delete(1.0, tk.END)

    def run_command(self, command, shell=True):
        """명령어 실행 및 결과 출력"""
        def run():
            try:
                self.append_output(f"\n🔄 실행 중: {command}")
                self.append_output("=" * 50)
                
                process = subprocess.Popen(
                    command,
                    shell=shell,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=PROJECT_ROOT,
                    encoding='utf-8'
                )
                
                # 실시간 출력
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        self.append_output(output.strip())
                
                # 에러 출력
                stderr = process.stderr.read()
                if stderr:
                    self.append_output(f"\n⚠️ 경고/에러: {stderr}")
                
                # 완료 메시지
                if process.returncode == 0:
                    self.append_output(f"\n✅ 명령어 완료: {command}")
                else:
                    self.append_output(f"\n❌ 명령어 실패 (코드: {process.returncode}): {command}")
                    
                self.append_output("=" * 50 + "\n")
                
            except Exception as e:
                self.append_output(f"\n💥 실행 오류: {e}")
                
        # 별도 스레드에서 실행 (GUI 프리징 방지)
        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def start_work(self):
        """Start Work 버튼"""
        self.clear_output()
        self.append_output("🚀 작업 세션을 시작합니다...")
        self.append_output("현재 상황을 파악하고 AI 컨텍스트를 로딩합니다.\n")
        
        self.run_command("start_work.bat")
        
        # 상태 업데이트
        self.root.after(2000, self.update_status)

    def create_plan(self):
        """Create Plan 버튼"""
        # 기획서 이름 입력
        plan_name = simpledialog.askstring(
            "새 기획서 생성",
            "기획서 이름을 입력하세요:",
            initialvalue=""
        )
        
        if not plan_name:
            return
            
        # 카테고리 선택
        category_window = tk.Toplevel(self.root)
        category_window.title("카테고리 선택")
        category_window.geometry("300x200")
        category_window.transient(self.root)
        category_window.grab_set()
        
        # 창 가운데 배치
        category_window.geometry("+%d+%d" % (
            (self.root.winfo_x() + 150),
            (self.root.winfo_y() + 150)
        ))
        
        selected_category = tk.StringVar(value="plans")
        
        ttk.Label(category_window, text="기획서 카테고리를 선택하세요:", 
                 font=("Arial", 10)).pack(pady=20)
        
        categories = [
            ("plans", "📋 실행 계획/기능 기획"),
            ("reference", "📚 매뉴얼/가이드/참고자료"),  
            ("analysis", "📊 분석/연구/실험 보고서")
        ]
        
        for value, desc in categories:
            ttk.Radiobutton(category_window, text=desc, variable=selected_category, 
                          value=value).pack(anchor=tk.W, padx=30, pady=5)
        
        def on_ok():
            category_window.destroy()
            self.create_plan_execute(plan_name, selected_category.get())
            
        def on_cancel():
            category_window.destroy()
            
        btn_frame = ttk.Frame(category_window)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="확인", command=on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="취소", command=on_cancel).pack(side=tk.LEFT, padx=10)

    def create_plan_execute(self, plan_name, category):
        """기획서 생성 실행"""
        self.clear_output()
        self.append_output(f"💡 새 기획서를 생성합니다...")
        self.append_output(f"📄 이름: {plan_name}")
        self.append_output(f"📂 카테고리: {category}")
        self.append_output("")
        
        command = f'create_plan.bat "{plan_name}" "{category}"'
        self.run_command(command)
        
        # 상태 업데이트
        self.root.after(3000, self.update_status)

    def finish_work(self):
        """Finish Work 버튼"""
        # 커밋 메시지 입력
        commit_msg = simpledialog.askstring(
            "작업 완료",
            "Git 커밋 메시지를 입력하세요:",
            initialvalue=f"작업 정리 ({dt.datetime.now().strftime('%Y-%m-%d')})"
        )
        
        if not commit_msg:
            return
            
        self.clear_output()
        self.append_output("🎉 작업을 완료하고 정리합니다...")
        self.append_output(f"💬 커밋 메시지: {commit_msg}")
        self.append_output("")
        
        command = f'finish_work.bat "{commit_msg}"'
        self.run_command(command)
        
        # 상태 업데이트
        self.root.after(5000, self.update_status)

    def run_regression_test(self):
        """회귀 테스트 실행"""
        self.clear_output()
        self.append_output("🧪 회귀 테스트를 실행합니다...")
        self.append_output("Stage 3 후처리 시스템의 자동화된 검증을 수행합니다.")
        self.append_output("시간이 다소 걸릴 수 있습니다.\n")
        
        # UTF-8 인코딩 설정 포함
        command = 'chcp 65001 > $null; powershell -ExecutionPolicy Bypass -File "scripts\\run_regression.ps1"'
        self.run_command(command)

    def update_status(self):
        """현재 상태 정보 업데이트"""
        def update():
            try:
                # show_current_status.py 실행해서 정보 가져오기
                result = subprocess.run(
                    [sys.executable, "tools/show_current_status.py", "--quick-summary"],
                    capture_output=True,
                    text=True,
                    cwd=PROJECT_ROOT
                )
                
                if result.returncode == 0:
                    output = result.stdout
                    
                    # 간단한 파싱으로 상태 정보 추출
                    lines = output.split('\n')
                    
                    for line in lines:
                        if '**활성 기획서**' in line:
                            plans_info = line.split(':')[1].strip()
                            self.plans_label.config(text=f"활성 기획서: {plans_info}")
                        elif '**메인 목표**' in line:
                            goals_info = line.split(':')[1].strip()
                            self.goals_label.config(text=f"메인 목표: {goals_info}")
                
                # Git 상태 확인
                git_result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    cwd=PROJECT_ROOT
                )
                
                if git_result.returncode == 0:
                    if git_result.stdout.strip():
                        self.git_label.config(text="Git 상태: 변경사항 있음 🔴")
                    else:
                        self.git_label.config(text="Git 상태: 클린 ✅")
                else:
                    self.git_label.config(text="Git 상태: 저장소 없음")
                    
            except Exception as e:
                self.plans_label.config(text="활성 기획서: 오류")
                self.goals_label.config(text="메인 목표: 오류")
                self.git_label.config(text="Git 상태: 오류")
                print(f"상태 업데이트 오류: {e}")
                
        # 별도 스레드에서 실행
        thread = threading.Thread(target=update, daemon=True)
        thread.start()


def main():
    """메인 함수"""
    
    # 프로젝트 루트에서 실행되는지 확인
    if not (PROJECT_ROOT / "tools").exists():
        messagebox.showerror("오류", 
                           f"SnapTXT 프로젝트 루트에서 실행해주세요.\n"
                           f"현재 위치: {PROJECT_ROOT}")
        return
        
    # GUI 실행
    root = tk.Tk()
    app = WorkflowGUI(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("GUI 종료")


if __name__ == "__main__":
    main()