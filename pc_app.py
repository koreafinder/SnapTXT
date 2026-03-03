#!/usr/bin/env python3
"""
SnapTXT PC App - OCR 전용 데스크톱 애플리케이션
이미지/PDF에서 텍스트 추출 및 배치 처리
"""

import sys
import os
import re
from pathlib import Path
import logging

# OCR 프로세서 import
from snaptxt.backend.multi_engine import MultiOCRProcessor, load_default_engine

# 후처리 시스템 import 추가
from snaptxt.postprocess import run_pipeline, Stage2Config, Stage3Config

def ensure_utf8_console():
    """Force UTF-8 console output on Windows so Korean logs stay readable."""

    if os.environ.get("SNAPTXT_ENABLE_UTF8_CONSOLE", "1") != "1":
        return

    if os.name != "nt":  # pragma: no cover - Windows only
        return

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONLEGACYWINDOWSSTDIO", "0")

    for stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            continue


ensure_utf8_console()


LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
ALLOW_CONSOLE_EMOJI = os.environ.get("SNAPTXT_ALLOW_CONSOLE_EMOJI", "0") == "1"
EMOJI_PATTERN = re.compile(
    "["  # 넓은 범위의 이모지/픽토그램 코드를 ASCII로만 대체
    "\U0001F300-\U0001F6FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA70-\U0001FAFF"
    "\u2600-\u27BF"
    "]"
)


class ConsoleFormatter(logging.Formatter):
    """Strip emoji-like glyphs for consoles that fall back to serif fonts."""

    def format(self, record):
        message = super().format(record)
        if ALLOW_CONSOLE_EMOJI:
            return message
        return EMOJI_PATTERN.sub("", message)


console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(ConsoleFormatter(LOG_FORMAT))

file_handler = logging.FileHandler('snaptxt_debug.log', encoding='utf-8')
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

# 🔍 터미널 디버깅 활성화 - 상세한 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler]
)

logger = logging.getLogger(__name__)

# 🚀 앱 시작 로그
logger.info("=" * 60)
logger.info("🚀 SnapTXT PC App 시작 - 가상환경에서 실행 중")
logger.info("=" * 60)


def prewarm_pytorch_stack():
    """Qt GUI 이전에 PyTorch DLL을 사전 로드해 WinError 1114를 예방."""

    try:
        load_default_engine()
        logger.info("🔥 PyTorch DLL 사전 로드 완료 - Qt 초기화 전에 완료")
    except Exception as exc:  # pragma: no cover - 환경 의존
        logger.error("❌ PyTorch DLL 사전 로드 실패: %s", exc)


prewarm_pytorch_stack()


import PyQt5
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QTextEdit, QLabel, 
                            QFileDialog, QListWidget, QProgressBar, QTabWidget,
                            QGroupBox, QCheckBox, QSpinBox, QComboBox, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QLibraryInfo
from PyQt5.QtGui import QFont, QPixmap


def configure_qt_plugin_path():
    """Ensure Qt can find its platform plugins inside this virtual environment."""
    candidates = []

    try:
        qt_location = Path(QLibraryInfo.location(QLibraryInfo.PluginsPath))
        candidates.append(qt_location)
    except Exception as exc:  # pragma: no cover - diagnostic guard
        logger.warning(f"Qt 플러그인 경로 조회 실패: {exc}")

    pyqt_root = Path(PyQt5.__file__).resolve().parent
    candidates.append(pyqt_root / "Qt5" / "plugins")
    candidates.append(pyqt_root / "Qt" / "plugins")
    candidates.append(Path(sys.prefix) / "Lib" / "site-packages" / "PyQt5" / "Qt5" / "plugins")

    for plugin_root in candidates:
        if not plugin_root.exists():
            continue

        os.environ.setdefault("QT_PLUGIN_PATH", str(plugin_root))
        platforms_path = plugin_root / "platforms"
        if platforms_path.exists():
            os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(platforms_path))
        logger.info("Qt 플러그인 경로 설정됨: %s", plugin_root)
        return

    logger.warning("사용 가능한 Qt 플러그인 경로를 찾지 못했습니다. PyQt5 재설치를 권장합니다.")


configure_qt_plugin_path()


