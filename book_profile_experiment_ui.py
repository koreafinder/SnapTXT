#!/usr/bin/env python3
"""
📚 SnapTXT 실험 루프 UI - 현실적 MVP
Phase 2.8: 측정으로 증명하는 Book Profile 실험 시스템

5단계 실험 루프:
1. 📁 Book Folder Scanner
2. 🎯 Sample Generator  
3. 📦 GPT Pack Builder
4. 🧠 Profile Builder
5. 📊 Apply Test (CER 분해 측정)
"""

import sys
import json
import shutil
import random
import traceback
import requests
import base64
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import cv2
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QTextEdit, QProgressBar,
    QFileDialog, QMessageBox, QGroupBox, QGridLayout, QSpinBox,
    QScrollArea, QFrame, QSplitter, QCheckBox, QDialog, QButtonGroup, QRadioButton
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QTextCursor

# SnapTXT 시스템 통합 어댑터 임포트
try:
    from snaptxt_integration_adapters import SnapTXTSystemManager
    INTEGRATION_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ SnapTXT 통합 어댑터 임포트 실패: {e}")
    print("기본 기능으로 진행합니다.")
    INTEGRATION_AVAILABLE = False


class BasicLogger:
    """기본 로깅 시스템 - 복잡한 기능 제외"""
    
    def __init__(self):
        self.logs = []
        
    def info(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        print(log_entry)
        
    def error(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] ❌ {message}"
        self.logs.append(log_entry)
        print(log_entry)
        
    def get_recent_logs(self, count: int = 10) -> str:
        return "\n".join(self.logs[-count:])


class BasicSampleGenerator:
    """기본 샘플 생성기 - Phase 2 분산 전략 + 간단 품질 체크"""
    
    def __init__(self, logger: BasicLogger):
        self.logger = logger
        
    def generate_samples(self, image_files: List[Path], target_count: int = 10) -> List[Path]:
        """Phase 2 기준 분산 샘플링"""
        self.logger.info(f"🎯 샘플 생성 시작 (목표: {target_count}장)")
        
        total = len(image_files)
        if total < target_count:
            self.logger.error(f"이미지 부족: {total}장 < {target_count}장")
            return image_files
            
        # Phase 2 분산 전략: 초반2 + 중반6 + 후반2
        early_start, early_end = int(total * 0.05), int(total * 0.15)
        mid_start, mid_end = int(total * 0.35), int(total * 0.70)
        late_start, late_end = int(total * 0.80), int(total * 0.95)
        
        candidates = []
        distributions = [
            (early_start, early_end, 2, "초반"),
            (mid_start, mid_end, 6, "중반"),
            (late_start, late_end, 2, "후반")
        ]
        
        for start, end, count, label in distributions:
            range_files = image_files[start:end]
            selected = self._basic_quality_filter(range_files, count)
            candidates.extend(selected)
            self.logger.info(f"✅ {label} 구간: {len(selected)}/{count}장 선정")
            
        self.logger.info(f"✅ 분산 샘플링 완료: {len(candidates)}장")
        return candidates[:target_count]
    
    def _basic_quality_filter(self, files: List[Path], target_count: int) -> List[Path]:
        """기본 블러 체크만 - 복잡한 분석 제외"""
        valid_files = []
        
        for file_path in files:
            try:
                img = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    # 간단한 블러 체크
                    laplacian_var = cv2.Laplacian(img, cv2.CV_64F).var()
                    if laplacian_var > 100:  # 기본 임계값
                        valid_files.append(file_path)
                        
            except Exception as e:
                self.logger.error(f"품질 체크 실패: {file_path.name} - {str(e)}")
                continue
                
        # 충분하지 않으면 전체 사용
        if len(valid_files) < target_count:
            valid_files = list(files)
            
        return valid_files[:target_count]
    
    def copy_samples_to_directory(self, candidates: List[Path], samples_dir: Path) -> List[Path]:
        """샘플 파일을 samples/ 디렉토리에 복사"""
        self.logger.info(f"📁 샘플 복사 시작: {samples_dir}")
        samples_dir.mkdir(parents=True, exist_ok=True)
        copied_samples = []
        
        # 기존 파일들 정리
        for existing_file in samples_dir.glob("sample_*.jpg"):
            existing_file.unlink()
        for existing_file in samples_dir.glob("sample_*.JPG"):
            existing_file.unlink()
            
        for i, source in enumerate(candidates, 1):
            target_name = f"sample_{i:02d}_{source.name}"
            target_path = samples_dir / target_name
            
            try:
                if not source.exists():
                    self.logger.error(f"❌ 원본 파일 없음: {source}")
                    continue
                    
                shutil.copy2(source, target_path)
                if target_path.exists():
                    copied_samples.append(target_path)
                    self.logger.info(f"✅ 복사완료: {target_name} (크기: {target_path.stat().st_size:,} bytes)")
                else:
                    self.logger.error(f"❌ 복사 실패: {target_name}")
            except Exception as e:
                self.logger.error(f"❌ 파일 복사 에러: {source.name} -> {str(e)}")
                
        self.logger.info(f"📁 총 {len(copied_samples)}개 파일 복사 완료")
        return copied_samples


class SampleGeneratorWorker(QThread):
    """샘플 생성 Worker Thread - UI 프리징 방지"""
    progress = Signal(int, str)  # percent, message
    finished = Signal(list)  # copied samples
    error = Signal(str)
    
    def __init__(self, image_files: List[Path], target_count: int, samples_dir: Path, logger: BasicLogger):
        super().__init__()
        self.image_files = image_files
        self.target_count = target_count
        self.samples_dir = samples_dir
        self.logger = logger
        
    def run(self):
        """샘플 생성 실행"""
        try:
            self.progress.emit(10, "분산 계산 중...")
            
            generator = BasicSampleGenerator(self.logger)
            candidates = generator.generate_samples(self.image_files, self.target_count)
            
            self.progress.emit(50, f"선정 완료: {len(candidates)}장")
            
            copied_samples = generator.copy_samples_to_directory(candidates, self.samples_dir)
            
            self.progress.emit(100, f"샘플 생성 완료: {len(copied_samples)}장")
            self.finished.emit(copied_samples)
            
        except Exception as e:
            self.error.emit(f"샘플 생성 실패: {str(e)}")


class SimpleGoogleVisionOCR:
    """Google Vision REST API를 직접 호출하는 간단한 OCR 클라이언트"""
    
    def __init__(self, api_key: Optional[str] = None, logger: BasicLogger = None):
        """
        초기화
        
        Args:
            api_key: Google Vision API 키
            logger: 로깅 시스템
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        self.base_url = "https://vision.googleapis.com/v1/images:annotate"
        self.logger = logger or BasicLogger()
        
        if not self.api_key:
            self.logger.error("API 키가 설정되지 않았습니다!")
    
    def encode_image(self, image_path: Path) -> str:
        """이미지를 base64로 인코딩"""
        try:
            with open(image_path, 'rb') as image_file:
                image_content = image_file.read()
                encoded_image = base64.b64encode(image_content).decode('utf-8')
                return encoded_image
        except Exception as e:
            self.logger.error(f"이미지 인코딩 실패: {str(e)}")
            return ""
    
    def extract_text_from_image(self, image_path: Path) -> Dict:
        """
        이미지에서 텍스트 추출
        
        Args:
            image_path: 이미지 파일 경로
            
        Returns:
            추출 결과 딕셔너리
        """
        if not self.api_key:
            return {"error": "API 키가 설정되지 않았습니다"}
        
        if not image_path.exists():
            return {"error": f"이미지 파일을 찾을 수 없습니다: {image_path}"}
        
        try:
            self.logger.info(f"📖 Google Vision OCR 처리: {image_path.name}")
            
            # 이미지 인코딩
            encoded_image = self.encode_image(image_path)
            if not encoded_image:
                return {"error": "이미지 인코딩 실패"}
            
            # REST API 요청 데이터
            request_data = {
                "requests": [
                    {
                        "image": {
                            "content": encoded_image
                        },
                        "features": [
                            {
                                "type": "DOCUMENT_TEXT_DETECTION",
                                "maxResults": 1
                            }
                        ]
                    }
                ]
            }
            
            # API 호출
            headers = {'Content-Type': 'application/json'}
            url = f"{self.base_url}?key={self.api_key}"
            
            response = requests.post(url, headers=headers, json=request_data, timeout=30)
            
            if response.status_code != 200:
                return {
                    "error": f"API 호출 실패: {response.status_code} - {response.text[:200]}"
                }
            
            # 응답 파싱
            result_data = response.json()
            
            if "error" in result_data:
                return {"error": f"Vision API 오류: {result_data['error']}"}
            
            responses = result_data.get("responses", [])
            if not responses:
                return {"error": "API 응답이 비어있습니다"}
            
            first_response = responses[0]
            
            # 오류 체크
            if "error" in first_response:
                return {"error": f"OCR 처리 오류: {first_response['error']}"}
            
            # 텍스트 추출
            extracted_text = ""
            if "fullTextAnnotation" in first_response:
                extracted_text = first_response["fullTextAnnotation"].get("text", "")
            elif "textAnnotations" in first_response:
                # fallback으로 textAnnotations 사용
                text_annotations = first_response["textAnnotations"]
                if text_annotations:
                    extracted_text = text_annotations[0].get("description", "")
            
            result = {
                "success": True,
                "text": extracted_text.strip(),
                "text_length": len(extracted_text.strip()),
                "image_file": image_path.name,
                "api_version": "Google Vision REST API"
            }
            
            self.logger.info(f"✅ Vision OCR 완료: {len(extracted_text.strip())} 글자 추출")
            return result
            
        except requests.exceptions.Timeout:
            return {"error": "API 호출 시간 초과"}
        except requests.exceptions.ConnectionError:
            return {"error": "인터넷 연결 오류"}
        except Exception as e:
            error_msg = f"Vision OCR 처리 실패: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def batch_ocr(self, image_paths: List[Path]) -> Dict[str, str]:
        """
        여러 이미지 일괄 OCR 처리
        
        Args:
            image_paths: 이미지 파일 경로 리스트
            
        Returns:
            파일별 OCR 결과 딕셔너리
        """
        results = {}
        
        self.logger.info(f"🔄 Google Vision 일괄 OCR 시작: {len(image_paths)}장")
        
        for i, image_path in enumerate(image_paths, 1):
            self.logger.info(f"📄 {i}/{len(image_paths)}: {image_path.name}")
            result = self.extract_text_from_image(image_path)
            
            if result.get("success"):
                results[image_path.name] = result["text"]
            else:
                self.logger.error(f"OCR 실패: {result.get('error', 'Unknown error')}")
                results[image_path.name] = f"[OCR 실패: {result.get('error', 'Unknown error')}]"
        
        successful = sum(1 for text in results.values() if not text.startswith("[OCR 실패"))
        self.logger.info(f"🎉 Google Vision OCR 완료: {successful}/{len(image_paths)}장 성공")
        
        return results


class VisionOCRWorker(QThread):
    """Google Vision OCR 배치 작업 Worker Thread"""
    progress = Signal(int, str)  # percent, message
    finished = Signal(dict)  # {sample_name: ocr_text}
    error = Signal(str)
    
    def __init__(self, samples: List[Path], api_key: str, logger: BasicLogger):
        super().__init__()
        self.samples = samples
        self.api_key = api_key
        self.logger = logger
        
    def run(self):
        """Vision OCR 배치 실행"""
        try:
            self.progress.emit(10, "Google Vision API 준비 중...")
            
            # Vision OCR 클라이언트 생성
            vision_ocr = SimpleGoogleVisionOCR(self.api_key, self.logger)
            
            if not vision_ocr.api_key:
                self.error.emit("Google Vision API 키가 설정되지 않았습니다")
                return
            
            self.progress.emit(20, f"OCR 처리 시작: {len(self.samples)}장")
            
            # 배치 OCR 실행
            ocr_results = {}
            for i, sample_path in enumerate(self.samples, 1):
                progress_percent = 20 + (i * 70) // len(self.samples)
                self.progress.emit(progress_percent, f"처리 중: {sample_path.name}")
                
                result = vision_ocr.extract_text_from_image(sample_path)
                
                if result.get("success"):
                    ocr_results[sample_path.name] = result["text"]
                else:
                    error_msg = result.get("error", "Unknown error")
                    self.logger.error(f"Vision OCR 실패: {sample_path.name} - {error_msg}")
                    ocr_results[sample_path.name] = f"[Vision OCR 실패: {error_msg}]"
            
            self.progress.emit(100, f"Google Vision OCR 완료: {len(ocr_results)}장")
            self.finished.emit(ocr_results)
            
        except Exception as e:
            error_msg = f"Google Vision OCR 배치 실패: {str(e)}"
            self.logger.error(error_msg)
            self.error.emit(error_msg)


class OCRWorker(QThread):
    """OCR 배치 작업 Worker Thread - SnapTXT 시스템 연동"""
    progress = Signal(int, str)  # percent, message
    finished = Signal(dict)  # {sample_name: ocr_text}
    error = Signal(str)
    
    def __init__(self, samples: List[Path], system_manager: 'SnapTXTSystemManager', logger: BasicLogger):
        super().__init__()
        self.samples = samples
        self.system_manager = system_manager
        self.logger = logger
        
    def run(self):
        """OCR 배치 실행 - SnapTXT 통합 시스템 사용"""
        try:
            results = {}
            total = len(self.samples)
            
            for i, sample_path in enumerate(self.samples):
                progress_percent = int((i + 1) / total * 100)
                self.progress.emit(progress_percent, f"OCR 처리 중: {i+1}/{total}")
                
                # SnapTXT OCR 어댑터 사용
                ocr_result = self.system_manager.ocr_adapter.process_image(sample_path)
                ocr_text = ocr_result.get('text', '')
                
                results[sample_path.name] = ocr_text
                self.logger.info(f"✅ {sample_path.name} OCR: {len(ocr_text)}자 추출 "
                               f"(신뢰도: {ocr_result.get('confidence', 0):.2f})")
                
            self.finished.emit(results)
            
        except Exception as e:
            self.error.emit(f"OCR 배치 실패: {str(e)}")


class ApplyTestWorker(QThread):
    """Apply Test Worker Thread - SnapTXT CER 분해 측정 연동"""
    progress = Signal(int, str)  # percent, message  
    finished = Signal(dict)  # test results
    error = Signal(str)
    
    def __init__(self, test_samples: List[Path], profile_path: Path, 
                 system_manager: 'SnapTXTSystemManager', logger: BasicLogger):
        super().__init__()
        self.test_samples = test_samples
        self.profile_path = profile_path
        self.system_manager = system_manager
        self.logger = logger
        
    def run(self):
        """Apply Test 실행 - SnapTXT 통합 시스템 사용"""
        try:
            total_steps = len(self.test_samples) * 2  # Before + After
            current_step = 0
            
            before_results = {}
            after_results = {}
            
            # Before OCR (기본 파이프라인)
            self.progress.emit(10, "Before OCR 시작...")
            for sample_path in self.test_samples:
                current_step += 1
                progress = int(current_step / total_steps * 50)
                self.progress.emit(progress, f"Before OCR: {sample_path.name}")
                
                # SnapTXT OCR 어댑터 사용
                result = self.system_manager.ocr_adapter.process_image(sample_path)
                before_results[sample_path.name] = result.get('text', '')
            
            # After OCR (Book Profile 적용)
            self.progress.emit(60, "After OCR 시작 (Profile 적용)...")
            
            # Profile 로드
            profile_data = self._load_profile(self.profile_path)
            
            for sample_path in self.test_samples:
                current_step += 1
                progress = int(50 + current_step / total_steps * 40)
                self.progress.emit(progress, f"After OCR: {sample_path.name}")
                
                # Base OCR 결과에 Profile 적용
                base_text = before_results.get(sample_path.name, '')
                improved_text = self.system_manager.layout_adapter.apply_profile_to_text(
                    base_text, profile_data
                )
                after_results[sample_path.name] = improved_text
            
            # CER 분해 계산 - SnapTXT Phase 2.6 시스템 사용
            self.progress.emit(90, "CER 분해 계산 중...")
            cer_results = self.system_manager.cer_adapter.analyze_cer_breakdown(
                before_results, after_results
            )
            
            # 결과 구성
            test_results = {
                'before_texts': before_results,
                'after_texts': after_results,
                'cer_analysis': cer_results,
                'test_samples': [p.name for p in self.test_samples],
                'profile_applied': profile_data,
                'timestamp': datetime.now().isoformat()
            }
            
            self.progress.emit(100, "Apply Test 완료!")
            self.finished.emit(test_results)
            
        except Exception as e:
            self.error.emit(f"Apply Test 실패: {str(e)}")
    
    def _load_profile(self, profile_path: Path) -> Dict:
        """Profile 파일 로드"""
        try:
            import yaml
            with open(profile_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Profile 로드 실패: {str(e)}")
            # 기본 프로필 반환
            return {
                'type': 'layout_specific',
                'rules': [
                    {'pattern': r'\s+을\s+', 'replacement': '을 ', 'rule_id': 'particle_merge'}
                ]
            }


class BookExperimentUI(QMainWindow):
    """SnapTXT 실험 루프 메인 UI"""
    
    def __init__(self):
        super().__init__()
        self.logger = BasicLogger()
        
        # SnapTXT 시스템 매니저 초기화
        if INTEGRATION_AVAILABLE:
            self.system_manager = SnapTXTSystemManager(self.logger)
            self.logger.info("🚀 SnapTXT 통합 시스템 연동 완료")
        else:
            self.system_manager = None
            self.logger.info("🔧 기본 모드로 실행 (시뮬레이션)")
        
        # UI 상태 변수들
        self.book_folder = None
        self.image_files = []
        self.snaptxt_dir = None
        self.generated_samples = []
        self.ocr_results = {}
        self.test_results = {}
        
        self.init_ui()
        self.logger.info("🚀 SnapTXT 실험 루프 UI 시작")
        
        # 시스템 상태 체크 및 표시
        if self.system_manager:
            status = self.system_manager.get_system_status()
            self.logger.info(f"📊 시스템 상태: {status}")
        
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("SnapTXT 실험 루프 UI - Phase 2.8 MVP")
        self.setGeometry(100, 100, 1400, 900)
        
        # 메인 위젯
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # 제목
        title = QLabel("📚 SnapTXT 실험 루프 - 측정으로 증명하는 Book Profile 시스템")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 분할 위젯 (탭 + 로그)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 탭 위젯
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)
        
        # 5개 화면 초기화
        self.init_folder_scanner_tab()     # 화면 A
        self.init_sample_generator_tab()   # 화면 B 
        self.init_gpt_pack_builder_tab()   # 화면 C
        self.init_profile_builder_tab()    # 화면 D
        self.init_apply_test_tab()         # 화면 E ★
        
        # 로그 영역
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        
        log_label = QLabel("📋 실시간 로그")
        log_label.setFont(QFont("Arial", 12, QFont.Bold))
        log_layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumWidth(400)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        splitter.addWidget(log_widget)
        splitter.setSizes([1000, 400])
        
        # 로그 업데이트 타이머
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.update_log_display)
        self.log_timer.start(1000)  # 1초마다 업데이트
        
    def init_folder_scanner_tab(self):
        """화면 A: Book Folder Scanner"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 폴더 선택 그룹
        folder_group = QGroupBox("📁 Book Folder Scanner")
        folder_layout = QVBoxLayout(folder_group)
        
        self.select_folder_btn = QPushButton("📁 폴더 선택")
        self.select_folder_btn.setFont(QFont("Arial", 14, QFont.Bold))
        self.select_folder_btn.setMinimumHeight(60)
        self.select_folder_btn.clicked.connect(self.select_book_folder)
        folder_layout.addWidget(self.select_folder_btn)
        
        self.folder_label = QLabel("선택된 폴더 없음")
        folder_layout.addWidget(self.folder_label)
        
        # 스캔 결과
        self.scan_result_text = QTextEdit()
        self.scan_result_text.setMaximumHeight(300)
        folder_layout.addWidget(self.scan_result_text)
        
        layout.addWidget(folder_group)
        
        # 다음 단계
        next_btn = QPushButton("➡️ 다음: 샘플 생성")
        next_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        layout.addWidget(next_btn)
        
        self.tabs.addTab(tab, "1️⃣ Book Folder")
    
    def init_sample_generator_tab(self):
        """화면 B: Sample Generator + Ground Truth 입력"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 설정 그룹
        settings_group = QGroupBox("🎯 Sample Generator (Phase 2 분산)")
        settings_layout = QGridLayout(settings_group)
        
        settings_layout.addWidget(QLabel("샘플 개수:"), 0, 0)
        self.sample_count_spin = QSpinBox()
        self.sample_count_spin.setRange(7, 15)
        self.sample_count_spin.setValue(10)
        settings_layout.addWidget(self.sample_count_spin, 0, 1)
        
        settings_layout.addWidget(QLabel("분산 전략:"), 1, 0)
        strategy_label = QLabel("초반 2장 + 중반 6장 + 후반 2장")
        settings_layout.addWidget(strategy_label, 1, 1)
        
        layout.addWidget(settings_group)
        
        # 생성 그룹
        gen_group = QGroupBox("📊 샘플 생성")
        gen_layout = QVBoxLayout(gen_group)
        
        self.generate_samples_btn = QPushButton("🎯 Generate Samples")
        self.generate_samples_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.generate_samples_btn.setMinimumHeight(50)
        self.generate_samples_btn.clicked.connect(self.generate_samples)
        self.generate_samples_btn.setEnabled(False)
        gen_layout.addWidget(self.generate_samples_btn)
        
        self.sample_progress = QProgressBar()
        gen_layout.addWidget(self.sample_progress)
        
        layout.addWidget(gen_group)
        
        # Ground Truth 입력 그룹
        gt_group = QGroupBox("📝 Ground Truth 텍스트 입력")
        gt_layout = QVBoxLayout(gt_group)
        
        # 스크롤 영역
        self.samples_scroll = QScrollArea()
        self.samples_scroll.setWidgetResizable(True)
        self.samples_scroll.setVisible(False)  # 처음에는 숨김
        
        self.samples_widget = QWidget()
        self.samples_layout = QVBoxLayout(self.samples_widget)
        self.samples_scroll.setWidget(self.samples_widget)
        
        gt_layout.addWidget(self.samples_scroll)
        
        # Ground Truth JSON 생성 버튼들
        gt_buttons_layout = QHBoxLayout()
        
        self.generate_gt_json_btn = QPushButton("💾 Ground Truth JSON 생성")
        self.generate_gt_json_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.generate_gt_json_btn.clicked.connect(self.generate_ground_truth_json)
        self.generate_gt_json_btn.setEnabled(False)
        gt_buttons_layout.addWidget(self.generate_gt_json_btn)
        
        self.preview_gt_btn = QPushButton("👁️ JSON 미리보기")
        self.preview_gt_btn.clicked.connect(self.preview_ground_truth_json)
        self.preview_gt_btn.setEnabled(False)
        gt_buttons_layout.addWidget(self.preview_gt_btn)
        
        gt_layout.addLayout(gt_buttons_layout)
        
        layout.addWidget(gt_group)
        
        # 다음 단계
        next_btn = QPushButton("➡️ 다음: GPT Pack 빌드")
        next_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        layout.addWidget(next_btn)
        
        # 샘플별 텍스트 입력창 저장용
        self.sample_text_inputs = {}
        
        self.tabs.addTab(tab, "2️⃣ Sample Generator + GT")
    
    def init_gpt_pack_builder_tab(self):
        """화면 C: GPT Pack Builder"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # OCR 방법 선택 그룹
        ocr_method_group = QGroupBox("🔧 OCR 방법 선택")
        ocr_method_layout = QVBoxLayout(ocr_method_group)
        
        # 라디오 버튼 그룹
        self.ocr_method_group = QButtonGroup()
        
        # SnapTXT OCR 옵션
        self.snaptxt_ocr_radio = QRadioButton("📱 SnapTXT OCR (기존 방식)")
        self.snaptxt_ocr_radio.setChecked(True)
        self.ocr_method_group.addButton(self.snaptxt_ocr_radio, 0)
        ocr_method_layout.addWidget(self.snaptxt_ocr_radio)
        
        # Google Vision OCR 옵션
        self.vision_ocr_radio = QRadioButton("🚀 Google Vision API (자동화)")
        self.ocr_method_group.addButton(self.vision_ocr_radio, 1)
        ocr_method_layout.addWidget(self.vision_ocr_radio)
        
        # Vision API 장점 표시
        vision_info = QLabel("   ✅ 20배 빠른 속도 | ✅ 높은 정확도 | ✅ 완전 자동화")
        vision_info.setStyleSheet("color: #2196F3; font-size: 11px; margin-left: 20px;")
        ocr_method_layout.addWidget(vision_info)
        
        layout.addWidget(ocr_method_group)
        
        # GPT Pack 빌드 그룹
        builder_group = QGroupBox("📦 GPT Pack Builder")
        builder_layout = QVBoxLayout(builder_group)
        
        self.build_gpt_pack_btn = QPushButton("📦 Build GPT Pack")
        self.build_gpt_pack_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.build_gpt_pack_btn.setMinimumHeight(50)
        self.build_gpt_pack_btn.clicked.connect(self.build_gpt_pack)
        self.build_gpt_pack_btn.setEnabled(False)
        builder_layout.addWidget(self.build_gpt_pack_btn)
        
        self.ocr_progress = QProgressBar()
        builder_layout.addWidget(self.ocr_progress)
        
        self.gpt_result_text = QTextEdit()
        self.gpt_result_text.setMaximumHeight(200)
        builder_layout.addWidget(self.gpt_result_text)
        
        layout.addWidget(builder_group)
        
        # GPT 업로드 가이드
        guide_group = QGroupBox("📋 GPT 업로드 가이드")
        guide_layout = QVBoxLayout(guide_group)
        
        guide_text = QTextEdit()
        guide_text.setPlainText(
            "1. ChatGPT에 두 파일 업로드:\n"
            "   - gpt_input_ocr.txt (OCR 결과)\n"
            "   - gpt_prompt.txt (Phase 2.7 프롬프트)\n\n"
            "2. 추가 메시지: '분석해주세요'\n\n"
            "3. 결과를 다음 화면에 붙여넣기"
        )
        guide_text.setMaximumHeight(150)
        guide_layout.addWidget(guide_text)
        
        layout.addWidget(guide_group)
        
        # 다음 단계
        next_btn = QPushButton("➡️ 다음: Profile 생성")
        next_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        layout.addWidget(next_btn)
        
        self.tabs.addTab(tab, "3️⃣ GPT Pack Builder")
    
    def init_profile_builder_tab(self):
        """화면 D: Profile Builder"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # GPT 결과 입력
        input_group = QGroupBox("📝 GPT 결과 입력")
        input_layout = QVBoxLayout(input_group)
        
        self.gpt_result_input = QTextEdit()
        self.gpt_result_input.setPlaceholderText("ChatGPT 결과를 여기에 붙여넣으세요...")
        self.gpt_result_input.setMaximumHeight(300)
        input_layout.addWidget(self.gpt_result_input)
        
        layout.addWidget(input_group)
        
        # Profile 생성
        profile_group = QGroupBox("🧠 Profile Builder")
        profile_layout = QVBoxLayout(profile_group)
        
        self.build_profile_btn = QPushButton("🧠 Build Profile")
        self.build_profile_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.build_profile_btn.setMinimumHeight(50)
        self.build_profile_btn.clicked.connect(self.build_profile)
        profile_layout.addWidget(self.build_profile_btn)
        
        self.profile_result_text = QTextEdit()
        self.profile_result_text.setMaximumHeight(150)
        profile_layout.addWidget(self.profile_result_text)
        
        layout.addWidget(profile_group)
        
        # 다음 단계
        next_btn = QPushButton("➡️ 다음: Apply Test")
        next_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(4))
        layout.addWidget(next_btn)
        
        self.tabs.addTab(tab, "4️⃣ Profile Builder")
    
    def init_apply_test_tab(self):
        """화면 E: Apply Test (CER 분해 측정) ★ 가장 중요!"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Ground Truth 상태 표시
        gt_group = QGroupBox("📊 Ground Truth 상태")
        gt_layout = QVBoxLayout(gt_group)
        
        self.gt_status_label = QLabel("시스템 상태 확인 중...")
        gt_layout.addWidget(self.gt_status_label)
        
        layout.addWidget(gt_group)
        
        # Apply Test 그룹
        test_group = QGroupBox("📊 Apply Test - CER 분해 측정 (Phase 2.6 스타일)")
        test_layout = QVBoxLayout(test_group)
        
        self.apply_test_btn = QPushButton("📊 Apply Test (Random 5 pages)")
        self.apply_test_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.apply_test_btn.setMinimumHeight(50)
        self.apply_test_btn.clicked.connect(self.apply_test)
        self.apply_test_btn.setEnabled(False)
        test_layout.addWidget(self.apply_test_btn)
        
        self.test_progress = QProgressBar()
        test_layout.addWidget(self.test_progress)
        
        layout.addWidget(test_group)
        
        # 측정 결과 (가장 중요!)
        result_group = QGroupBox("🎯 CER 분해 결과 - SnapTXT 핵심 차별점")
        result_layout = QVBoxLayout(result_group)
        
        self.test_result_text = QTextEdit()
        self.test_result_text.setFont(QFont("Consolas", 10))
        self.test_result_text.setMinimumHeight(400)
        result_layout.addWidget(self.test_result_text)
        
        layout.addWidget(result_group)
        
        # 재측정 버튼
        retest_btn = QPushButton("🔄 재측정 (다른 5장)")
        retest_btn.clicked.connect(self.apply_test)
        layout.addWidget(retest_btn)
        
        self.tabs.addTab(tab, "5️⃣ Apply Test ★")
        
        # Ground Truth 상태 업데이트
        self.update_ground_truth_status()
    
    def update_ground_truth_status(self):
        """Ground Truth 상태 업데이트"""
        if not self.system_manager:
            self.gt_status_label.setText("🔧 시뮬레이션 모드")
            return
        
        status = self.system_manager.cer_adapter.get_ground_truth_status()
        
        if status['available']:
            status_text = f"✅ Ground Truth 로드 완료\n"
            status_text += f"📚 책: {status['book']}\n"
            status_text += f"📊 테스트 가능: {status['test_eligible']}/{status['total_samples']}장\n"
            status_text += f"🎯 측정 모드: 정확한 CER 계산"
        else:
            status_text = f"⚠️ Ground Truth 사용 불가\n"
            status_text += f"🔧 측정 모드: 시뮬레이션"
            
        self.gt_status_label.setText(status_text)
    
    def update_log_display(self):
        """로그 디스플레이 업데이트"""
        recent_logs = self.logger.get_recent_logs(20)
        self.log_text.setPlainText(recent_logs)
        # 자동 스크롤
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
    
    def select_book_folder(self):
        """폴더 선택 및 자동 스캔"""
        folder = QFileDialog.getExistingDirectory(self, "Book 폴더 선택")
        if not folder:
            return
            
        self.book_folder = Path(folder)
        self.logger.info(f"📁 폴더 선택: {self.book_folder.name}")
        
        # .snaptxt 디렉토리 생성
        self.snaptxt_dir = self.book_folder / ".snaptxt"
        self.snaptxt_dir.mkdir(exist_ok=True)
        
        for subdir in ["samples", "gpt", "profiles", "logs"]:
            (self.snaptxt_dir / subdir).mkdir(exist_ok=True)
        
        # 이미지 파일 스캔
        self.scan_images()
        
        # UI 업데이트
        self.folder_label.setText(f"📁 {self.book_folder.name}")
        self.generate_samples_btn.setEnabled(True)
    
    def scan_images(self):
        """이미지 스캔 + Phase 2 분산 미리보기"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        image_files = set()
        
        for ext in image_extensions:
            image_files.update(self.book_folder.glob(f"**/*{ext.lower()}"))
            image_files.update(self.book_folder.glob(f"**/*{ext.upper()}"))
        
        self.image_files = sorted(list(image_files))
        total = len(self.image_files)
        
        self.logger.info(f"🔍 이미지 스캔: {total}장 발견")
        
        # Phase 2 분산 미리보기
        info_text = f"📊 스캔 결과:\n"
        info_text += f"   총 이미지: {total}장\n"
        info_text += f"   폴더 경로: {self.book_folder}\n\n"
        
        if total >= 10:
            info_text += f"📄 Phase 2 분산 샘플 미리보기 (10장 기준):\n"
            
            # 분산 계산
            early_start, early_end = int(total * 0.05), int(total * 0.15)
            mid_start, mid_end = int(total * 0.35), int(total * 0.70)
            late_start, late_end = int(total * 0.80), int(total * 0.95)
            
            preview_indices = [
                (early_start, "초반 본문"), (early_start + (early_end - early_start)//2, "초반 본문"),
                (mid_start, "중반 핵심"), (mid_start + (mid_end - mid_start)//6, "중반 핵심"),
                (mid_start + 2*(mid_end - mid_start)//6, "중반 핵심"), (mid_start + 3*(mid_end - mid_start)//6, "중반 핵심"),
                (mid_start + 4*(mid_end - mid_start)//6, "중반 핵심"), (mid_start + 5*(mid_end - mid_start)//6, "중반 핵심"),
                (late_start, "후반 본문"), (late_end, "후반 본문")
            ]
            
            for i, (idx, label) in enumerate(preview_indices[:10], 1):
                if idx < len(self.image_files):
                    info_text += f"   {i:02d}. {label}: {self.image_files[idx].name}\n"
        
        self.scan_result_text.setPlainText(info_text)
        self.logger.info("🎯 분산 미리보기 완료")
    
    def generate_samples(self):
        """샘플 생성 (Worker Thread)"""
        if not self.image_files:
            QMessageBox.warning(self, "오류", "먼저 폴더를 선택하세요")
            return
        
        target_count = self.sample_count_spin.value()
        samples_dir = self.snaptxt_dir / "samples"
        
        self.logger.info(f"🎯 샘플 생성 시작: {target_count}장")
        
        # Worker 시작
        self.sample_worker = SampleGeneratorWorker(
            self.image_files, target_count, samples_dir, self.logger
        )
        self.sample_worker.progress.connect(self.sample_progress.setValue)
        self.sample_worker.finished.connect(self.on_samples_generated)
        self.sample_worker.error.connect(self.on_sample_error)
        self.sample_worker.start()
        
        self.generate_samples_btn.setEnabled(False)
    
    def on_samples_generated(self, samples: List[Path]):
        """샘플 생성 완료 + GT 입력 UI 생성"""
        self.generated_samples = samples
        self.logger.info(f"✅ 샘플 생성 완료: {len(samples)}장")
        
        # Ground Truth 입력 UI 생성
        self.create_sample_input_widgets(samples)
        
        # UI 활성화
        self.generate_samples_btn.setEnabled(True)
        self.generate_gt_json_btn.setEnabled(True)
        self.preview_gt_btn.setEnabled(True)
        self.build_gpt_pack_btn.setEnabled(True)
    
    def create_sample_input_widgets(self, samples: List[Path]):
        """각 샘플에 대한 입력 위젯 생성"""
        # 기존 위젯들 제거
        for i in reversed(range(self.samples_layout.count())):
            child = self.samples_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # 샘플별 텍스트 입력창 초기화
        self.sample_text_inputs.clear()
        
        for i, sample in enumerate(samples, 1):
            # 샘플 그룹 박스
            sample_group = QGroupBox(f"📄 Sample {i:02d}: {sample.name}")
            sample_layout = QHBoxLayout(sample_group)
            
            # 이미지 미리보기 (작은 크기)
            try:
                pixmap = QPixmap(str(sample))
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(150, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    img_label = QLabel()
                    img_label.setPixmap(scaled_pixmap)
                    img_label.setAlignment(Qt.AlignCenter)
                    sample_layout.addWidget(img_label)
            except Exception:
                # 이미지 로드 실패 시 플레이스홀더
                placeholder = QLabel("📷\n이미지")
                placeholder.setAlignment(Qt.AlignCenter)
                placeholder.setFixedSize(150, 200)
                placeholder.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
                sample_layout.addWidget(placeholder)
            
            # 텍스트 입력 영역
            text_layout = QVBoxLayout()
            
            # 페이지 번호 입력
            page_layout = QHBoxLayout()
            page_layout.addWidget(QLabel("페이지:"))
            page_input = QTextEdit()
            page_input.setMaximumHeight(30)
            page_input.setPlaceholderText("p.33 또는 title_page 등")
            page_layout.addWidget(page_input)
            text_layout.addLayout(page_layout)
            
            # Ground Truth 텍스트 입력
            text_layout.addWidget(QLabel("📝 Ground Truth 텍스트 (GPT에서 복사):"))
            text_input = QTextEdit()
            text_input.setPlaceholderText("GPT에서 추출한 Ground Truth 텍스트를 여기에 붙여넣으세요...")
            text_input.setMinimumHeight(150)
            text_input.setMaximumHeight(200)
            text_layout.addWidget(text_input)
            
            # 측정 여부 체크박스
            measure_checkbox = QCheckBox("CER 측정 포함")
            measure_checkbox.setChecked(True)  # 기본값: 측정 포함
            text_layout.addWidget(measure_checkbox)
            
            sample_layout.addLayout(text_layout)
            
            # 입력창들을 딕셔너리에 저장
            self.sample_text_inputs[sample.name] = {
                'page': page_input,
                'text': text_input,
                'measure': measure_checkbox,
                'sample_path': sample
            }
            
            self.samples_layout.addWidget(sample_group)
        
        # 스크롤 영역 표시
        self.samples_scroll.setVisible(True)
        
        self.logger.info(f"📝 Ground Truth 입력 UI 생성: {len(samples)}개 샘플")
    
    def on_sample_error(self, error_msg: str):
        """샘플 생성 오류"""
        self.logger.error(f"샘플 생성 실패: {error_msg}")
        QMessageBox.critical(self, "오류", error_msg)
        self.generate_samples_btn.setEnabled(True)
    
    def build_gpt_pack(self):
        """GPT Pack 빌드 (Worker Thread) - SnapTXT 또는 Vision API 선택"""
        if not self.generated_samples:
            QMessageBox.warning(self, "오류", "먼저 샘플을 생성하세요")
            return
        
        self.logger.info("📦 GPT Pack 빌드 시작")
        
        # OCR 방법 결정
        use_vision_api = self.vision_ocr_radio.isChecked()
        
        if use_vision_api:
            # Google Vision API 사용
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                QMessageBox.warning(
                    self, "API 키 없음", 
                    "Google Vision API 키가 설정되지 않았습니다.\n\n"
                    "PowerShell에서 다음 명령어를 실행하세요:\n"
                    '$env:GOOGLE_API_KEY = "your_api_key"'
                )
                return
            
            self.logger.info("🚀 Google Vision API OCR 사용")
            self.ocr_worker = VisionOCRWorker(self.generated_samples, api_key, self.logger)
        else:
            # SnapTXT OCR 사용 (기존 방식)
            if not self.system_manager:
                QMessageBox.warning(self, "오류", "SnapTXT 시스템이 초기화되지 않았습니다")
                return
            
            self.logger.info("📱 SnapTXT OCR 사용")
            self.ocr_worker = OCRWorker(self.generated_samples, self.system_manager, self.logger)
        
        # Worker 연결 및 시작
        self.ocr_worker.progress.connect(self.ocr_progress.setValue)
        self.ocr_worker.finished.connect(self.on_gpt_pack_built)
        self.ocr_worker.error.connect(self.on_gpt_pack_error)
        self.ocr_worker.start()
        
        self.build_gpt_pack_btn.setEnabled(False)
    
    def on_gpt_pack_built(self, ocr_results: Dict[str, str]):
        """GPT Pack 빌드 완료"""
        self.ocr_results = ocr_results
        
        # GPT 입력 파일 생성
        gpt_dir = self.snaptxt_dir / "gpt"
        
        # 1. gpt_input_ocr.txt 생성
        input_content = ""
        for i, (sample_name, ocr_text) in enumerate(ocr_results.items(), 1):
            input_content += f"### SAMPLE_{i:02d} ({sample_name})\n"
            input_content += f"{ocr_text}\n\n"
        
        input_file = gpt_dir / "gpt_input_ocr.txt"
        input_file.write_text(input_content, encoding='utf-8')
        
        # 2. gpt_prompt.txt 생성 (Phase 2.7 프롬프트)
        prompt_content = """당신은 OCR 후처리 전문가입니다. 다음 OCR 텍스트들을 분석하여 layout_specific 규칙을 生成해주세요.

특히 다음에 집중해주세요:
1. 줄바꿈으로 인한 어절 분리 오류 (예: "자아 을" → "자아를")
2. 단어 중간 분리 오류 (예: "만들 어진" → "만들어진")  
3. 대화문 경계 문제
4. 조사 분리 패턴

각 샘플별로 발견된 패턴을 정리하고, 이를 수정한 결과를 제시해주세요.
의심스러운 부분은 [[ ]] 표기를 사용하세요.

Phase 2.7 구조 복원 중심으로 분석해주세요."""
        
        prompt_file = gpt_dir / "gpt_prompt.txt"
        prompt_file.write_text(prompt_content, encoding='utf-8')
        
        self.logger.info("✅ GPT Pack 생성 완료")
        
        # 결과 표시
        result_text = f"📦 GPT Pack 생성 완료:\n\n"
        result_text += f"📄 생성된 파일:\n"
        result_text += f"   {input_file.name} ({input_file.stat().st_size // 1024}KB)\n"
        result_text += f"   {prompt_file.name} ({prompt_file.stat().st_size // 1024}KB)\n\n"
        result_text += f"📊 OCR 결과 요약:\n"
        
        for sample_name, text in ocr_results.items():
            result_text += f"   {sample_name}: {len(text)}자\n"
        
        self.gpt_result_text.setPlainText(result_text)
        
        # Google Vision API 사용 시 자동으로 다음 단계로 진행
        if self.vision_ocr_radio.isChecked():
            self.logger.info("🚀 Google Vision API 완료 - 자동으로 Profile 생성 준비")
            self.gpt_result_input.setPlainText("Google Vision API 자동 완료")
            QMessageBox.information(
                self, "자동화 완료", 
                "🎉 Google Vision API OCR이 완료되었습니다!\n\n"
                "이제 '다음 Profile 생성' 버튼을 눌러 Ground Truth를 생성하세요."
            )
        
        self.build_gpt_pack_btn.setEnabled(True)
    
    def on_gpt_pack_error(self, error_msg: str):
        """GPT Pack 빌드 오류"""
        self.logger.error(f"GPT Pack 빌드 실패: {error_msg}")
        QMessageBox.critical(self, "오류", error_msg)
        self.build_gpt_pack_btn.setEnabled(True)
    
    def build_profile(self):
        """Book Profile 생성 - SnapTXT Layout Restoration 연동"""
        gpt_result = self.gpt_result_input.toPlainText().strip()
        
        # Google Vision API 자동 완료 처리
        if gpt_result == "Google Vision API 자동 완료":
            self.logger.info("🚀 Google Vision API 자동 완료 - OCR 결과로 Profile 생성")
        elif not gpt_result:
            QMessageBox.warning(self, "오류", "GPT 결과를 입력하세요")
            return
        
        if not self.system_manager:
            QMessageBox.warning(self, "오류", "SnapTXT 시스템이 초기화되지 않았습니다")
            return
        
        self.logger.info("🧠 Profile 생성 시작")
        
        # Google Vision API 자동 완료가 아닌 경우에만 검증
        if gpt_result != "Google Vision API 자동 완료":
            sample_count = gpt_result.count("SAMPLE_")
            if sample_count < len(self.generated_samples) // 2:
                QMessageBox.warning(self, "경고", f"샘플 수가 부족합니다. ({sample_count}/{len(self.generated_samples)})")
        
        # SnapTXT Layout Adapter로 Profile 생성
        sample_texts = list(self.ocr_results.values())
        profile_data = self.system_manager.layout_adapter.generate_profile(
            gpt_result, sample_texts, "textbook"
        )
        
        # Profile 저장
        profile_file = self.snaptxt_dir / "profiles" / "book_profile.yaml"
        import yaml
        with open(profile_file, 'w', encoding='utf-8') as f:
            yaml.dump(profile_data, f, allow_unicode=True, default_flow_style=False)
        
        self.logger.info("💾 book_profile.yaml 저장 완료")
        
        # 결과 표시
        result_text = f"🧠 Profile 생성 완료:\n\n"
        result_text += f"📊 생성된 규칙: {profile_data['type']} {len(profile_data['rules'])}개\n"
        result_text += f"📋 규칙 유형:\n"
        
        rule_types = {}
        for rule in profile_data['rules']:
            rule_type = rule['rule_type']
            rule_types[rule_type] = rule_types.get(rule_type, 0) + 1
        
        for rule_type, count in rule_types.items():
            result_text += f"   {rule_type}: {count}개\n"
        
        # SnapTXT 시스템 신뢰도 표시
        metadata = profile_data.get('metadata', {})
        if 'confidence_metrics' in metadata:
            conf = metadata['confidence_metrics']
            result_text += f"\n🔍 SnapTXT 품질 분석:\n"
            result_text += f"   평균 신뢰도: {conf.get('avg_confidence', 0):.2f}\n"
            result_text += f"   고우선순위: {conf.get('high_priority_count', 0)}개\n"
        
        result_text += f"\n💾 저장 위치: {profile_file}\n"
        
        self.profile_result_text.setPlainText(result_text)
        self.apply_test_btn.setEnabled(True)
        self.logger.info("✅ Profile Builder 완료")
    
    def apply_test(self):
        """Apply Test 실행 - SnapTXT CER 분해 측정 ★"""
        if not self.generated_samples:
            QMessageBox.warning(self, "오류", "먼저 샘플을 생성하세요")
            return
        
        if not self.system_manager:
            QMessageBox.warning(self, "오류", "SnapTXT 시스템이 초기화되지 않았습니다")
            return
        
        profile_file = self.snaptxt_dir / "profiles" / "book_profile.yaml"
        if not profile_file.exists():
            QMessageBox.warning(self, "오류", "먼저 Profile을 생성하세요")
            return
        
        # 테스트용 5페이지 랜덤 선택 (기존 샘플 제외)
        sample_names = {s.name for s in self.generated_samples}
        available_images = [img for img in self.image_files if img.name not in sample_names]
        
        if len(available_images) < 5:
            QMessageBox.warning(self, "경고", f"테스트 가능한 이미지가 부족합니다. ({len(available_images)}장)")
            available_images = self.image_files[:5]  # 기존 샘플 포함해서라도 테스트
        
        test_samples = random.sample(available_images, min(5, len(available_images)))
        
        self.logger.info(f"📊 SnapTXT Apply Test 시작: {len(test_samples)}장")
        
        # Worker 시작 - SnapTXT 통합 시스템 사용
        self.test_worker = ApplyTestWorker(
            test_samples, profile_file, self.system_manager, self.logger
        )
        self.test_worker.progress.connect(self.test_progress.setValue)
        self.test_worker.finished.connect(self.on_apply_test_finished)
        self.test_worker.error.connect(self.on_apply_test_error)
        self.test_worker.start()
        
        self.apply_test_btn.setEnabled(False)
    
    def on_apply_test_finished(self, results: Dict):
        """Apply Test 완료 - Phase 2.6 스타일 결과 표시 + Ground Truth 지원"""
        self.test_results = results
        cer_data = results['cer_analysis']
        
        # 측정 모드 확인
        is_real_measurement = cer_data.get('sample_count', 0) > 0
        
        # 헤더 표시
        if is_real_measurement:
            result_text = f"🔍 Profile 효과 측정 ({cer_data['sample_count']}페이지 - 실제 Ground Truth)\n\n"
        else:
            result_text = f"🔍 Profile 효과 측정 ({len(results['test_samples'])}페이지 - 시뮬레이션)\n\n"
        
        # Phase 2.6 스타일 CER 분해 결과 포맷팅
        before = cer_data['before']
        after = cer_data['after']
        improvement = cer_data['improvement']
        
        result_text += f"전체 CER:     {before['cer_all']:.1f}% → {after['cer_all']:.1f}% "
        if improvement['cer_all'] > 0:
            result_text += f"(+{improvement['cer_all']:.1f}% 개선) ✅\n"
        else:
            result_text += f"({improvement['cer_all']:.1f}%) ❌\n"
        
        result_text += f"├── 글자 인식: {before['cer_all'] - before['cer_space_only']:.1f}% → {after['cer_all'] - after['cer_space_only']:.1f}% (변화 없음)\n"
        result_text += f"├── 공백 처리: {before['cer_space_only']:.1f}% → {after['cer_space_only']:.1f}% "
        
        if improvement['cer_space_only'] > 0:
            result_text += f"(+{improvement['cer_space_only']:.1f}% 개선) ⭐\n"
        else:
            result_text += f"({improvement['cer_space_only']:.1f}%)\n"
        
        result_text += f"└── 문장부호: {before['cer_punctuation']:.1f}% → {after['cer_punctuation']:.1f}% "
        
        if improvement['cer_punctuation'] > 0:
            result_text += f"(+{improvement['cer_punctuation']:.1f}% 개선)\n"
        else:
            result_text += f"(변화 없음)\n"
        
        # 기여도 분석
        contrib = cer_data['contribution_analysis']
        result_text += f"\n🎯 개선 기여도:\n"
        result_text += f"- layout_specific 규칙: {contrib['layout_specific']:.1f}% (+{improvement['cer_all']:.1f}%)\n"
        result_text += f"- 전통적 교정: {contrib['traditional']:.1f}%\n"
        
        # 결론
        if improvement['cer_all'] > 2.0:
            result_text += f"\n✅ Phase 2.7 구조 복원 전략 효과 입증!\n"
        elif improvement['cer_all'] > 0:
            result_text += f"\n🔍 Phase 2.7 효과 미미 - 규칙 보완 필요\n"
        else:
            result_text += f"\n❌ Profile 효과 없음 - 재검토 필요\n"
        
        # 측정 신뢰성 표시
        if is_real_measurement:
            result_text += f"\n📊 실제 Ground Truth 기반 정확한 측정\n"
            result_text += f"📚 책: \"이 순간의 나\" (에크하르트 톨레)\n"
            if 'test_samples' in cer_data:
                result_text += f"📋 매칭된 샘플:\n"
                for sample in cer_data['test_samples']:
                    result_text += f"   {sample}\n"
        else:
            result_text += f"\n⚠️ 시뮬레이션 측정 - Ground Truth 매칭 실패\n"
            result_text += f"📋 테스트 샘플:\n"
            for sample_name in results['test_samples']:
                result_text += f"   {sample_name}\n"
        
        # 결과 저장
        result_file = self.snaptxt_dir / "logs" / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        result_text += f"\n💾 결과 저장: {result_file.name}\n"
        
        self.test_result_text.setPlainText(result_text)
        self.apply_test_btn.setEnabled(True)
        
        improvement_value = improvement['cer_all']
        if is_real_measurement:
            self.logger.info(f"✨ Apply Test 완료 (실제 측정): +{improvement_value:.1f}% 개선")
        else:
            self.logger.info(f"🔧 Apply Test 완료 (시뮬레이션): +{improvement_value:.1f}% 개선")
    
    def on_apply_test_error(self, error_msg: str):
        """Apply Test 오류"""
        self.logger.error(f"Apply Test 실패: {error_msg}")
        QMessageBox.critical(self, "오류", error_msg)
        self.apply_test_btn.setEnabled(True)
    
    def generate_ground_truth_json(self):
        """입력된 데이터로 Ground Truth JSON 생성"""
        try:
            if not self.sample_text_inputs:
                QMessageBox.warning(self, "경고", "먼저 샘플을 생성하세요")
                return
            
            # Ground Truth 데이터 수집
            ground_truth_data = {
                "book_title": self.book_folder.name if self.book_folder else "Unknown Book",
                "ground_truth_version": "v2.0_ui_generated",
                "pages": []
            }
            
            for sample_name, inputs in self.sample_text_inputs.items():
                page_text = inputs['page'].toPlainText().strip()
                gt_text = inputs['text'].toPlainText().strip()
                should_measure = inputs['measure'].isChecked()
                
                if gt_text:  # 텍스트가 입력된 경우만 추가
                    # 페이지 번호 처리
                    try:
                        page_num = int(page_text.replace('p.', '').replace('page', '').strip())
                    except ValueError:
                        page_num = page_text if page_text else "unknown"
                    
                    page_entry = {
                        "image_file": sample_name,
                        "page": page_num,
                        "measure": should_measure,
                        "notes": f"UI 입력 - {page_text}",
                        "text": gt_text
                    }
                    
                    ground_truth_data["pages"].append(page_entry)
            
            if not ground_truth_data["pages"]:
                QMessageBox.warning(self, "경고", "Ground Truth 텍스트를 입력하세요")
                return
            
            # JSON 파일 저장
            if self.snaptxt_dir:
                gt_dir = self.snaptxt_dir / "ground_truth"
                gt_dir.mkdir(exist_ok=True)
                gt_file = gt_dir / "ground_truth_map.json"
            else:
                gt_file = Path("ground_truth_map.json")
            
            with open(gt_file, 'w', encoding='utf-8') as f:
                json.dump(ground_truth_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"💾 Ground Truth JSON 저장: {gt_file}")
            QMessageBox.information(self, "완료", f"Ground Truth JSON이 저장되었습니다!\n\n{gt_file}")
            
        except Exception as e:
            self.logger.error(f"Ground Truth JSON 생성 실패: {str(e)}")
            QMessageBox.critical(self, "오류", f"JSON 생성 중 오류가 발생했습니다:\n{str(e)}")
    
    def preview_ground_truth_json(self):
        """Ground Truth JSON 미리보기"""
        try:
            if not self.sample_text_inputs:
                QMessageBox.warning(self, "경고", "먼저 샘플을 생성하세요")
                return
            
            # 미리보기용 데이터 생성
            preview_data = {
                "book_title": self.book_folder.name if self.book_folder else "Unknown Book",
                "ground_truth_version": "v2.0_ui_generated",
                "pages": []
            }
            
            for sample_name, inputs in self.sample_text_inputs.items():
                page_text = inputs['page'].toPlainText().strip()
                gt_text = inputs['text'].toPlainText().strip()
                should_measure = inputs['measure'].isChecked()
                
                if gt_text:  # 텍스트가 입력된 경우만 추가
                    try:
                        page_num = int(page_text.replace('p.', '').replace('page', '').strip())
                    except ValueError:
                        page_num = page_text if page_text else "unknown"
                    
                    # 미리보기용으로 텍스트 축약
                    preview_text = gt_text[:100] + "..." if len(gt_text) > 100 else gt_text
                    
                    page_entry = {
                        "image_file": sample_name,
                        "page": page_num,
                        "measure": should_measure,
                        "notes": f"UI 입력 - {page_text}",
                        "text": preview_text
                    }
                    
                    preview_data["pages"].append(page_entry)
            
            # 미리보기 다이얼로그
            dialog = QDialog(self)
            dialog.setWindowTitle("📄 Ground Truth JSON 미리보기")
            dialog.resize(800, 600)
            
            layout = QVBoxLayout(dialog)
            
            text_area = QTextEdit()
            text_area.setPlainText(json.dumps(preview_data, ensure_ascii=False, indent=2))
            text_area.setFont(QFont("Courier New", 9))
            layout.addWidget(text_area)
            
            button_layout = QHBoxLayout()
            
            copy_btn = QPushButton("📋 클립보드 복사")
            copy_btn.clicked.connect(lambda: self.copy_json_to_clipboard(preview_data))
            button_layout.addWidget(copy_btn)
            
            close_btn = QPushButton("닫기")
            close_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(close_btn)
            
            layout.addLayout(button_layout)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"미리보기 생성 중 오류가 발생했습니다:\n{str(e)}")
    
    def copy_json_to_clipboard(self, data):
        """JSON을 클립보드에 복사"""
        try:
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            QApplication.clipboard().setText(json_str)
            QMessageBox.information(self, "완료", "JSON이 클립보드에 복사되었습니다!")
        except Exception as e:
            QMessageBox.warning(self, "오류", f"클립보드 복사 실패:\n{str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 한글 폰트 설정
    app.setApplicationName("SnapTXT 실험 루프 UI")
    
    window = BookExperimentUI()
    window.show()
    
    sys.exit(app.exec())