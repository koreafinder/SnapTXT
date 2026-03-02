#!/usr/bin/env python3
"""
PC 앱 피드백 통합 모듈

기존 pc_app.py에 사용자 피드백 수집 기능을 추가하는 확장 모듈
"""

import sys
import re
from pathlib import Path
from datetime import datetime

# PyQt5 import with error handling
try:
    from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                                QPushButton, QLabel, QGroupBox, QMessageBox,
                                QCheckBox, QSpinBox, QTabWidget, QDialog,
                                QDialogButtonBox, QScrollArea)
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QFont
except ImportError:
    print("PyQt5가 설치되지 않았습니다. pip install PyQt5를 실행하세요.")
    sys.exit(1)

# 피드백 수집기 import
sys.path.insert(0, str(Path(__file__).parent.parent))
from snaptxt.learning.feedback_collector import UserFeedbackCollector


class FeedbackWidget(QWidget):
    """사용자 피드백 수집을 위한 위젯"""
    
    feedback_collected = pyqtSignal(dict)  # 피드백 수집 완료 시그널
    
    def __init__(self):
        super().__init__()
        self.collector = UserFeedbackCollector()
        self.current_original_text = ""
        self.current_image_source = ""
        self.init_ui()
        
    def init_ui(self):
        """피드백 UI 초기화"""
        layout = QVBoxLayout(self)
        
        # 피드백 활성화 체크박스
        self.check_enable_feedback = QCheckBox("🧠 실시간 학습 활성화 (Beta)")
        self.check_enable_feedback.setToolTip("사용자 수정사항을 분석하여 자동으로 후처리 규칙을 개선합니다")
        self.check_enable_feedback.setChecked(True)
        layout.addWidget(self.check_enable_feedback)
        
        # 학습 상태 표시
        self.label_learning_status = QLabel("📊 학습 상태: 준비됨")
        self.label_learning_status.setStyleSheet("color: #2e7d32; font-weight: bold;")
        layout.addWidget(self.label_learning_status)
        
        # 텍스트 수정 영역
        text_group = QGroupBox("✏️ 텍스트 수정 및 학습")
        text_layout = QVBoxLayout(text_group)
        
        # 원본 텍스트 (읽기 전용)
        text_layout.addWidget(QLabel("🔍 OCR 원본:"))
        self.text_original = QTextEdit()
        self.text_original.setMaximumHeight(100)
        self.text_original.setReadOnly(True)
        self.text_original.setStyleSheet("background-color: #f5f5f5;")
        text_layout.addWidget(self.text_original)
        
        # 수정된 텍스트 (편집 가능)
        text_layout.addWidget(QLabel("✏️ 수정된 텍스트 (편집 가능):"))
        self.text_corrected = QTextEdit()
        self.text_corrected.setMaximumHeight(120)
        self.text_corrected.textChanged.connect(self.on_text_changed)
        text_layout.addWidget(self.text_corrected)
        
        # 피드백 버튼들
        btn_layout = QHBoxLayout()
        
        self.btn_submit_feedback = QPushButton("📝 학습 적용")
        self.btn_submit_feedback.clicked.connect(self.submit_feedback)
        self.btn_submit_feedback.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        self.btn_submit_feedback.setEnabled(False)
        btn_layout.addWidget(self.btn_submit_feedback)
        
        self.btn_reset = QPushButton("🔄 원본 복원")
        self.btn_reset.clicked.connect(self.reset_text)
        btn_layout.addWidget(self.btn_reset)
        
        self.btn_view_patterns = QPushButton("🎯 학습된 패턴")
        self.btn_view_patterns.clicked.connect(self.view_learned_patterns)
        btn_layout.addWidget(self.btn_view_patterns)
        
        text_layout.addLayout(btn_layout)
        layout.addWidget(text_group)
        
        # 학습 통계
        stats_group = QGroupBox("📈 학습 통계")
        stats_layout = QVBoxLayout(stats_group)
        
        self.label_feedback_count = QLabel("수집된 피드백: 0개")
        stats_layout.addWidget(self.label_feedback_count)
        
        self.label_pattern_count = QLabel("학습된 패턴: 0개")
        stats_layout.addWidget(self.label_pattern_count)
        
        self.label_confidence = QLabel("평균 신뢰도: N/A")
        stats_layout.addWidget(self.label_confidence)
        
        layout.addWidget(stats_group)
        
        # 초기 통계 업데이트
        self.update_statistics()
    
    def set_ocr_result(self, text: str, image_source: str):
        """OCR 결과 설정"""
        self.current_original_text = text
        self.current_image_source = image_source
        
        self.text_original.setText(text)
        self.text_corrected.setText(text)
        self.btn_submit_feedback.setEnabled(False)
        
        # Phase 1 규칙이 이미 적용된 텍스트라고 표시
        self.label_learning_status.setText("📊 Phase 1 규칙 적용됨, 추가 학습 준비됨")
    
    def on_text_changed(self):
        """텍스트 변경 감지"""
        if not self.check_enable_feedback.isChecked():
            return
            
        original = self.current_original_text.strip()
        corrected = self.text_corrected.toPlainText().strip()
        
        if original and corrected and original != corrected:
            self.btn_submit_feedback.setEnabled(True)
            self.label_learning_status.setText("✏️ 수정 감지됨 - 학습 준비")
            self.label_learning_status.setStyleSheet("color: #ff9800; font-weight: bold;")
        else:
            self.btn_submit_feedback.setEnabled(False)
            self.label_learning_status.setText("📊 변경 사항 없음")
            self.label_learning_status.setStyleSheet("color: #2e7d32; font-weight: bold;")
    
    def submit_feedback(self):
        """피드백 제출 및 학습"""
        if not self.check_enable_feedback.isChecked():
            QMessageBox.information(self, "알림", "실시간 학습이 비활성화되어 있습니다.")
            return
            
        original = self.current_original_text.strip()
        corrected = self.text_corrected.toPlainText().strip()
        
        if not original or not corrected:
            QMessageBox.warning(self, "경고", "원본 또는 수정된 텍스트가 없습니다.")
            return
            
        if original == corrected:
            QMessageBox.information(self, "알림", "변경 사항이 없습니다.")
            return
        
        try:
            # 피드백 수집
            feedback_data = self.collector.collect_user_correction(
                original, corrected, self.current_image_source
            )
            
            # 성공 메시지
            corrections = feedback_data.get('correction_count', 0)
            patterns = len(feedback_data.get('extracted_patterns', []))
            
            msg = f"✅ 학습 완료!\n\n"
            msg += f"📝 수정사항: {corrections}개\n"
            msg += f"🎯 추출된 패턴: {patterns}개\n"
            msg += f"🧠 지속적인 학습으로 OCR 품질이 향상됩니다."
            
            QMessageBox.information(self, "학습 완료", msg)
            
            # 통계 업데이트
            self.update_statistics()
            
            # 상태 업데이트
            self.label_learning_status.setText("✅ 학습 완료 - 패턴 업데이트됨")
            self.label_learning_status.setStyleSheet("color: #4caf50; font-weight: bold;")
            
            # 시그널 발생
            self.feedback_collected.emit(feedback_data)
            
            # 버튼 비활성화
            self.btn_submit_feedback.setEnabled(False)
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"학습 중 오류가 발생했습니다:\n{e}")
    
    def reset_text(self):
        """텍스트 원본으로 복원"""
        self.text_corrected.setText(self.current_original_text)
        self.btn_submit_feedback.setEnabled(False)
        self.label_learning_status.setText("🔄 원본 복원됨")
    
    def view_learned_patterns(self):
        """학습된 패턴 보기"""
        dialog = LearnedPatternsDialog(self.collector, self)
        dialog.exec_()
    
    def update_statistics(self):
        """학습 통계 업데이트"""
        try:
            # 피드백 로그 카운트
            feedback_count = 0
            if self.collector.feedback_log.exists():
                with open(self.collector.feedback_log, 'r', encoding='utf-8') as f:
                    feedback_count = sum(1 for line in f)
            
            # 학습된 패턴 정보
            patterns = self.collector.get_high_confidence_patterns(min_confidence=0.3, min_frequency=1)
            pattern_count = len(patterns)
            
            avg_confidence = 0
            if patterns:
                avg_confidence = sum(p['confidence'] for p in patterns) / len(patterns)
            
            # UI 업데이트
            self.label_feedback_count.setText(f"수집된 피드백: {feedback_count}개")
            self.label_pattern_count.setText(f"학습된 패턴: {pattern_count}개")
            
            if pattern_count > 0:
                self.label_confidence.setText(f"평균 신뢰도: {avg_confidence:.0%}")
            else:
                self.label_confidence.setText("평균 신뢰도: N/A")
                
        except Exception as e:
            print(f"통계 업데이트 오류: {e}")