class OCRWorkerThread(QThread):
    """OCR 처리를 위한 워커 스레드"""
    progress_updated = pyqtSignal(int)
    text_extracted = pyqtSignal(str, str)  # (filename, extracted_text)
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, file_paths, ocr_settings):
        super().__init__()
        self.file_paths = file_paths
        self.ocr_settings = ocr_settings
        # Qt가 올라오기 전에 load_default_engine()으로 DLL을 사전 로드한다.
        self.ocr_processor = load_default_engine()
        
    def run(self):
        """배치 OCR 처리 실행"""
        try:
            total_files = len(self.file_paths)
            
            for i, file_path in enumerate(self.file_paths):
                # 진행률 업데이트
                progress = int((i / total_files) * 100)
                self.progress_updated.emit(progress)
                
                # OCR 처리
                filename = Path(file_path).name
                extracted_text = self.ocr_processor.process_file(file_path, self.ocr_settings)
                
                # 후처리 파이프라인 적용 (새로 추가)
                if extracted_text and not extracted_text.startswith("❌"):
                    try:
                        print(f"🧠 후처리 시작: {filename} ({len(extracted_text)}자)")
                        
                        # Stage2 + Stage3 후처리 실행
                        processed_text = run_pipeline(
                            extracted_text,
                            stage2_config=Stage2Config(),
                            stage3_config=Stage3Config()
                        )
                        
                        # 후처리 결과 분석
                        if processed_text:
                            change_ratio = abs(len(processed_text) - len(extracted_text)) / len(extracted_text) * 100
                            print(f"✅ 후처리 완료: {len(extracted_text)}자 → {len(processed_text)}자 ({change_ratio:.1f}% 변화)")
                            extracted_text = processed_text
                        else:
                            print(f"⚠️  후처리 결과 없음 - 원본 유지")
                            
                    except Exception as e:
                        # 후처리 실패시 원본 텍스트 사용 (안전성 우선)
                        print(f"⚠️ 후처리 실패 {filename}: {e}")
                        print(f"🛡️  안전성 우선 - 원본 텍스트 사용")
                        # extracted_text는 그대로 유지
                
                # 결과 전송
                self.text_extracted.emit(filename, extracted_text)
                
            self.progress_updated.emit(100)
            self.finished.emit()
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class SnapTXTMainWindow(QMainWindow):
    """SnapTXT 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.file_list = []
        self.ocr_results = {}  # filename: extracted_text
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("SnapTXT - OCR 텍스트 추출기")
        self.setGeometry(100, 100, 1200, 800)
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        
        # 왼쪽 패널: 파일 선택 및 설정
        left_panel = self.create_left_panel()
        layout.addWidget(left_panel, 1)
        
        # 오른쪽 패널: 결과 표시
        right_panel = self.create_right_panel()
        layout.addWidget(right_panel, 2)
        
    def create_left_panel(self):
        """왼쪽 패널 생성: 파일 선택 및 OCR 설정"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 파일 선택 그룹
        file_group = QGroupBox("📂 파일 선택")
        file_layout = QVBoxLayout(file_group)
        
        # 파일 선택 버튼들
        btn_layout = QHBoxLayout()
        
        self.btn_add_files = QPushButton("📄 파일 추가")
        self.btn_add_files.clicked.connect(self.add_files)
        btn_layout.addWidget(self.btn_add_files)
        
        self.btn_add_folder = QPushButton("📁 폴더 추가")  
        self.btn_add_folder.clicked.connect(self.add_folder)
        btn_layout.addWidget(self.btn_add_folder)
        
        self.btn_clear = QPushButton("🗑️ 목록 비우기")
        self.btn_clear.clicked.connect(self.clear_files)
        btn_layout.addWidget(self.btn_clear)
        
        file_layout.addLayout(btn_layout)
        
        # 파일 목록
        self.file_list_widget = QListWidget()
        file_layout.addWidget(self.file_list_widget)
        
        layout.addWidget(file_group)
        
        # OCR 설정 그룹
        ocr_group = QGroupBox("⚙️ EasyOCR 설정 - 단순화된 고성능 OCR")
        ocr_layout = QVBoxLayout(ocr_group)
        
        # EasyOCR 엔진 (하드코딩된 활성 상태)
        easyocr_label = QLabel("🚀 EasyOCR 전용 모드 - 자동 한국어 후처리 적용")
        easyocr_label.setStyleSheet("color: #2e7d32; font-weight: bold; padding: 8px;")
        ocr_layout.addWidget(easyocr_label)
        
        # 언어 설정
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("🌍 언어:"))
        self.combo_language = QComboBox()
        self.combo_language.addItems(["ko+en (한국어+영어)", "ko (한국어만)", "en (영어만)"])
        self.combo_language.setCurrentIndex(0)  # 기본으로 한국어+영어
        lang_layout.addWidget(self.combo_language)
        ocr_layout.addLayout(lang_layout)
        
        # 성능 설정
        perf_layout = QHBoxLayout()
        perf_layout.addWidget(QLabel("📈 스레드 수:"))
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, 4)  # EasyOCR에 최적화
        self.spin_threads.setValue(2)
        perf_layout.addWidget(self.spin_threads)
        ocr_layout.addLayout(perf_layout)
        
        # TTS는 웹에서 처리하므로 PC 앱에서는 제거
        
        # 하드코딩된 옵션들 표시
        features_label = QLabel("✨ 자동 적용: PyKoSpacing 띠어쓰기 교정, 한글 오류 수정, TTS 최적화")
        features_label.setStyleSheet("color: #1565c0; font-size: 11px; font-style: italic; padding: 5px;")
        ocr_layout.addWidget(features_label)
        
        layout.addWidget(ocr_group)
        
        # 처리 버튼 및 진행률
        self.btn_start_ocr = QPushButton("🚀 OCR 시작")
        self.btn_start_ocr.clicked.connect(self.start_ocr_processing)
        self.btn_start_ocr.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        layout.addWidget(self.btn_start_ocr)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        return panel
        
    def create_right_panel(self):
        """오른쪽 패널 생성: 결과 표시"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 결과 탭 위젯
        self.tab_widget = QTabWidget()
        
        # 전체 결과 탭
        self.tab_all_results = QTextEdit()
        self.tab_all_results.setFont(QFont("맑은 고딕", 10))
        self.tab_widget.addTab(self.tab_all_results, "📝 전체 결과")
        
        # 파일별 결과 탭  
        self.tab_file_results = QTextEdit()
        self.tab_file_results.setFont(QFont("맑은 고딕", 10))
        self.tab_widget.addTab(self.tab_file_results, "📄 파일별 결과")
        
        layout.addWidget(self.tab_widget)
        
        # 결과 조작 버튼들
        btn_layout = QHBoxLayout()
        
        self.btn_copy_text = QPushButton("📋 텍스트 복사")
        self.btn_copy_text.clicked.connect(self.copy_text_to_clipboard)
        btn_layout.addWidget(self.btn_copy_text)
        
        self.btn_save_text = QPushButton("💾 텍스트 저장")
        self.btn_save_text.clicked.connect(self.save_text_to_file)
        btn_layout.addWidget(self.btn_save_text)
        
        self.btn_send_to_web = QPushButton("🌐 웹으로 전송")
        self.btn_send_to_web.clicked.connect(self.send_to_web)
        btn_layout.addWidget(self.btn_send_to_web)
        
        self.btn_reload_engines = QPushButton("🔄 엔진 재로드")
        self.btn_reload_engines.clicked.connect(self.reload_ocr_engines)
        btn_layout.addWidget(self.btn_reload_engines)
        
        layout.addLayout(btn_layout)
        
        return panel
        
    def add_files(self):
        """이미지 파일들 추가"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "이미지 파일 선택", "",
            "이미지 파일 (*.png *.jpg *.jpeg *.bmp *.tiff *.gif);;모든 파일 (*.*)"
        )
        
        for file_path in file_paths:
            if file_path not in self.file_list:
                self.file_list.append(file_path)
                filename = Path(file_path).name
                self.file_list_widget.addItem(f"📷 {filename}")
                
    def add_folder(self):
        """폴더의 모든 이미지 파일들 추가"""
        folder_path = QFileDialog.getExistingDirectory(self, "폴더 선택")
        
        if folder_path:
            # 지원하는 이미지 확장자들
            image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif'}
            
            folder = Path(folder_path)
            for file_path in folder.rglob('*'):
                if (file_path.suffix.lower() in image_extensions and 
                    str(file_path) not in self.file_list):
                    self.file_list.append(str(file_path))
                    self.file_list_widget.addItem(f"📷 {file_path.name}")
    
    def clear_files(self):
        """파일 목록 비우기"""
        self.file_list.clear()
        self.file_list_widget.clear()
        self.ocr_results.clear()
        
    def start_ocr_processing(self):
        """OCR 처리 시작"""
        logger.info("🚀 OCR 처리 시작 요청")
        
        if not self.file_list:
            logger.warning("⚠️ 처리할 파일이 없습니다")
            QMessageBox.warning(self, "경고", "처리할 파일이 없습니다.")
            return
            
        # OCR 설정 수집 (단순화됨)
        language_map = {
            "ko+en (한국어+영어)": "ko+en",
            "ko (한국어만)": "ko", 
            "en (영어만)": "en"
        }
        selected_lang = self.combo_language.currentText()
        
        ocr_settings = {
            'language': language_map.get(selected_lang, 'ko+en'),
            'threads': self.spin_threads.value(),
            'use_scientific': True,  # 과학적 전처리 시스템 활성화
            'preprocessing_level': 2  # 레거시 시스템용 기본 레벨
        }
        
        # 🔍 OCR 설정 로그
        logger.info(f"📋 OCR 설정:")
        logger.info(f"  - EasyOCR: True (전용 모드)")
        logger.info(f"  - 언어: {ocr_settings['language']}")
        logger.info(f"  - 스레드: {ocr_settings['threads']}")
        logger.info(f"  - 과학적 전처리: {ocr_settings['use_scientific']}")
        logger.info(f"  - 전처리 레벨: {ocr_settings['preprocessing_level']}")

        logger.info(f"📁 처리할 파일 수: {len(self.file_list)}")
        for i, filepath in enumerate(self.file_list, 1):
            logger.info(f"  {i}. {Path(filepath).name}")
        
        # 최소 검증 생략 - EasyOCR 전용 모드
            
        # UI 상태 변경
        logger.info("🎬 UI 상태 변경 및 워커 스레드 시작")
        self.btn_start_ocr.setText("처리 중...")
        self.btn_start_ocr.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # 워커 스레드 시작
        self.ocr_thread = OCRWorkerThread(self.file_list, ocr_settings)
        self.ocr_thread.progress_updated.connect(self.progress_bar.setValue)
        self.ocr_thread.text_extracted.connect(self.on_text_extracted)
        self.ocr_thread.finished.connect(self.on_ocr_finished)
        self.ocr_thread.error_occurred.connect(self.on_ocr_error)
        self.ocr_thread.start()
        logger.info("✅ OCR 워커 스레드 시작됨")
        
    def on_text_extracted(self, filename, extracted_text):
        """텍스트 추출 완료시 호출"""
        self.ocr_results[filename] = extracted_text
        
        # 전체 결과 탭 업데이트
        all_text = ""
        for fname, text in self.ocr_results.items():
            all_text += f"=== {fname} ===\n{text}\n\n"
        self.tab_all_results.setText(all_text)
        
        # 파일별 결과 탭 업데이트 (최신 파일)
        self.tab_file_results.setText(f"📄 {filename}\n\n{extracted_text}")
        
    def on_ocr_finished(self):
        """OCR 처리 완료"""
        self.btn_start_ocr.setText("🚀 OCR 시작")
        self.btn_start_ocr.setEnabled(True)
        QMessageBox.information(self, "완료", f"{len(self.ocr_results)}개 파일 처리 완료!")
        
    def on_ocr_error(self, error_message):
        """OCR 처리 오류"""
        self.btn_start_ocr.setText("🚀 OCR 시작")
        self.btn_start_ocr.setEnabled(True)
        QMessageBox.critical(self, "오류", f"OCR 처리 중 오류 발생:\n{error_message}")
        
    def copy_text_to_clipboard(self):
        """텍스트를 클립보드에 복사"""
        current_text = self.tab_widget.currentWidget().toPlainText()
        if current_text:
            QApplication.clipboard().setText(current_text)
            QMessageBox.information(self, "복사 완료", "텍스트가 클립보드에 복사되었습니다.")
            
    def save_text_to_file(self):
        """텍스트를 파일로 저장"""
        current_text = self.tab_widget.currentWidget().toPlainText()
        if not current_text:
            QMessageBox.warning(self, "경고", "저장할 텍스트가 없습니다.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "텍스트 파일 저장", "", "텍스트 파일 (*.txt);;모든 파일 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(current_text)
                QMessageBox.information(self, "저장 완료", f"파일이 저장되었습니다:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"파일 저장 중 오류:\n{str(e)}")
                
    def send_to_web(self):
        """웹 서버로 텍스트 전송 (향후 구현)"""
        QMessageBox.information(self, "알림", "웹 연동 기능은 향후 구현 예정입니다.")
        
    def reload_ocr_engines(self):
        """OCR 엔진들 다시 로드"""
        try:
            # 새로운 OCR 프로세서 생성
            processor = load_default_engine()
            processor.init_engines()
            
            # 엔진 정보 확인
            engine_info = processor.get_engine_info()
            
            info_text = "🔄 OCR 엔진 재로드 완료!\n\n"
            for engine, available in engine_info.items():
                status = "✅ 사용 가능" if available else "❌ 없음"
                info_text += f"{engine}: {status}\n"
            
            QMessageBox.information(self, "엔진 재로드", info_text)
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"엔진 재로드 실패:\n{str(e)}")


def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # 애플리케이션 정보 설정
    app.setApplicationName("SnapTXT")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("SnapTXT Team")
    
    # 메인 윈도우 생성 및 표시
    window = SnapTXTMainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()