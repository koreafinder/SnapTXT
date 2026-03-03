#!/usr/bin/env python3
"""
GPT 텍스트 → Ground Truth JSON 자동 변환기
GPT에서 추출한 텍스트를 복사 붙여넣기하면 자동으로 JSON 생성

사용법:
1. GPT에서 텍스트 추출 결과 복사
2. 이 스크립트 실행 후 붙여넣기
3. 자동으로 파일명 매칭 + JSON 생성
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox, ttk

class GPTTextToJSONConverter:
    """GPT 텍스트를 Ground Truth JSON으로 변환"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📚 GPT Text → Ground Truth JSON 변환기")
        self.root.geometry("1200x800")
        
        self.image_files = []
        self.book_folder = None
        
        # 페이지 → 파일명 매핑표 (이 순간의 나)
        self.page_to_file_mapping = {
            "title_page": "sample_01_IMG_4975.JPG",
            "cover": "sample_02_IMG_4976.JPG", 
            33: "sample_03_IMG_5006.JPG",
            "blur_page": "sample_04_IMG_5007.JPG",
            35: "sample_05_IMG_5008.JPG",
            36: "sample_06_IMG_5009.JPG",
            37: "sample_07_IMG_5010.JPG", 
            38: "sample_08_IMG_5011.JPG",
            76: "sample_09_IMG_5051.JPG",
            77: "sample_10_IMG_5052.JPG"
        }
        
        self.setup_ui()
    
    def setup_ui(self):
        """UI 구성"""
        # 상단 프레임 - 폴더 선택
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="1. 📁 Book 폴더 선택:", font=("", 12, "bold")).pack(anchor=tk.W)
        
        folder_frame = ttk.Frame(top_frame)
        folder_frame.pack(fill=tk.X, pady=5)
        
        self.folder_label = ttk.Label(folder_frame, text="폴더를 선택하세요", foreground="gray")
        self.folder_label.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(folder_frame, text="📁 폴더 선택", command=self.select_folder).pack(side=tk.LEFT)
        ttk.Button(folder_frame, text="🔍 이미지 스캔", command=self.scan_images).pack(side=tk.LEFT, padx=(10, 0))
        
        # 이미지 파일 목록과 매핑표
        list_frame = ttk.Frame(folder_frame) 
        list_frame.pack(side=tk.LEFT, padx=(20, 0), fill=tk.BOTH, expand=True)
        
        ttk.Label(list_frame, text="📄 페이지→파일명 매핑표:", font=("", 9, "bold")).pack(anchor=tk.W)
        self.mapping_listbox = tk.Listbox(list_frame, height=6, width=60, font=("Courier New", 8))
        self.mapping_listbox.pack(fill=tk.BOTH, expand=True)
        
        # 매핑표 표시
        self.update_mapping_display()
        
        ttk.Label(list_frame, text="🖼️ 스캔된 이미지:", font=("", 9, "bold")).pack(anchor=tk.W, pady=(10, 0))
        self.image_listbox = tk.Listbox(list_frame, height=3, width=60, font=("Courier New", 8))
        self.image_listbox.pack(fill=tk.BOTH, expand=True)
        
        # 구분선
        ttk.Separator(self.root, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 중앙 프레임 - 텍스트 입력
        mid_frame = ttk.Frame(self.root, padding="10")
        mid_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(mid_frame, text="2. 📋 GPT 텍스트 붙여넣기:", font=("", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(mid_frame, text="GPT에서 추출한 텍스트를 아래에 붙여넣으세요 (페이지 번호와 텍스트 포함)", foreground="blue").pack(anchor=tk.W, pady=(0, 5))
        
        # 텍스트 입력 영역
        text_frame = ttk.Frame(mid_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text_input = scrolledtext.ScrolledText(
            text_frame, 
            wrap=tk.WORD, 
            font=("맑은 고딕", 10),
            height=15
        )
        self.text_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 미리보기 영역
        preview_frame = ttk.Frame(text_frame)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        ttk.Label(preview_frame, text="📄 JSON 미리보기:", font=("", 11, "bold")).pack(anchor=tk.W)
        
        self.json_preview = scrolledtext.ScrolledText(
            preview_frame,
            wrap=tk.WORD,
            font=("Courier New", 9),
            height=15
        )
        self.json_preview.pack(fill=tk.BOTH, expand=True)
        
        # 하단 프레임 - 버튼들
        bottom_frame = ttk.Frame(self.root, padding="10")
        bottom_frame.pack(fill=tk.X)
        
        button_frame = ttk.Frame(bottom_frame)
        button_frame.pack()
        
        ttk.Button(button_frame, text="🔄 텍스트 파싱", command=self.parse_gpt_text).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="👁️ JSON 미리보기", command=self.preview_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="💾 JSON 저장", command=self.save_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📋 클립보드 복사", command=self.copy_to_clipboard).pack(side=tk.LEFT, padx=5)
        
        # 상태 표시
        self.status_label = ttk.Label(bottom_frame, text="폴더를 선택하고 GPT 텍스트를 붙여넣으세요", foreground="blue")
        self.status_label.pack(pady=(10, 0))
        
        # 이벤트 바인딩
        self.text_input.bind('<KeyRelease>', self.on_text_change)
        
        # 샘플 텍스트 삽입
        self.insert_sample_text()
    
    def update_mapping_display(self):
        """매핑표 디스플레이 업데이트"""
        self.mapping_listbox.delete(0, tk.END)
        self.mapping_listbox.insert(tk.END, "📄 페이지 → 📁 파일명 매핑 (이 순간의 나)")
        self.mapping_listbox.insert(tk.END, "=" * 50)
        
        for page, filename in self.page_to_file_mapping.items():
            if isinstance(page, int):
                self.mapping_listbox.insert(tk.END, f"p.{page:2d} → {filename}")
            else:
                self.mapping_listbox.insert(tk.END, f"{page:12s} → {filename}")
    
    def select_folder(self):
        """Book 폴더 선택"""
        folder = filedialog.askdirectory(title="Book 폴더 선택")
        if folder:
            self.book_folder = Path(folder)
            self.folder_label.config(text=f"📁 {self.book_folder.name}", foreground="black")
            self.scan_images()
    
    def scan_images(self):
        """이미지 파일 스캔"""
        if not self.book_folder:
            messagebox.showwarning("경고", "먼저 폴더를 선택하세요")
            return
        
        # 이미지 파일 찾기
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        self.image_files = []
        
        for ext in image_extensions:
            self.image_files.extend(self.book_folder.glob(f"**/*{ext.lower()}"))
            self.image_files.extend(self.book_folder.glob(f"**/*{ext.upper()}"))
        
        self.image_files = sorted(list(set(self.image_files)))
        
        # 리스트박스 업데이트
        self.image_listbox.delete(0, tk.END)
        for img_file in self.image_files:
            self.image_listbox.insert(tk.END, img_file.name)
        
        self.status_label.config(text=f"✅ {len(self.image_files)}개 이미지 파일 발견", foreground="green")
    
    def insert_sample_text(self):
        """샘플 텍스트 삽입 - 실제 GPT 출력과 유사한 형태"""
        sample_text = """📘 이 순간의 나 – Ground Truth Text

📄 p.33
02
두려움에서 벗어나기

마음이 만들어낸 두려움

두려움을 느끼는 순간의 심리적 상황은 구체적이고, 실제적이며, 즉각적인 위험에 처했을 때와는 다릅니다. 두려움은 불안, 근심, 걱정, 신경과민, 긴장, 무서움, 공포 등 다양한 모습으로 나타납니다. 이런 종류의 심리적 두려움은

📄 p.35
받고 있어.' 이런 메시지를 지속적으로 받는다면 어떤 감정이 생길까요? 당연히 두려움입니다.

두려움의 원인에는 여러 가지가 있는 것처럼 보입니다. 상실에 대한 두려움, 실패에 대한 두려움, 상처받는 것에 대한 두려움 등등. 그러나 궁극적으로 모든 두려움은 에고가 느끼고 있는 죽음과 소멸에 대한 두려움입니다.

📄 p.36
그래서 에고는 자신이 틀렸음을 인정할 수 없습니다. 틀린다는 건 곧 죽음을 의미하기 때문입니다. 수없이 많은 관계가 깨지고, 전쟁이 벌어지는 이유가 여기에 있습니다.

📄 p.37
인간관계를 갉아먹는 모든 논쟁과 힘을 둘러싼 경쟁도 끝낼 수 있습니다. 다른 사람에게 행사하는 힘은 힘을 가장한 나약함일 뿐입니다. 진정한 힘은 내면에 있습니다. 그리고 지금 이 순간 당신은 그 힘을 사용할 수 있습니다."""
        
        self.text_input.insert('1.0', sample_text)
    
    def on_text_change(self, event=None):
        """텍스트 변경 시 자동 파싱"""
        self.preview_json()
    
    def parse_gpt_text(self):
        """GPT 텍스트 파싱"""
        try:
            text = self.text_input.get('1.0', tk.END).strip()
            if not text:
                self.status_label.config(text="❌ 텍스트를 입력하세요", foreground="red")
                return
            
            parsed_data = self._parse_text_to_pages(text)
            self.status_label.config(text=f"✅ {len(parsed_data)}개 페이지 파싱 완료", foreground="green")
            return parsed_data
            
        except Exception as e:
            self.status_label.config(text=f"❌ 파싱 오류: {str(e)}", foreground="red")
            return []
    
    def _parse_text_to_pages(self, text: str) -> List[Dict]:
        """텍스트를 페이지별로 파싱"""
        pages = []
        
        # 페이지 구분자로 분할
        page_pattern = r'📄\s*p\.(\d+)|📄\s*(\w+)'
        parts = re.split(page_pattern, text, flags=re.MULTILINE)
        
        if len(parts) < 4:
            # 간단한 방식: 숫자로 페이지 찾기
            page_pattern2 = r'(?:p\.|페이지\s*|page\s*)(\d+)'
            matches = list(re.finditer(page_pattern2, text, re.IGNORECASE))
            
            if matches:
                for i, match in enumerate(matches):
                    page_num = match.group(1)
                    start_pos = match.end()
                    
                    # 다음 페이지까지의 텍스트 추출
                    if i + 1 < len(matches):
                        end_pos = matches[i + 1].start()
                        page_text = text[start_pos:end_pos].strip()
                    else:
                        page_text = text[start_pos:].strip()
                    
                    if page_text:
                        # 자동 파일명 매칭
                        matched_file = self._match_image_file(page_num)
                        
                        pages.append({
                            "page_num": int(page_num),
                            "text": page_text,
                            "matched_file": matched_file,
                            "measure": True  # 기본값
                        })
            else:
                # 전체 텍스트를 하나의 페이지로 처리
                pages.append({
                    "page_num": 1,
                    "text": text.strip(),
                    "matched_file": self.image_files[0].name if self.image_files else "sample_01.jpg",
                    "measure": True
                })
        else:
            # 정규식 매칭 성공
            for i in range(1, len(parts), 3):
                if i + 2 < len(parts):
                    page_num = parts[i] or parts[i + 1]
                    page_text = parts[i + 2].strip()
                    
                    if page_text:
                        matched_file = self._match_image_file(page_num)
                        
                        pages.append({
                            "page_num": page_num,
                            "text": page_text,
                            "matched_file": matched_file,
                            "measure": True
                        })
        
        return pages
    
    def _match_image_file(self, page_identifier: str) -> str:
        """페이지 식별자로 이미지 파일 자동 매칭 (매핑표 우선)"""
        
        # 1순위: 매핑표 체크
        try:
            page_num = int(page_identifier)
            if page_num in self.page_to_file_mapping:
                return self.page_to_file_mapping[page_num]
        except ValueError:
            # 숫자가 아닌 경우 (title_page, cover 등)
            if page_identifier in self.page_to_file_mapping:
                return self.page_to_file_mapping[page_identifier]
        
        # 2순위: 기존 자동 매칭 (스캔된 이미지 파일 기준)
        if not self.image_files:
            return f"sample_{page_identifier}.jpg"
        
        # 이미지 파일명에서 페이지 번호 찾기
        for img_file in self.image_files:
            filename = img_file.name.lower()
            
            # 파일명에 페이지 번호가 포함된 경우
            if str(page_identifier) in filename:
                return img_file.name
            
            # IMG_ 패턴에서 번호 추출
            img_match = re.search(r'img[_\s]*(\d+)', filename, re.IGNORECASE)
            if img_match and img_match.group(1) == str(page_identifier):
                return img_file.name
        
        # 3순위: 매칭 실패 시 기본 이름 생성
        if self.image_files:
            return self.image_files[0].name  # 첫 번째 파일 사용
        else:
            return f"sample_{page_identifier}.jpg"
    
    def preview_json(self):
        """JSON 미리보기"""
        try:
            parsed_data = self.parse_gpt_text()
            if not parsed_data:
                return
            
            # JSON 구조 생성
            json_structure = {
                "book_title": self.book_folder.name if self.book_folder else "Unknown Book",
                "ground_truth_version": "v2.0_gpt_generated",
                "pages": []
            }
            
            for i, page_data in enumerate(parsed_data, 1):
                page_entry = {
                    "image_file": page_data["matched_file"],
                    "page": page_data["page_num"],
                    "measure": page_data["measure"],
                    "notes": f"GPT 추출 - p.{page_data['page_num']}",
                    "text": page_data["text"][:200] + "..." if len(page_data["text"]) > 200 else page_data["text"]  # 미리보기용 축약
                }
                json_structure["pages"].append(page_entry)
            
            # JSON 미리보기 표시
            json_str = json.dumps(json_structure, ensure_ascii=False, indent=2)
            self.json_preview.delete('1.0', tk.END)
            self.json_preview.insert('1.0', json_str)
            
        except Exception as e:
            self.json_preview.delete('1.0', tk.END)
            self.json_preview.insert('1.0', f"미리보기 오류: {str(e)}")
    
    def save_json(self):
        """JSON 파일 저장"""
        try:
            parsed_data = self.parse_gpt_text()
            if not parsed_data:
                return
            
            # 전체 텍스트로 JSON 생성 (축약 없이)
            json_structure = {
                "book_title": self.book_folder.name if self.book_folder else "Unknown Book",
                "ground_truth_version": "v2.0_gpt_generated",
                "pages": []
            }
            
            for page_data in parsed_data:
                page_entry = {
                    "image_file": page_data["matched_file"],
                    "page": page_data["page_num"],
                    "measure": page_data["measure"],
                    "notes": f"GPT 추출 - p.{page_data['page_num']}",
                    "text": page_data["text"]  # 전체 텍스트
                }
                json_structure["pages"].append(page_entry)
            
            # 파일 저장
            save_path = filedialog.asksaveasfilename(
                title="Ground Truth JSON 저장",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile="ground_truth_map.json"
            )
            
            if save_path:
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(json_structure, f, ensure_ascii=False, indent=2)
                
                self.status_label.config(text=f"✅ JSON 저장 완료: {Path(save_path).name}", foreground="green")
                messagebox.showinfo("완료", f"Ground Truth JSON이 저장되었습니다!\n\n{save_path}")
            
        except Exception as e:
            self.status_label.config(text=f"❌ 저장 오류: {str(e)}", foreground="red")
            messagebox.showerror("오류", f"저장 중 오류가 발생했습니다:\n{str(e)}")
    
    def copy_to_clipboard(self):
        """JSON을 클립보드에 복사"""
        try:
            json_content = self.json_preview.get('1.0', tk.END).strip()
            if json_content and json_content != "미리보기가 없습니다":
                self.root.clipboard_clear()
                self.root.clipboard_append(json_content)
                self.status_label.config(text="✅ JSON이 클립보드에 복사되었습니다", foreground="green")
            else:
                self.status_label.config(text="❌ 복사할 JSON이 없습니다", foreground="red")
        except Exception as e:
            self.status_label.config(text=f"❌ 복사 오류: {str(e)}", foreground="red")
    
    def run(self):
        """앱 실행"""
        self.root.mainloop()

def main():
    """메인 함수"""
    print("🚀 GPT Text → Ground Truth JSON 변환기 시작")
    app = GPTTextToJSONConverter()
    app.run()

if __name__ == "__main__":
    main()