class LearnedPatternsDialog(QDialog):
    """학습된 패턴 보기 대화상자"""
    
    def __init__(self, collector: UserFeedbackCollector, parent=None):
        super().__init__(parent)
        self.collector = collector
        self.setWindowTitle("🎯 학습된 패턴")
        self.setMinimumSize(600, 400)
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # 패턴 목록
        scroll_area = QScrollArea()
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        patterns = self.collector.get_high_confidence_patterns(min_confidence=0.3, min_frequency=1)
        
        if not patterns:
            label = QLabel("🔍 아직 학습된 패턴이 없습니다.\n\nOCR 결과를 수정하면 자동으로 패턴을 학습합니다.")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #666; font-size: 14px; padding: 20px;")
            content_layout.addWidget(label)
        else:
            for i, pattern in enumerate(patterns, 1):
                pattern_widget = self.create_pattern_widget(i, pattern)
                content_layout.addWidget(pattern_widget)
        
        scroll_area.setWidget(content_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # 버튼
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Stage3 규칙 생성 버튼
        if patterns:
            btn_generate_rules = QPushButton("🔧 Stage3 규칙 생성")
            btn_generate_rules.clicked.connect(self.generate_stage3_rules)
            btn_generate_rules.setStyleSheet("QPushButton { background-color: #2196F3; color: white; }")
            layout.insertWidget(-1, btn_generate_rules)
    
    def create_pattern_widget(self, index: int, pattern: Dict) -> QWidget:
        """개별 패턴 위젯 생성"""
        widget = QGroupBox(f"패턴 {index}")
        layout = QVBoxLayout(widget)
        
        # 패턴 정보
        info_text = f"🔍 패턴: {pattern['pattern']}\n"
        info_text += f"✏️ 수정: {pattern['replacement']}\n"
        info_text += f"📊 신뢰도: {pattern['confidence']:.0%} | 빈도: {pattern['frequency']}회\n"
        info_text += f"📁 카테고리: {pattern['category']}\n"
        info_text += f"🕒 학습일: {pattern['learned_at'][:10]}"
        
        label = QLabel(info_text)
        label.setWordWrap(True)
        layout.addWidget(label)
        
        return widget
    
    def generate_stage3_rules(self):
        """Stage3 규칙 생성"""
        update = self.collector.generate_stage3_rules_update()
        
        if not update.get('update_available', False):
            QMessageBox.information(self, "알림", "생성할 고신뢰도 규칙이 없습니다.")
            return
            
        total_rules = update['total_new_rules']
        msg = f"✅ {total_rules}개의 새로운 규칙이 준비되었습니다!\n\n"
        
        for category, rules in update['rules_by_category'].items():
            if rules:
                msg += f"📋 {category}: {len(rules)}개\n"
        
        msg += f"\n🔧 이 규칙들을 Stage3에 적용하시겠습니까?"
        
        reply = QMessageBox.question(self, "Stage3 규칙 생성", msg,
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.apply_learned_rules_to_stage3(update)
    
    def apply_learned_rules_to_stage3(self, update: Dict):
        """학습된 규칙을 Stage3에 적용"""
        try:
            # 이 기능은 Phase 2의 다음 단계에서 구현
            QMessageBox.information(self, "구현 예정", 
                                  "자동 Stage3 규칙 적용은 Phase 2.2에서 구현됩니다.\n"
                                  "현재는 수동으로 적용해주세요.")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"규칙 적용 중 오류: {e}")


def integrate_feedback_to_pc_app():
    """PC 앱에 피드백 기능을 통합하는 방법을 안내하는 함수"""
    integration_guide = """
    PC 앱(pc_app.py)에 피드백 기능 통합 방법:
    
    1. 기존 create_right_panel() 메소드에 피드백 탭 추가:
    
    def create_right_panel(self):
        # ... 기존 코드 ...
        
        # 피드백 학습 탭 추가
        self.feedback_widget = FeedbackWidget() 
        self.tab_widget.addTab(self.feedback_widget, "🧠 학습")
        
        # OCR 결과 처리 시 피드백 위젯에 연결
        self.feedback_widget.feedback_collected.connect(self.on_feedback_collected)
        
        return panel
    
    2. OCR 처리 완료 후 피드백 위젯에 결과 전달:
    
    def on_ocr_complete(self, result_text, image_source):
        # ... 기존 결과 표시 코드 ...
        
        # 피드백 위젯에 OCR 결과 설정
        self.feedback_widget.set_ocr_result(result_text, image_source)
    
    3. 피드백 수집 완료 시 처리:
    
    def on_feedback_collected(self, feedback_data):
        print(f"피드백 수집됨: {feedback_data['correction_count']}개 수정사항")
        # 필요시 추가 처리...
    """
    
    return integration_guide


if __name__ == "__main__":
    # 테스트 실행
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 피드백 위젯 테스트
    widget = FeedbackWidget()
    widget.set_ocr_result(
        "마이 클 싱 어는 유명한 명 상 가입니다. 연구 결과가 드러워습니다.",
        "test_image.jpg"
    )
    widget.show()
    
    app.exec_()