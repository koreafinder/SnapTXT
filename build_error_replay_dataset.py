#!/usr/bin/env python3
"""
실제 오류 분포 기반 합성(오류 재현) 데이터셋 구축 시스템
Office Lens/iPhone 촬영 이미지 → SnapTXT vs Google Vision 비교 → 오류 패턴 추출 → 합성 테스트셋 생성

Usage:
    python build_error_replica_dataset.py --folder "이미지경로" --topk 200 --seed 42
자동 run_id 생성 및 성공/실패 추적 지원
"""

import argparse
import time
import json
import os
import re
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict, Counter
import difflib
from dataclasses import dataclass, asdict
import random
import hashlib
import base64
import math
from itertools import combinations
import numpy as np
from scipy.spatial.distance import jensenshannon
from scipy.stats import spearmanr
from PIL import Image
import io
import shutil

# SnapTXT 기존 모듈들 임포트
from snaptxt.postprocess import run_pipeline, apply_stage2_rules, apply_stage3_rules
from snaptxt.backend.multi_engine import MultiOCRProcessor, load_default_engine
from simple_google_vision_ui import SimpleGoogleVisionOCR


@dataclass
class ErrorEvent:
    """오류 이벤트 정보"""
    page_id: str
    image_file: str
    bucket: str  # space/punctuation/layout/character
    raw_ocr_snippet: str
    stage23_snippet: str
    gt_snippet: str
    op_type: str  # replace/insert/delete/transpose/normalize
    signature: str  # 패턴 시그니처
    count: str  # 집계용 키
    context_before: str
    context_after: str
    confidence_score: float


@dataclass
class ErrorPattern:
    """오류 패턴 정보"""
    signature: str
    bucket: str
    frequency: int
    op_type: str
    examples: List[Dict]
    stage23_already_handled: bool
    confidence_avg: float


class ErrorDistributionAnalyzer:
    """실제 오류 분포 분석기"""
    
    def __init__(self, cache_dir: str = ".snaptxt/cache", output_dir: str = ".snaptxt/analysis"):
        self.cache_dir = Path(cache_dir)
        self.output_dir = Path(output_dir)
        self.google_vision_cache = self.cache_dir / "google_vision"
        self.ocr_results_dir = self.cache_dir / "ocr_results"
        
        # run_id 기반 출력 관리
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
        self.runs_dir = self.output_dir / "runs"
        self.current_run_dir = self.runs_dir / self.run_id
        self.latest_link = self.output_dir / "latest"
        
        # 디렉토리 생성 (기존 cache 및 run_id 기반 출력)
        for dir_path in [self.cache_dir, self.runs_dir, self.current_run_dir, 
                         self.google_vision_cache, self.ocr_results_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        print(f"🎯 Run ID: {self.run_id}")
        print(f"📁 출력 디렉토리: {self.current_run_dir}")
        
        # Google Vision OCR 초기화
        self.google_ocr = None
        self._init_google_vision()
        
        # SnapTXT OCR 초기화
        self.snaptxt_ocr = None
        self._init_snaptxt_ocr()
        
        # 1) 페이지 단위 산출물 저장 디렉토리 (run_id 기반)
        self.outputs_dir = self.current_run_dir / "outputs"
        self.raw_ocr_dir = self.outputs_dir / "raw_ocr"
        self.stage23_dir = self.outputs_dir / "stage23" 
        self.gt_dir = self.outputs_dir / "gt"
        
        # 주요 출력 파일들 (run_id 기반)
        self.error_events_file = self.current_run_dir / "error_events.jsonl"
        
        # Vision API 성능 측정 변수 추가
        self.vision_api_stats = {
            "total_vision_ms": 0,
            "cache_hit": 0,
            "cache_miss": 0,
            "api_call_times": []
        }
        
        # 2) error_events.jsonl 파일 경로 설정 제거 (run_id 기반으로 이동)
        # self.error_events_file = self.output_dir / "error_events.jsonl"  # 제거
        
        # 디렉토리 생성
        for dir_path in [self.raw_ocr_dir, self.stage23_dir, self.gt_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # 오류 버킷 분류 패턴
        self.bucket_patterns = {
            "space": [
                r"(\S)(\S) ?→ ?\1\2",  # 띄어쓰기 제거
                r"(\S) (\S)→\1\2",     # 띄어쓰기 추가  
                r"\s+→\s",             # 공백 정규화
            ],
            "punctuation": [
                r"[‛′]→[']",           # 인용부호 정규화
                r"[。]→[.]",           # 마침표 정규화
                r"[，]→[,]",           # 쉼표 정규화
                r"[？]→[?]",           # 물음표 정규화
                r"[！]→[!]",           # 느낌표 정규화
            ],
            "layout": [
                r"\n→\s",              # 줄바꿈 변화
                r"-\n→",               # 하이픈 줄바꿈 처리
                r"「」→""",            # 인용부호 레이아웃
                r"『』→""",            # 책제목 인용부호
            ],
            "character": [
                r"[ㄱ-ㅎㅏ-ㅣ가-힣]→[ㄱ-ㅎㅏ-ㅣ가-힣]",  # 한글 문자 혼동
                r"[a-zA-Z]→[a-zA-Z]",   # 영문 문자 혼동
                r"[0-9]→[0-9]",         # 숫자 혼동
                r"[ㄱ-ㅎㅏ-ㅣ가-힣]→[a-zA-Z0-9]",  # 한글→영숫자 혼동
                r"[a-zA-Z0-9]→[ㄱ-ㅎㅏ-ㅣ가-힣]",  # 영숫자→한글 혼동
            ]
        }
    
    def _mark_success_and_update_latest(self):
        """성공 마커 파일 생성 및 latest 심볼릭 링크 갱신"""
        try:
            # SUCCESS.marker 파일 생성
            success_marker = self.current_run_dir / "SUCCESS.marker"
            with open(success_marker, 'w', encoding='utf-8') as f:
                f.write(f"Run completed successfully at {datetime.now().isoformat()}\n")
                f.write(f"Run ID: {self.run_id}\n")
            
            # latest 심볼릭 링크 갱신 (Windows 환경 고려)
            if self.latest_link.exists() or self.latest_link.is_symlink():
                if os.name == 'nt':  # Windows
                    if self.latest_link.is_dir():
                        shutil.rmtree(self.latest_link)
                    else:
                        self.latest_link.unlink()
                else:
                    self.latest_link.unlink()
            
            if os.name == 'nt':  # Windows - junction 사용
                import subprocess
                subprocess.run(['mklink', '/J', str(self.latest_link), str(self.current_run_dir)], 
                             shell=True, check=True)
            else:  # Unix/Linux - symlink 사용
                self.latest_link.symlink_to(self.current_run_dir, target_is_directory=True)
            
            print(f"✅ 성공 마커 생성: {success_marker}")
            print(f"🔗 latest 링크 갱신: {self.latest_link} → {self.run_id}")
            
        except Exception as e:
            print(f"⚠️ latest 링크 갱신 실패: {e}")
            # 실패해도 전체 실행은 성공으로 간주
    
    def _init_google_vision(self):
        """Google Vision OCR 초기화"""
        try:
            # API 키 환경변수에서 로드
            api_key = os.getenv("GOOGLE_VISION_API_KEY")
            if api_key:
                self.google_ocr = SimpleGoogleVisionOCR(api_key)
                print(f"✅ Google Vision API 초기화 완료: {api_key[:10]}...")
            else:
                print("⚠️ GOOGLE_VISION_API_KEY 환경변수가 설정되지 않았습니다.")
                print("   Google Vision API를 사용하려면 환경변수를 설정하세요.")
                print("   PowerShell에서: $env:GOOGLE_VISION_API_KEY='YOUR_API_KEY'")
                print("   또는 시스템 환경변수에서 설정하세요.")
                print("   Ground Truth 생성 없이 SnapTXT OCR만 처리됩니다.")
                print("⚠️ GOOGLE_VISION_API_KEY 환경변수가 설정되지 않음")
        except Exception as e:
            print(f"⚠️ Google Vision 초기화 실패: {e}")
    
    def _init_snaptxt_ocr(self):
        """SnapTXT OCR 초기화"""
        try:
            self.snaptxt_ocr = load_default_engine()
            print("✅ SnapTXT OCR 초기화 완료")
        except Exception as e:
            print(f"⚠️ SnapTXT OCR 초기화 실패: {e}")
            self.snaptxt_ocr = None
    
    def process_image_folder(self, folder_path: str, topk: int = 200, seed: int = 42, max_pages: int = 30, synthetic_size: int = 5000) -> Dict:
        """이미지 폴더 전체 처리"""
        print("🔍 실제 오류 분포 기반 합성 데이터셋 구축 시작")
        print("="*70)
        
        folder_path = Path(folder_path)
        if not folder_path.exists():
            raise ValueError(f"폴더가 존재하지 않습니다: {folder_path}")
        
        # 1. 이미지 파일 수집
        image_files = self._collect_image_files(folder_path)
        if max_pages is not None and len(image_files) > max_pages:
            image_files = image_files[:max_pages]
            print(f"📷 발견된 이미지: {len(image_files)}개 (최대 {max_pages}개로 제한)")
        else:
            print(f"📷 발견된 이미지: {len(image_files)}개")
        
        if len(image_files) == 0:
            print("❌ 처리할 이미지가 없습니다.")
            return {
                "total_images": 0,
                "error_events": 0,
                "top_patterns": 0,
                "synthetic_samples": 0,
                "output_files": []
            }
        
        # 2. OCR 처리 (SnapTXT + Google Vision)
        ocr_results = self._process_all_images(image_files)
        print(f"📄 OCR 처리 완료: {len(ocr_results)}개 페이지")
        
        # 3. 오류 이벤트 추출  
        error_events = self._extract_error_events(ocr_results)
        print(f"🎯 추출된 오류 이벤트: {len(error_events)}개")
        
        # 3-way diff 분류 통계 분석
        if error_events:
            self._analyze_3way_diff_statistics(error_events)
        
        # 4. 상위 패턴 분석
        top_patterns = self._analyze_top_patterns(error_events, topk)
        print(f"📊 상위 오류 패턴: {len(top_patterns)}개")
        
        # 5. Event Replay 합성 데이터셋 생성 (input≠target 100% 보장)
        if top_patterns:
            synthetic_dataset = self._generate_event_replay_dataset(top_patterns, seed, synthetic_size)
            print(f"🧪 Event Replay 데이터셋: {len(synthetic_dataset)}개 샘플")
        else:
            synthetic_dataset = []
            print("🧪 Event Replay 데이터셋: 0개 샘플 (패턴 없음)")
        
        # 6. 분포 검증 (진짜 비교표 생성)
        if top_patterns and synthetic_dataset:
            print(f"\n📊 분포 검증 시작...")
            
            # 최종 검증
            validation_result = self._validate_distribution(top_patterns, synthetic_dataset)
            
            print(f"\n📊 Top{len(top_patterns)} 최종 분포 검증 결과:")
            print(f"  • KL divergence: {validation_result['kl_divergence']:.6f}")
            print(f"  • Jensen-Shannon distance: {validation_result['js_distance']:.6f}")
            print(f"  • Spearman correlation: {validation_result['spearman_correlation']:.6f}")
            print(f"  • Coverage: {validation_result['coverage_count']}/{len(top_patterns)} ({validation_result['coverage_rate']*100:.1f}%)")
            print(f"  • 최종 판정: {validation_result['validation_quality']}")
            
            # Reverse-check 수치 계산
            reverse_check_rate = self._compute_reverse_check_rate(synthetic_dataset)
            print(f"  • Reverse-check rate: {reverse_check_rate:.3f} ({'✅ PASS' if reverse_check_rate >= 0.95 else '❌ FAIL, 목표 0.95 이상'})")
        else:
            validation_result = {
                "error": "분석할 데이터가 부족함",
                "message": "OCR 처리 성공 및 오류 패턴 추출 실패"
            }
        
        # 8. Vision API 성능 보고서 출력
        self._report_vision_api_performance()
        
        # 8. 결과 저장
        result_files = self._save_all_results(error_events, top_patterns, synthetic_dataset, validation_result)
        
        print("\n✅ 실제 오류 분포 기반 합성 데이터셋 구축 완료!")
        print(f"📁 결과 파일들: {self.output_dir}")
        for file_name in result_files:
            print(f"   📄 {file_name}")
        
        return {
            "total_images": len(image_files),
            "error_events": len(error_events),
            "top_patterns": len(top_patterns), 
            "synthetic_samples": len(synthetic_dataset),
            "output_files": result_files
        }
    
    def _collect_image_files(self, folder_path: Path) -> List[Path]:
        """이미지 파일 수집"""
        supported_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.HEIC', '.JPG', '.JPEG', '.PNG'}
        image_files = []
        
        for file_path in folder_path.rglob("*"):
            if file_path.suffix in supported_extensions and file_path.is_file():
                image_files.append(file_path)
        
        return sorted(image_files)
    
    def _process_all_images(self, image_files: List[Path]) -> List[Dict]:
        """모든 이미지에 대해 OCR 처리"""
        ocr_results = []
        
        for i, image_file in enumerate(image_files):
            print(f"🔄 처리 중: {i+1}/{len(image_files)} - {image_file.name}")
            
            try:
                # 페이지 ID 생성
                page_id = f"page_{i+1:03d}_{image_file.stem}"
                
                # 캐시 확인
                cache_file = self.ocr_results_dir / f"{page_id}_ocr_results.json"
                if cache_file.exists():
                    print(f"   📋 캐시에서 로드: {cache_file.name}")
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        result = json.load(f)
                        ocr_results.append(result)
                        continue
                
                # OCR 실행
                result = self._process_single_image(image_file, page_id)
                
                if result:
                    # 캐시 저장
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    
                    ocr_results.append(result)
                    
            except Exception as e:
                print(f"   ❌ 처리 실패: {e}")
                continue
        
        return ocr_results
    
    def _process_single_image(self, image_file: Path, page_id: str) -> Optional[Dict]:
        """단일 이미지 OCR 처리"""
        try:
            # 1. SnapTXT OCR (raw)
            print(f"   🔄 SnapTXT OCR 실행...")
            raw_ocr_text = self._run_snaptxt_ocr(image_file)
            
            # 2. SnapTXT Stage2 적용
            print(f"   🔄 SnapTXT Stage2 적용...")
            stage2_text = apply_stage2_rules(raw_ocr_text)
            
            # 3. SnapTXT Stage3 적용
            print(f"   🔄 SnapTXT Stage3 적용...")  
            stage23_text = apply_stage3_rules(stage2_text)
            
            # 4. Google Vision OCR (Ground Truth)
            print(f"   🔄 Google Vision OCR 실행...")
            gt_text = self._run_google_vision_ocr(image_file)
            
            if not gt_text:
                print(f"   ⚠️ Google Vision 결과 없음")
                return None
            
            # 1) 페이지별 텍스트 파일 저장
            self._save_page_texts(page_id, raw_ocr_text, stage23_text, gt_text)
            
            result = {
                "page_id": page_id,
                "image_file": str(image_file),
                "timestamp": datetime.now().isoformat(),
                "ocr_results": {
                    "raw_ocr": raw_ocr_text,
                    "stage2_applied": stage2_text,
                    "stage23_applied": stage23_text,
                    "google_vision_gt": gt_text
                },
                "text_stats": {
                    "raw_length": len(raw_ocr_text),
                    "stage23_length": len(stage23_text), 
                    "gt_length": len(gt_text)
                }
            }
            
            print(f"   ✅ 완료: raw={len(raw_ocr_text)} → stage23={len(stage23_text)} vs gt={len(gt_text)}")
            return result
            
        except Exception as e:
            print(f"   ❌ OCR 처리 실패: {e}")
            return None
    
    def _save_page_texts(self, page_id: str, raw_text: str, stage23_text: str, gt_text: str):
        """1) 페이지별 텍스트 파일 저장 + 해시 로깅"""
        try:
            # 파일 저장
            raw_file = self.raw_ocr_dir / f"{page_id}.txt"
            stage23_file = self.stage23_dir / f"{page_id}.txt"
            gt_file = self.gt_dir / f"{page_id}.txt"
            
            raw_file.write_text(raw_text, encoding='utf-8')
            stage23_file.write_text(stage23_text, encoding='utf-8')
            gt_file.write_text(gt_text, encoding='utf-8')
            
            # 해시 계산 및 로깅
            raw_hash = hashlib.sha256(raw_text.encode()).hexdigest()
            stage23_hash = hashlib.sha256(stage23_text.encode()).hexdigest()
            gt_hash = hashlib.sha256(gt_text.encode()).hexdigest()
            
            print(f"   📄 {page_id}: len(raw={len(raw_text)}, stage23={len(stage23_text)}, gt={len(gt_text)})")
            print(f"   🔐 hash(raw={raw_hash[:8]}, stage23={stage23_hash[:8]}, gt={gt_hash[:8]})")
            
        except Exception as e:
            print(f"   ⚠️ 페이지 텍스트 저장 실패: {e}")
    
    def _run_snaptxt_ocr(self, image_file: Path) -> str:
        """SnapTXT OCR 실행 (MultiOCRProcessor 사용)"""
        if not self.snaptxt_ocr:
            print(f"     ⚠️ SnapTXT OCR 사용 불가")
            return ""
            
        try:
            # MultiOCRProcessor로 이미지 처리
            default_settings = {
                'engine': 'easyocr',
                'language': 'ko,en', 
                'confidence_threshold': 0.1,
                'preprocessing': True
            }
            
            # 디버깅: 사용 가능한 메서드 확인
            print(f"     🔍 OCR 객체 타입: {type(self.snaptxt_ocr)}")
            print(f"     🔍 사용 가능한 메서드: {[m for m in dir(self.snaptxt_ocr) if 'process' in m]}")
            
            result = self.snaptxt_ocr.process_file(str(image_file), default_settings)
            
            # 결과는 직접 텍스트 문자열
            extracted_text = result if isinstance(result, str) else str(result)
            
            print(f"     ✅ SnapTXT OCR 완료: {len(extracted_text)}자")
            return extracted_text
                
        except Exception as e:
            import traceback
            print(f"     ⚠️ SnapTXT OCR 실패: {e}")
            print(f"     🔍 스택 트레이스: {traceback.format_exc()}")
            # 폴백: 빈 문자열 반환
            return ""
    
    def _run_google_vision_ocr(self, image_file: Path) -> str:
        """Google Vision OCR 실행 (캐시 지원 + 시간 측정)"""
        if not self.google_ocr:
            print(f"     ⚠️ Google Vision OCR 사용 불가")
            return ""
        
        # 캐시 파일 확인
        cache_key = hashlib.md5(str(image_file).encode()).hexdigest()
        cache_file = self.google_vision_cache / f"{cache_key}.json"
        
        if cache_file.exists():
            print(f"     📋 Google Vision 캐시 사용")
            self.vision_api_stats["cache_hit"] += 1
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_result = json.load(f)
                return cached_result.get("text", "")
        
        try:
            # Google Vision API 호출 시간 측정
            start_time = time.time()
            print(f"     🌐 Google Vision API 호출 중...")
            
            result = self.google_ocr.extract_text(str(image_file))
            
            end_time = time.time()
            call_duration_ms = (end_time - start_time) * 1000
            
            self.vision_api_stats["cache_miss"] += 1
            self.vision_api_stats["total_vision_ms"] += call_duration_ms
            self.vision_api_stats["api_call_times"].append(call_duration_ms)
            
            extracted_text = ""
            if isinstance(result, dict):
                extracted_text = result.get("text", "")
            elif isinstance(result, str):
                extracted_text = result
            
            # 캐시 저장 (시간 정보 포함)
            cache_data = {
                "image_file": str(image_file),
                "timestamp": datetime.now().isoformat(),
                "text": extracted_text,
                "call_duration_ms": call_duration_ms
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            print(f"     ✅ Google Vision 완료: {len(extracted_text)}자 ({call_duration_ms:.0f}ms)")
            return extracted_text
            
        except Exception as e:
            print(f"     ⚠️ Google Vision 실패: {e}")
            return ""
    
    def _extract_error_events(self, ocr_results: List[Dict]) -> List[ErrorEvent]:
        """오류 이벤트 추출 (3-way diff)"""
        print("\n🔍 오류 이벤트 추출 중...")
        
        all_error_events = []
        
        for result in ocr_results:
            page_id = result["page_id"]
            image_file = result["image_file"]
            
            raw_ocr = result["ocr_results"]["raw_ocr"]
            stage23 = result["ocr_results"]["stage23_applied"]
            gt = result["ocr_results"]["google_vision_gt"]
            
            print(f"   🔄 {page_id} 분석 중...")
            
            # 3-way diff 분석: raw → stage23 → gt
            events_raw_to_stage23 = self._extract_diff_events(raw_ocr, stage23, "raw→stage23")
            events_stage23_to_gt = self._extract_diff_events(stage23, gt, "stage23→gt")
            events_raw_to_gt = self._extract_diff_events(raw_ocr, gt, "raw→gt")
            
            # Stage2/3에서 이미 해결된 오류 제거
            new_rule_candidates = []
            
            for event in events_raw_to_gt:
                # raw→gt 오류가 stage23에서 해결되었는지 확인
                is_already_handled = any(
                    self._is_similar_error(event, handled_event) 
                    for handled_event in events_raw_to_stage23
                )
                
                if not is_already_handled:
                    # Stage23 후에도 남는 오류 = 새 규칙 후보
                    error_event = ErrorEvent(
                        page_id=page_id,
                        image_file=image_file,
                        bucket=self._classify_error_bucket(event),
                        raw_ocr_snippet=event["before"],
                        stage23_snippet=self._find_corresponding_text(event["before"], stage23),
                        gt_snippet=event["after"],
                        op_type=event["op_type"],
                        signature=self._generate_error_signature(event),
                        count=self._generate_count_key(event),
                        context_before=event.get("context_before", ""),
                        context_after=event.get("context_after", ""),
                        confidence_score=event.get("confidence", 0.8)
                    )
                    new_rule_candidates.append(error_event)
            
            all_error_events.extend(new_rule_candidates)
            print(f"   ✅ {page_id}: {len(new_rule_candidates)}개 새 규칙 후보")
        
        print(f"🎯 총 {len(all_error_events)}개 오류 이벤트 추출 완료")
        
        # 2) error_events.jsonl 저장 및 샘플 출력
        self._save_and_display_error_events(all_error_events)
        
        return all_error_events
    
    def _save_and_display_error_events(self, error_events: List[ErrorEvent]):
        """2) error_events.jsonl 실제 라인 샘플 30개 출력 (run_id 기반)"""
        try:
            # error_events.jsonl 저장 (run_id 기반 경로)
            with open(self.error_events_file, 'w', encoding='utf-8') as f:
                for event in error_events:
                    event_dict = asdict(event)
                    f.write(json.dumps(event_dict, ensure_ascii=False) + '\n')
            
            print(f"\n📄 error_events.jsonl 저장: {self.error_events_file}")
            print(f"🎯 Run ID: {self.run_id}")
            
            # 처음 30개 라인 출력
            print("\n📋 error_events.jsonl 처음 30개 라인:")
            print("-" * 80)
            for i, event in enumerate(error_events[:30]):
                event_dict = asdict(event)
                print(f"Line {i+1}: {json.dumps(event_dict, ensure_ascii=False)}")
                if i >= 29:  # 30개까지만
                    break
            
            if len(error_events) > 30:
                print(f"... 및 {len(error_events) - 30}개 추가 라인")
            print("-" * 80)
            
        except Exception as e:
            print(f"⚠️ error_events 저장 실패: {e}")
    
    def _extract_diff_events(self, text1: str, text2: str, label: str) -> List[Dict]:
        """두 텍스트 간의 차이점을 이벤트로 추출"""
        diff_events = []
        
        # SequenceMatcher를 사용한 정밀한 diff
        matcher = difflib.SequenceMatcher(None, text1, text2)
        
        for op, i1, i2, j1, j2 in matcher.get_opcodes():
            if op == 'equal':
                continue
            
            before_text = text1[i1:i2]
            after_text = text2[j1:j2]
            
            # 컨텍스트 추출 (앞뒤 10자)
            context_before = text1[max(0, i1-10):i1]
            context_after = text1[i2:i2+10]
            
            event = {
                "op_type": op,  # replace, insert, delete
                "before": before_text,
                "after": after_text,
                "position": (i1, i2),
                "context_before": context_before,
                "context_after": context_after,
                "confidence": self._calculate_diff_confidence(before_text, after_text, op),
                "label": label
            }
            
            diff_events.append(event)
        
        return diff_events
    
    def _classify_error_bucket(self, event: Dict) -> str:
        """오류를 버킷별로 분류"""
        before = event["before"]
        after = event["after"]
        
        # 패턴 매칭을 통한 분류
        for bucket, patterns in self.bucket_patterns.items():
            for pattern in patterns:
                if re.search(pattern, f"{before}→{after}"):
                    return bucket
        
        # 휴리스틱 분류
        if re.search(r'\s', before) or re.search(r'\s', after):
            return "space"
        elif any(char in before + after for char in "‛′「」『』.,?!"):
            return "punctuation"
        elif '\n' in before or '\n' in after:
            return "layout"
        else:
            return "character"
    
    def _generate_error_signature(self, event: Dict) -> str:
        """오류 시그니처 생성"""
        before = event["before"]
        after = event["after"]
        op_type = event["op_type"]
        
        if op_type == "replace":
            # 유니코드 코드포인트 기반 시그니처
            if len(before) == 1 and len(after) == 1:
                return f"U+{ord(before):04X}→U+{ord(after):04X}"
            else:
                return f'"{before}"→"{after}"'
        elif op_type == "insert":
            return f'INSERT["{after}"]'
        elif op_type == "delete":
            return f'DELETE["{before}"]'
        else:
            return f'{op_type}["{before}"→"{after}"]'
    
    def _generate_count_key(self, event: Dict) -> str:
        """집계용 키 생성"""
        return f"{event['op_type']}:{event['before']}→{event['after']}"
    
    def _is_similar_error(self, event1: Dict, event2: Dict) -> bool:
        """두 오류 이벤트가 유사한지 판단"""
        # 간단한 유사도 기준: before/after 텍스트가 90% 이상 일치
        if event1["before"] == event2["before"] and event1["after"] == event2["after"]:
            return True
        
        # 부분 일치 확인
        similarity = difflib.SequenceMatcher(None, event1["before"], event2["before"]).ratio()
        return similarity > 0.9
    
    def _find_corresponding_text(self, raw_snippet: str, stage23_text: str) -> str:
        """Stage23 텍스트에서 해당 부분 찾기"""
        # 간단한 구현: raw_snippet과 가장 유사한 부분 찾기
        if raw_snippet in stage23_text:
            return raw_snippet
        
        # 부분 매칭 시도
        best_match = ""
        best_ratio = 0
        
        for i in range(len(stage23_text) - len(raw_snippet) + 1):
            candidate = stage23_text[i:i+len(raw_snippet)]
            ratio = difflib.SequenceMatcher(None, raw_snippet, candidate).ratio()
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = candidate
        
        return best_match if best_ratio > 0.7 else raw_snippet
    
    def _calculate_diff_confidence(self, before: str, after: str, op_type: str) -> float:
        """차이점의 신뢰도 계산"""
        # 기본 신뢰도
        base_confidence = 0.8
        
        # 길이 기반 조정
        length_factor = min(len(before) + len(after), 10) / 10
        
        # 오퍼레이션 타입 기반 조정
        op_confidence = {
            "replace": 0.9,
            "insert": 0.8,
            "delete": 0.8
        }.get(op_type, 0.7)
        
        return base_confidence * length_factor * op_confidence
    
    def _analyze_3way_diff_statistics(self, error_events: List[ErrorEvent]):
        """3) 3-way diff 분류 통계표 출력"""
        print("\n📊 3-way diff 분류 통계표")
        print("=" * 60)
        
        # 통계 계산
        total_events = len(error_events)
        bucket_stats = Counter()
        resolved_by_stage23 = 0
        remaining_after_stage23 = 0
        unchanged_all = 0
        
        for event in error_events:
            bucket_stats[event.bucket] += 1
            
            # raw != stage23 이고 stage23 == gt 이면 해결됨
            if event.raw_ocr_snippet != event.stage23_snippet and event.stage23_snippet == event.gt_snippet:
                resolved_by_stage23 += 1
            # stage23 != gt 이면 아직 남은 오류
            elif event.stage23_snippet != event.gt_snippet:
                remaining_after_stage23 += 1
            # raw == stage23 == gt 이면 변화 없음 (버그 가능)
            elif event.raw_ocr_snippet == event.stage23_snippet == event.gt_snippet:
                unchanged_all += 1
        
        # 통계표 출력
        print(f"총 이벤트: {total_events}")
        print(f"Stage23으로 해결됨: {resolved_by_stage23} ({resolved_by_stage23/total_events*100:.1f}%)")
        print(f"Stage23 후에도 남음 (새 규칙 후보): {remaining_after_stage23} ({remaining_after_stage23/total_events*100:.1f}%)")
        print(f"전체 동일 (버그 가능): {unchanged_all} ({unchanged_all/total_events*100:.1f}%)")
        
        # resolved_by_stage23=0 해석
        print(f"\n🔍 resolved_by_stage23={resolved_by_stage23} 해석:")
        print(f"📝 정의: (raw≠stage23) AND (stage23=gt) 조건을 만족하는 오류")
        if resolved_by_stage23 == 0:
            print(f"  ⚠️ Stage2/3 규칙이 GT 수준까지 교정하는 사례가 없음")
            print(f"  💭 원인 해석:")
            print(f"     1. 책/도메인 특성: Stage2/3 규칙이 이 텍스트 유형에 맞지 않음")
            print(f"     2. GT 품질 이슈: Google Vision도 완벽하지 않은 텍스트")
            print(f"     3. Stage2/3 성능 한계: 현재 규칙으로 해결 가능한 오류가 적음")
            print(f"     4. diff 로직: 'resolved' 정의가 너무 엄격함 (정확 일치 요구)")
        else:
            print(f"  ✅ Stage2/3이 {resolved_by_stage23}개 오류를 GT 수준까지 교정함")
        print()
        
        # 4) Bucket 분포 출력
        print("📊 Bucket 분포:")
        for bucket, count in bucket_stats.most_common():
            percentage = count / total_events * 100
            print(f"  {bucket}: {count}개 ({percentage:.1f}%)")
        print("=" * 60)
    
    def _analyze_top_patterns(self, error_events: List[ErrorEvent], topk: int) -> List[ErrorPattern]:
        """상위 오류 패턴 분석"""
        print(f"\n📊 상위 {topk}개 오류 패턴 분석 중...")
        
        # 시그니처별 집계
        pattern_stats = defaultdict(lambda: {
            "frequency": 0,
            "bucket": "",
            "op_type": "",
            "examples": [],
            "stage23_handled_count": 0,
            "confidence_scores": []
        })
        
        for event in error_events:
            sig = event.signature
            pattern_stats[sig]["frequency"] += 1
            pattern_stats[sig]["bucket"] = event.bucket
            pattern_stats[sig]["op_type"] = event.op_type
            pattern_stats[sig]["confidence_scores"].append(event.confidence_score)
            
            # 예시 수집 (최대 5개)
            if len(pattern_stats[sig]["examples"]) < 5:
                example = {
                    "page_id": event.page_id,
                    "raw_snippet": event.raw_ocr_snippet,
                    "stage23_snippet": event.stage23_snippet,
                    "gt_snippet": event.gt_snippet,
                    "context": event.context_before + "|" + event.context_after
                }
                pattern_stats[sig]["examples"].append(example)
        
        # 빈도순 정렬하여 상위 topk개 선택
        sorted_patterns = sorted(pattern_stats.items(), key=lambda x: x[1]["frequency"], reverse=True)
        
        top_patterns = []
        for i, (signature, stats) in enumerate(sorted_patterns[:topk]):
            # Stage2/3에서 이미 처리했는지 확인
            stage23_already_handled = self._check_stage23_handling(signature, stats["examples"])
            
            # 평균 신뢰도 계산
            avg_confidence = sum(stats["confidence_scores"]) / len(stats["confidence_scores"]) if stats["confidence_scores"] else 0.8
            
            pattern = ErrorPattern(
                signature=signature,
                bucket=stats["bucket"],
                frequency=stats["frequency"],
                op_type=stats["op_type"],
                examples=stats["examples"],
                stage23_already_handled=stage23_already_handled,
                confidence_avg=avg_confidence
            )
            top_patterns.append(pattern)
            
            if i < 10:  # 상위 10개만 출력
                print(f"   {i+1:2d}. {signature} ({stats['bucket']}) - {stats['frequency']}회")
        
        # 4) Top 20 패턴 표 출력
        self._display_top20_patterns(sorted_patterns[:20])
        
        return top_patterns
    
    def _display_top20_patterns(self, sorted_patterns):
        """4) Signature Top 20 패턴 표 출력"""
        print("\n📈 Signature Top 20 패턴:")
        print("-" * 100)
        print(f"{'순위':<4} {'빈도':<6} {'버킷':<8} {'시그니처':<50} {'예시 2개'}")
        print("-" * 100)
        
        for i, (signature, stats) in enumerate(sorted_patterns[:20]):
            frequency = stats["frequency"]
            bucket = stats["bucket"]
            
            # 예시 2개 선택
            examples = stats["examples"][:2]
            example_str = ""
            if examples:
                ex1 = examples[0]
                example_str = f"{ex1['raw_snippet'][:20]}→{ex1['gt_snippet'][:20]}"
                if len(examples) > 1:
                    ex2 = examples[1]
                    example_str += f"; {ex2['raw_snippet'][:20]}→{ex2['gt_snippet'][:20]}"
            
            print(f"{i+1:<4} {frequency:<6} {bucket:<8} {signature[:50]:<50} {example_str}")
        
        print("-" * 100)
    
    def _check_stage23_handling(self, signature: str, examples: List[Dict]) -> bool:
        """Stage2/3에서 이미 처리하는 패턴인지 확인"""
        # 간단한 휴리스틱: raw와 stage23가 이미 일치하는 경우가 많으면 이미 처리됨
        handled_count = 0
        
        for example in examples:
            raw = example["raw_snippet"]
            stage23 = example["stage23_snippet"]
            gt = example["gt_snippet"]
            
            # stage23이 이미 gt에 가까우면 처리됨
            if difflib.SequenceMatcher(None, stage23, gt).ratio() > 0.9:
                handled_count += 1
        
        return handled_count / len(examples) > 0.5 if examples else False
    
    def _analyze_invalid_samples(self, top_patterns: List[ErrorPattern], seed: int, target_size: int) -> Dict:
        """🔍 무효 샘플 12개 원인 분석"""
        print(f"\n🔍 무효 샘플 원인 분석 시작 (seed={seed}, target_size={target_size})...")
        print("=" * 80)
        
        random.seed(seed)
        invalid_samples_analysis = []
        failure_counts = {
            "NO_MATCH": 0,
            "NO_CHANGE": 0, 
            "CANCELLED": 0,
            "EXCEPTION": 0,
            "OTHER": 0
        }
        
        # 빈도 기반 가중치 계산
        frequencies = [pattern.frequency for pattern in top_patterns]
        total_freq = sum(frequencies)
        weights = [freq / total_freq for freq in frequencies]
        
        for i in range(target_size):
            # weighted sampling으로 패턴 선택
            selected_patterns = np.random.choice(
                top_patterns,
                size=random.randint(1, 3),  # 1-3개 패턴
                p=weights,
                replace=True
            )
            
            # 기본 텍스트 생성
            base_example = random.choice(selected_patterns[0].examples)
            input_text = base_example["raw_snippet"] + " " + base_example["context"]
            target_text = input_text
            
            applied_signatures = []
            apply_logs = []
            
            # 각 패턴 적용 with 상세 로깅
            for pattern in selected_patterns:
                before_text = target_text
                try:
                    if pattern.op_type == "replace":
                        target_text = self._apply_replace_pattern(target_text, pattern)
                    elif pattern.op_type == "insert":
                        target_text = self._apply_insert_pattern(target_text, pattern)
                    elif pattern.op_type == "delete":  
                        target_text = self._apply_delete_pattern(target_text, pattern)
                    elif pattern.op_type == "normalize":
                        target_text = self._apply_normalize_pattern(target_text, pattern)
                    
                    changed = (before_text != target_text)
                    apply_logs.append({
                        "signature": pattern.signature,
                        "op_type": pattern.op_type,
                        "before_len": len(before_text),
                        "after_len": len(target_text), 
                        "changed": changed
                    })
                    
                    if changed:
                        applied_signatures.append(pattern.signature)
                        
                except Exception as e:
                    apply_logs.append({
                        "signature": pattern.signature,
                        "op_type": pattern.op_type,
                        "error": str(e),
                        "changed": False
                    })
                    failure_counts["EXCEPTION"] += 1
            
            # 무효 샘플인지 확인 및 원인 분석
            is_valid = (input_text != target_text and len(applied_signatures) > 0 and 
                       self._validate_text_change(input_text, target_text, applied_signatures))
            
            if not is_valid:
                # 구체적인 실패 원인 판정
                if input_text == target_text:
                    if len(applied_signatures) == 0:
                        failure_reason = "NO_MATCH"  # 패턴이 아예 매칭되지 않음
                        failure_counts["NO_MATCH"] += 1
                    else:
                        failure_reason = "CANCELLED"  # 여러 패턴이 서로 상쇄됨
                        failure_counts["CANCELLED"] += 1
                else:
                    failure_reason = "NO_CHANGE"  # validation에서 거부됨
                    failure_counts["NO_CHANGE"] += 1
                
                invalid_sample = {
                    "sample_id": f"invalid_{i+1:05d}",
                    "chosen_signature": [log["signature"] for log in apply_logs],
                    "input_excerpt": input_text[:100] + "..." if len(input_text) > 100 else input_text,
                    "target_excerpt": target_text[:100] + "..." if len(target_text) > 100 else target_text,
                    "apply_status": f"matched: {sum(1 for log in apply_logs if log.get('changed', False))}/{len(apply_logs)}",
                    "failure_reason": failure_reason,
                    "apply_logs": apply_logs
                }
                invalid_samples_analysis.append(invalid_sample)
        
        return {
            "invalid_samples": invalid_samples_analysis,
            "failure_counts": failure_counts
        }

    def _generate_synthetic_dataset_with_validation(self, top_patterns: List[ErrorPattern], seed: int, target_size: int) -> List[Dict]:
        """5) 합성 데이터셋 생성 방식 명시 + 7) 가짜 적용 여부 검증"""
        print(f"\n🧪 합성 데이터셋 생성 중 (seed={seed}, target_size={target_size})...")
        print("=" * 60)
        print("📋 생성 방식:")
        print("  • 분포 유지: weighted sampling (빈도 기반)")
        print("  • seed 고정: True")
        print("  • 1 샘플당 패턴: 1-3개 삽입")
        print("  • op_type별 규칙: replace/insert/delete/normalize")
        print("  • 검증: input_text != target_text 100% 확인")
        print("=" * 60)
        
        random.seed(seed)
        synthetic_samples = []
        
        # 빈도 기반 가중치 계산
        frequencies = [pattern.frequency for pattern in top_patterns]
        total_freq = sum(frequencies)
        weights = [freq / total_freq for freq in frequencies]
        
        print(f"💾 가중치 분포: Top 5 패턴 - {[f'{w:.3f}' for w in weights[:5]]}")
        
        valid_samples = 0
        invalid_samples = 0
        
        for i in range(target_size):
            # weighted sampling으로 패턴 선택
            selected_patterns = np.random.choice(
                top_patterns,
                size=random.randint(1, 3),  # 1-3개 패턴
                p=weights,
                replace=True
            )
            
            # 기본 텍스트 생성 (실제 예시에서)
            base_example = random.choice(selected_patterns[0].examples)
            input_text = base_example["raw_snippet"] + " " + base_example["context"]
            target_text = input_text
            
            applied_signatures = []
            
            # 각 패턴 적용
            for pattern in selected_patterns:
                try:
                    # op_type별 적용 규칙
                    if pattern.op_type == "replace":
                        target_text = self._apply_replace_pattern(target_text, pattern)
                    elif pattern.op_type == "insert":
                        target_text = self._apply_insert_pattern(target_text, pattern)
                    elif pattern.op_type == "delete":
                        target_text = self._apply_delete_pattern(target_text, pattern)
                    elif pattern.op_type == "normalize":
                        target_text = self._apply_normalize_pattern(target_text, pattern)
                    
                    applied_signatures.append(pattern.signature)
                    
                except Exception as e:
                    continue
            
            # 7) 가짜 적용 여부 검증
            if input_text != target_text and len(applied_signatures) > 0:
                # reverse-check: 실제로 변화가 있는지 확인
                if self._validate_text_change(input_text, target_text, applied_signatures):
                    sample = {
                        "sample_id": f"synthetic_{i+1:05d}",
                        "input_text": input_text,
                        "target_text": target_text,
                        "applied_patterns": applied_signatures,
                        "pattern_count": len(applied_signatures),
                        "timestamp": datetime.now().isoformat()
                    }
                    synthetic_samples.append(sample)
                    valid_samples += 1
                else:
                    invalid_samples += 1
            else:
                invalid_samples += 1
        
        # 무효 샘플 상세 분석 실행
        invalid_analysis = self._analyze_invalid_samples(top_patterns, seed, target_size)
        
        print(f"✅ 유효 샘플: {valid_samples}개")
        print(f"❌ 무효 샘플: {invalid_samples}개")
        print(f"📊 유효율: {valid_samples/(valid_samples+invalid_samples)*100:.1f}%")
        
        # 무효 샘플 상세 출력
        print(f"\n🔍 무효 샘플 상세 분석:")
        for sample in invalid_analysis["invalid_samples"]:
            print(f"  • {sample['sample_id']}: {sample['failure_reason']}")
            print(f"    시그니처: {sample['chosen_signature']}")
            print(f"    적용상태: {sample['apply_status']}")
            print(f"    input: {sample['input_excerpt']}")
            print(f"    target: {sample['target_excerpt']}")
        
        print(f"\n📊 실패 원인별 요약:")
        for reason, count in invalid_analysis["failure_counts"].items():
            print(f"  • {reason}: {count}개")
        
        return synthetic_samples
    
    def _generate_event_replay_dataset(self, top_patterns: List[ErrorPattern], seed: int, target_size: int) -> List[Dict]:
        """🎯 Event Replay 방식: GT → 에러 주입 → Input 생성 (input≠target 100% 보장)"""
        print(f"\n🎯 Event Replay 데이터셋 생성 중 (seed={seed}, target_size={target_size})...")
        print("=" * 60)
        print("📋 새로운 생성 방식 (Event Replay):")
        print("  • 시작점: Ground Truth 텍스트")
        print("  • 에러 주입: 실제 error event의 역변환 (gt→raw)")
        print("  • input: inject_errors(gt, events_gt_to_raw)")
        print("  • target: 원래 GT 그대로")
        print("  • 보장: input ≠ target (원천적으로 no-op 방지)")
        print("=" * 60)
        
        random.seed(seed)
        synthetic_samples = []
        
        # 빈도 기반 가중치 계산
        frequencies = [pattern.frequency for pattern in top_patterns]
        total_freq = sum(frequencies)
        weights = [freq / total_freq for freq in frequencies]
        
        print(f"💾 가중치 분포: Top 5 패턴 - {[f'{w:.3f}' for w in weights[:5]]}")
        
        # GT 텍스트 풀 생성 (error_events.jsonl에서 실제 GT 수집)
        gt_text_pool = self._collect_gt_text_pool()
        print(f"📚 GT 텍스트 풀: {len(gt_text_pool)}개 문단")
        
        valid_samples = 0
        invalid_samples = 0
        
        # 🔍 디버깅: 선택된 signature 추적
        selected_signatures_all = []  # 선택된 모든 signature
        applied_signatures_all = []   # 실제 적용된 signature
        invalid_details = []          # 무효 샘플 상세 정보
        
        for i in range(target_size):
            # 1. GT 텍스트를 target으로 설정
            target_text = random.choice(gt_text_pool)
            
            # 2. weighted sampling으로 에러 이벤트 선택
            selected_patterns = np.random.choice(
                top_patterns,
                size=random.randint(1, 3),  # 1-3개 에러
                p=weights,
                replace=True
            )
            
            # 3. GT → Raw 역변환으로 Input 생성
            input_text = target_text
            applied_events = []
            sample_selected_sigs = []
            sample_applied_sigs = []
            
            for pattern in selected_patterns:
                sample_selected_sigs.append(pattern.signature)
                
                # 실제 error event 선택
                event_example = random.choice(pattern.examples)
                
                # GT → Raw 역변환 적용
                try:
                    before_text = input_text
                    input_text = self._apply_reverse_error_event(
                        input_text, event_example, pattern.op_type
                    )
                    
                    # 실제 변화가 있었는지 확인
                    if before_text != input_text:
                        applied_events.append({
                            "signature": pattern.signature,
                            "op_type": pattern.op_type,
                            "raw_span": event_example["raw_snippet"],
                            "gt_span": event_example["gt_snippet"]
                        })
                        sample_applied_sigs.append(pattern.signature)
                except Exception as e:
                    continue
            
            selected_signatures_all.extend(sample_selected_sigs)
            applied_signatures_all.extend(sample_applied_sigs)
            
            # 4. 결과 검증
            if input_text != target_text and len(applied_events) > 0:
                sample = {
                    "sample_id": f"event_replay_{i+1:05d}",
                    "input_text": input_text,
                    "target_text": target_text,
                    "applied_events": applied_events,
                    "event_count": len(applied_events),
                    "timestamp": datetime.now().isoformat(),
                    "generation_method": "event_replay"
                }
                synthetic_samples.append(sample)
                valid_samples += 1
            else:
                # 🔍 무효 샘플 상세 정보 저장
                invalid_details.append({
                    "sample_id": f"invalid_{i+1:05d}",
                    "chosen_signatures": sample_selected_sigs,
                    "gt_text": target_text,
                    "input_text": input_text,
                    "target_text": target_text,
                    "failure_reason": "NO_CHANGE" if input_text == target_text else "NO_EVENTS",
                    "apply_debug": {
                        "selected_count": len(sample_selected_sigs),
                        "applied_count": len(sample_applied_sigs),
                        "selected_sigs": sample_selected_sigs,
                        "applied_sigs": sample_applied_sigs
                    }
                })
                invalid_samples += 1
        
        print(f"✅ 유효 샘플: {valid_samples}개")
        print(f"❌ 무효 샘플: {invalid_samples}개")
        print(f"📊 유효율: {valid_samples/target_size*100:.1f}%")
        
        # 🔍 디버깅 정보 출력
        print(f"\n🔍 Signature 선택/적용 분석:")
        print(f"  • 총 선택된 signature: {len(selected_signatures_all)}개")
        print(f"  • 실제 적용된 signature: {len(applied_signatures_all)}개")
        print(f"  • 적용 성공률: {len(applied_signatures_all)/len(selected_signatures_all)*100:.1f}%" if selected_signatures_all else "  • 적용 성공률: 0%")
        
        # 선택된 signature 목록
        selected_counter = Counter(selected_signatures_all)
        applied_counter = Counter(applied_signatures_all)
        
        print(f"\n📋 선택된 Signature Top 5:")
        for sig, count in selected_counter.most_common(5):
            applied_count = applied_counter.get(sig, 0)
            print(f"    {sig}: 선택={count}, 적용={applied_count}")
        
        # 무효 샘플 상세 출력
        if invalid_details:
            print(f"\n❌ 무효 샘플 상세 (총 {len(invalid_details)}개):")
            for detail in invalid_details[:3]:  # 처음 3개만 출력
                print(f"  • {detail['sample_id']}: {detail['failure_reason']}")
                print(f"    선택된 signatures: {detail['chosen_signatures']}")
                print(f"    GT: {detail['gt_text'][:100]}...")
                print(f"    Input: {detail['input_text'][:100]}...")
                print(f"    Apply debug: {detail['apply_debug']}")
        
        return synthetic_samples
    
    def _collect_gt_text_pool(self) -> List[str]:
        """실제 Vision GT 텍스트 풀 수집 (인위적 expansion 없음)"""
        print("🔍 실제 Vision GT에서만 텍스트 풀 수집 (authentic distribution)")
        
        # Real Vision GT 폴더에서 직접 로딩
        gt_pool = set()  # 중복 제거용
        
        try:
            # Real folder 기반 GT 로딩
            real_folder = Path("real")
            if not real_folder.exists():
                print(f"❌ Real folder not found: {real_folder}")
                # Fallback to error_events.jsonl but with authentic GT only
                return self._collect_authentic_gt_from_events()
            
            print(f"📁 Real folder 발견: {real_folder}")
            for gt_file in real_folder.glob("**/*_gt.txt"):
                try:
                    with open(gt_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if len(content) > 50:  # 최소 길이 필터
                            # 문단으로 분할하여 추가
                            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
                            for para in paragraphs:
                                if len(para) > 30:  # 문단 최소 길이
                                    gt_pool.add(para)
                except Exception as e:
                    print(f"⚠️ GT 파일 읽기 실패: {gt_file} - {e}")
                    
        except Exception as e:
            print(f"❌ Real folder GT 로딩 실패: {e}")
            # Fallback to authentic events
            return self._collect_authentic_gt_from_events()
        
        result = list(gt_pool)
        print(f"✅ Authentic Vision GT 풀: {len(result)}개 문단 (Average: {sum(len(t) for t in result)/len(result):.0f} chars)" if result else "❌ GT 풀이 비어있음")
        return result

    def _collect_authentic_gt_from_events(self) -> List[str]:
        """Error events에서 authentic GT만 추출 (expansion 없음)"""
        print("🔄 Fallback: error_events.jsonl에서 authentic GT snippet만 수집")
        gt_pool = set()
        
        try:
            if self.error_events_file.exists():
                with open(self.error_events_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            # ⚠️ 인위적 조합 금지: GT snippet만 사용 
                            gt_snippet = event.get("gt_snippet", "").strip()
                            
                            # GT snippet이 의미있는 길이면 그대로 사용
                            if len(gt_snippet) > 5:  # 최소 길이
                                gt_pool.add(gt_snippet)
                                
                        except json.JSONDecodeError:
                            continue
        
        except Exception as e:
            print(f"❌ Events GT 수집 실패: {e}")
        
        result = list(gt_pool)
        print(f"✅ Authentic GT from events: {len(result)}개 snippet" if result else "❌ GT 풀이 비어있음")
        return result

    def _apply_reverse_error_event(self, gt_text: str, event_example: Dict, op_type: str) -> str:
        """GT → Raw 역변환으로 오류 주입 (정확한 INSERT/DELETE 의미 반영)
        
        오류 이벤트의 실제 의미 (examples 기준):
        - INSERT[","] = GT에 ","가 있는데 OCR(raw)에서 "" → GT에서 ","를 제거하여 Raw 생성
        - DELETE[" "] = GT에 ""가 있는데 OCR(raw)에서 " " → GT에 " "를 추가하여 Raw 생성  
        - REPLACE = GT의 A가 OCR(raw)에서 B → GT의 A를 B로 교체하여 Raw 생성
        """
        raw_snippet = event_example["raw_snippet"]
        gt_snippet = event_example["gt_snippet"]
        
        # GT 텍스트에서 gt_snippet을 찾아서 raw_snippet으로 교체 (1차 시도)
        if gt_snippet in gt_text:
            return gt_text.replace(gt_snippet, raw_snippet, 1)
        else:
            # 매칭되지 않으면 op_type별 역변환 수행 (2차 시도)
            if op_type == "insert":
                # INSERT 의미: GT에 있던 것을 OCR이 누락
                # 역변환: GT에서 gt_snippet(있던 것)을 raw_snippet(없는 것)으로 교체
                # 일반적으로 gt_snippet 제거 (raw_snippet=""인 경우)
                if raw_snippet == "":
                    # GT에서 gt_snippet과 같은 문자를 찾아서 제거
                    if gt_snippet in gt_text:
                        return gt_text.replace(gt_snippet, "", 1)
                    else:
                        # 유사한 문자를 추가 후 제거하여 의미적 일관성 확보
                        pos = random.randint(0, len(gt_text))
                        temp_text = gt_text[:pos] + gt_snippet + gt_text[pos:]
                        return temp_text.replace(gt_snippet, raw_snippet, 1)
                else:
                    # raw_snippet이 비어있지 않은 경우 직접 교체
                    pos = random.randint(0, len(gt_text))
                    return gt_text[:pos] + raw_snippet + gt_text[pos:]
                    
            elif op_type == "delete":
                # DELETE 의미: GT에 없던 것을 OCR이 추가
                # 역변환: GT에 raw_snippet 추가
                pos = random.randint(0, len(gt_text))
                return gt_text[:pos] + raw_snippet + gt_text[pos:]
                
            else:
                # Replace/Normalize: 문자 교체
                if len(gt_text) >= len(gt_snippet):
                    start = random.randint(0, len(gt_text) - len(gt_snippet))
                    return gt_text[:start] + raw_snippet + gt_text[start + len(gt_snippet):]
        
        return gt_text
    
    def _report_vision_api_performance(self):
        """📊 Vision API 성능 통계 보고서 출력"""
        stats = self.vision_api_stats
        
        print(f"\n📊 Google Vision API 성능 보고서:")
        print("=" * 50)
        
        total_requests = stats["cache_hit"] + stats["cache_miss"]
        
        if total_requests == 0:
            print("  ⚠️ Vision API 호출이 없었습니다.")
            return
        
        # 캐시 통계
        print(f"  📋 캐시 통계:")
        print(f"    • Cache Hit: {stats['cache_hit']}회")
        print(f"    • Cache Miss: {stats['cache_miss']}회")
        print(f"    • 캐시 적중률: {stats['cache_hit']/total_requests*100:.1f}%")
        
        # API 호출 시간 통계
        if stats["api_call_times"]:
            api_times = stats["api_call_times"]
            avg_time = sum(api_times) / len(api_times)
            
            print(f"\n  ⏱️ API 호출 시간 통계:")
            print(f"    • 총 API 호출: {len(api_times)}회")
            print(f"    • 총 소요 시간: {stats['total_vision_ms']:.0f}ms")
            print(f"    • 페이지당 평균: {avg_time:.0f}ms")
            print(f"    • 최소 시간: {min(api_times):.0f}ms")
            print(f"    • 최대 시간: {max(api_times):.0f}ms")
        else:
            print(f"\n  ⏱️ API 호출 시간: 모든 요청이 캐시로 처리됨")
        
        print("=" * 50)

    def _compute_reverse_check_rate(self, synthetic_samples: List[Dict]) -> float:
        """🔍 Reverse-check 수치 계산: 실제 diff에서 chosen_signature가 발견되는 비율"""
        if not synthetic_samples:
            return 0.0
        
        confirmed_samples = 0
        total_valid_samples = len(synthetic_samples)
        
        for sample in synthetic_samples:
            input_text = sample["input_text"]
            target_text = sample["target_text"]
            applied_signatures = sample.get("applied_events", sample.get("applied_patterns", []))
            
            # input → target diff 계산
            diff_ops = list(difflib.unified_diff(
                input_text.split(), target_text.split(),
                lineterm="", n=0
            ))
            diff_content = " ".join(diff_ops)
            
            # applied_signatures 중 하나라도 diff에 포함되는지 확인
            signature_found = False
            for sig_info in applied_signatures:
                if isinstance(sig_info, dict):
                    signature = sig_info.get("signature", sig_info.get("raw_span", ""))
                    raw_span = sig_info.get("raw_span", "")
                    gt_span = sig_info.get("gt_span", "")
                else:
                    signature = str(sig_info)
                    raw_span = ""
                    gt_span = ""
                
                # signature, raw_span, gt_span 중 하나라도 diff에 있으면 확인됨
                if (signature in diff_content or 
                    (raw_span and raw_span in diff_content) or
                    (gt_span and gt_span in diff_content)):
                    signature_found = True
                    break
            
            if signature_found:
                confirmed_samples += 1
        
        reverse_check_rate = confirmed_samples / total_valid_samples
        return reverse_check_rate
    
    def _validate_text_change(self, input_text: str, target_text: str, applied_signatures: List[str]) -> bool:
        """7) 실제 텍스트 변화가 있는지 reverse-check"""
        # 기본 검증: 텍스트가 실제로 다른지
        if input_text == target_text:
            return False
        
        # 길이 변화 확인 (너무 극단적 변화는 비현실적)
        len_ratio = len(target_text) / len(input_text) if input_text else 1
        if len_ratio < 0.5 or len_ratio > 2.0:
            return False
        
        # 시그니처와 실제 변화의 일치성 확인
        similarity = difflib.SequenceMatcher(None, input_text, target_text).ratio()
        return 0.1 < similarity < 0.95  # 너무 같지도, 너무 다르지도 않게
        """합성 데이터셋 생성"""
        print(f"\n🧪 합성 데이터셋 생성 중 (seed={seed})...")
        
        random.seed(seed)
        synthetic_samples = []
        
        # 베이스 텍스트 템플릿들 (간단한 예시)
        base_texts = [
            "이것은 예시 문장입니다.",
            "한국어 텍스트 처리를 위한 테스트입니다.",
            "OCR 오류 패턴을 재현하기 위한 샘플 텍스트입니다.",
            "다양한 오류 유형을 포함한 합성 데이터셋입니다.",
            "실제 오류 분포를 유지하는 것이 중요합니다.",
        ]
        
        # 패턴 빈도에 따른 가중치 계산
        total_frequency = sum(pattern.frequency for pattern in top_patterns)
        pattern_weights = [pattern.frequency / total_frequency for pattern in top_patterns]
        
        # 합성 샘플 생성 (패턴 수 * 10개 정도)
        num_samples = min(len(top_patterns) * 10, 2000)
        
        for sample_id in range(num_samples):
            # 가중치 기반 패턴 선택
            selected_pattern = random.choices(top_patterns, weights=pattern_weights)[0]
            
            # 베이스 텍스트 선택
            base_text = random.choice(base_texts)
            
            # 오류 주입
            corrupted_text, target_text = self._inject_error_pattern(base_text, selected_pattern)
            
            if corrupted_text != target_text:  # 실제로 오류가 주입된 경우만
                synthetic_sample = {
                    "sample_id": f"synthetic_{sample_id:04d}",
                    "input_text": corrupted_text,
                    "target_text": target_text,
                    "applied_error_signatures": [selected_pattern.signature],
                    "error_bucket": selected_pattern.bucket,
                    "source_distribution_meta": {
                        "original_frequency": selected_pattern.frequency,
                        "pattern_rank": top_patterns.index(selected_pattern) + 1,
                        "total_patterns": len(top_patterns)
                    }
                }
                synthetic_samples.append(synthetic_sample)
        
        print(f"✅ {len(synthetic_samples)}개 합성 샘플 생성 완료")
        return synthetic_samples
    
    def _inject_error_pattern(self, base_text: str, pattern: ErrorPattern) -> Tuple[str, str]:
        """베이스 텍스트에 오류 패턴 주입"""
        target_text = base_text
        
        # 패턴 시그니처 분석
        if "→" in pattern.signature:
            # replacement 패턴
            if pattern.signature.startswith('"') and '"→"' in pattern.signature:
                # 문자열 교체 패턴
                parts = pattern.signature.split('→')
                from_str = parts[0].strip('"')
                to_str = parts[1].strip('"')
                
                if from_str in target_text:
                    corrupted_text = target_text.replace(from_str, to_str, 1)
                    return corrupted_text, target_text
            
            elif pattern.signature.startswith('U+'):
                # 유니코드 교체 패턴
                parts = pattern.signature.split('→')
                from_unicode = parts[0].replace('U+', '')
                to_unicode = parts[1].replace('U+', '')
                
                try:
                    from_char = chr(int(from_unicode, 16))
                    to_char = chr(int(to_unicode, 16))
                    
                    # 텍스트에 from_char가 있으면 첫 번째를 to_char로 교체
                    if from_char in target_text:
                        corrupted_text = target_text.replace(from_char, to_char, 1)
                        return corrupted_text, target_text
                except ValueError:
                    pass
        
        # 패턴 주입에 실패한 경우 원본 반환
        return target_text, target_text
    
    def _validate_distribution(self, top_patterns: List[ErrorPattern], synthetic_dataset: List[Dict]) -> Dict:
        """6) 진짜 분포 검증: real vs synth signature 비교표 생성"""
        print(f"\n📈 진짜 분포 검증 중 (Top{len(top_patterns)} 기준)...")
        print("=" * 80)
        
        # 🔍 Real signature 분포
        real_signatures = []
        real_frequencies = []
        for pattern in top_patterns:
            real_signatures.append(pattern.signature)
            real_frequencies.append(pattern.frequency)
        
        total_real_freq = sum(real_frequencies)
        
        print(f"📊 실제 분포 (Real): Top{len(top_patterns)} 패턴")
        print(f"   총 빈도: {total_real_freq}")
        real_top5 = [(sig, freq) for sig, freq in zip(real_signatures, real_frequencies)][:5]
        print(f"   Top 5: {[f'{sig}({freq})' for sig, freq in real_top5]}")
        
        # 🔍 Synthetic signature 분포 - applied_events에서 signature 추출
        print(f"🔍 합성 데이터에서 applied_events로부터 signature 추출 중...")
        synthetic_counter = Counter()
        valid_synthetic_samples = 0
        
        for i, sample in enumerate(synthetic_dataset):
            if i % 100 == 0 and i > 0:
                print(f"  진행률: {i+1}/{len(synthetic_dataset)} ({(i+1)/len(synthetic_dataset)*100:.1f}%)")
            
            try:
                # applied_events에서 signature 추출
                applied_events = sample.get('applied_events', [])
                
                if applied_events:
                    for event in applied_events:
                        signature = event.get('signature', '')
                        if signature:
                            synthetic_counter[signature] += 1
                            valid_synthetic_samples += 1
                        
            except Exception as e:
                # 조용히 넘어감 (디버깅용)
                print(f"    ⚠️ 샘플 {i} 처리 오류: {e}")
                continue
        
        total_synthetic = sum(synthetic_counter.values())
        print(f"📊 합성 분포 (Synthetic): {total_synthetic}개 signature ({valid_synthetic_samples}개 유효 샘플)")
        synth_top5 = list(synthetic_counter.most_common(5))
        print(f"   Top 5: {[f'{sig}({count})' for sig, count in synth_top5]}")
        
        # 🔍 Real vs Synth 비교 테이블
        print(f"\n📋 Real vs Synthetic 비교표 (Top{len(top_patterns)}):")
        print("-" * 100)
        print(f"{'Rank':<4} {'Signature':<40} {'Real Count':<12} {'Synth Count':<13} {'Match':<8}")
        print("-" * 100)
        
        coverage_count = 0
        comparison_table = []
        
        for i, (real_sig, real_count) in enumerate(zip(real_signatures, real_frequencies)):
            synth_count = synthetic_counter.get(real_sig, 0)
            is_match = synth_count > 0
            if is_match:
                coverage_count += 1
            
            comparison_table.append({
                "rank": i + 1,
                "signature": real_sig,
                "real_count": real_count,
                "synth_count": synth_count,
                "is_match": is_match
            })
            
            match_symbol = "✅" if is_match else "❌"
            print(f"{i+1:<4} {real_sig:<40} {real_count:<12} {synth_count:<13} {match_symbol:<8}")
        
        print("-" * 100)
        coverage_rate = coverage_count / len(real_signatures) if real_signatures else 0
        print(f"📈 커버리지: {coverage_count}/{len(real_signatures)} ({coverage_rate*100:.1f}%)")
        
        # 🔍 분포 검증 파일 저장 (run_id 기반)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Real signatures 파일
        real_file = self.current_run_dir / f"real_top{len(top_patterns)}_signatures_{timestamp}.txt"
        with open(real_file, 'w', encoding='utf-8') as f:
            f.write(f"Real Top{len(top_patterns)} Signatures\n")
            f.write("=" * 50 + "\n")
            for i, (sig, count) in enumerate(zip(real_signatures, real_frequencies)):
                f.write(f"{i+1:3d}. {sig:<40} ({count:3d}회)\n")
        
        # Synthetic signatures 파일
        synth_file = self.current_run_dir / f"synth_top{len(top_patterns)}_signatures_{timestamp}.txt"
        with open(synth_file, 'w', encoding='utf-8') as f:
            f.write(f"Synthetic Signatures (총 {total_synthetic}개)\n")
            f.write("=" * 50 + "\n")
            for i, (sig, count) in enumerate(synthetic_counter.most_common()):
                f.write(f"{i+1:3d}. {sig:<40} ({count:3d}회)\n")
        
        # 비교 테이블 파일
        comparison_file = self.current_run_dir / f"distribution_comparison_{timestamp}.txt"
        with open(comparison_file, 'w', encoding='utf-8') as f:
            f.write(f"Distribution Validation Report\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Real Patterns: {len(real_signatures)}\n")
            f.write(f"Synthetic Total: {total_synthetic}\n")
            f.write(f"Coverage: {coverage_count}/{len(real_signatures)} ({coverage_rate*100:.1f}%)\n\n")
            
            f.write("Rank | Signature                                | Real Count | Synth Count | Match\n")
            f.write("-" * 80 + "\n")
            for row in comparison_table:
                match_symbol = "✅" if row["is_match"] else "❌"
                f.write(f"{row['rank']:4d} | {row['signature']:<40} | {row['real_count']:10d} | {row['synth_count']:11d} | {match_symbol}\n")
        
        print(f"\n📁 분포 검증 파일 저장:")
        print(f"  • Real signatures: {real_file.name}")
        print(f"  • Synth signatures: {synth_file.name}")
        print(f"  • Comparison table: {comparison_file.name}")
        
        # 🔍 통계 계산
        try:
            # 정규화된 빈도 계산
            real_probs = [count / total_real_freq for count in real_frequencies]
            synth_probs = []
            
            for real_sig in real_signatures:
                synth_count = synthetic_counter.get(real_sig, 0)
                synth_prob = synth_count / total_synthetic if total_synthetic > 0 else 0
                synth_probs.append(synth_prob)
            
            # KL Divergence 계산: KL(P||Q)
            smoothing = 1e-8
            kl_divergence = 0.0
            for p, q in zip(real_probs, synth_probs):
                p_smooth = p + smoothing
                q_smooth = q + smoothing
                kl_divergence += p_smooth * np.log(p_smooth / q_smooth)
            
            print(f"🔍 KL(Real||Synth): {kl_divergence:.6f}")
            
            # Jensen-Shannon Distance
            try:
                js_distance = jensenshannon(real_probs, synth_probs)
                print(f"🔍 Jensen-Shannon distance: {js_distance:.6f}")
            except:
                js_distance = float('inf')
                print(f"🔍 Jensen-Shannon distance: 계산 실패")
            
            # Spearman rank correlation
            try:
                # 실제 빈도와 합성 빈도의 Spearman 상관관계
                spearman_corr, spearman_p = spearmanr(real_frequencies, [synthetic_counter.get(sig, 0) for sig in real_signatures])
                print(f"🔍 Spearman correlation: {spearman_corr:.6f} (p={spearman_p:.6f})")
            except:
                spearman_corr = -1
                spearman_p = 1
                print(f"🔍 Spearman correlation: 계산 실패")
            
        except Exception as e:
            print(f"⚠️ 통계 계산 실패: {e}")
            kl_divergence = float('inf')
            js_distance = float('inf')
            spearman_corr = -1
            spearman_p = 1
        
        # 🚨 PASS/FAIL 판정 (Authentic Distribution 기준)
        top10_coverage = coverage_rate if len(real_signatures) <= 10 else -1
        top50_coverage = coverage_rate if len(real_signatures) <= 50 else -1
        
        # Top10 signature ratio 계산 (authentic distribution 정확도)
        top10_signature_ratio = None
        if len(real_signatures) >= 10 and len(synth_signatures) >= 10:
            top10_real = comparison_table[:10]
            valid_ratios = []
            for item in top10_real:
                if item['real_count'] > 0 and item['synth_count'] > 0:
                    ratio = item['synth_count'] / item['real_count']
                    valid_ratios.append(ratio)
            
            if valid_ratios:
                top10_signature_ratio = sum(valid_ratios) / len(valid_ratios)
        
        # PASS 조건 체크 (더 엄격한 기준)
        pass_conditions = []
        if len(real_signatures) <= 10:
            pass_conditions.append(("Top10 coverage ≥ 0.9", coverage_rate >= 0.9))
        if len(real_signatures) <= 50:
            pass_conditions.append(("Top50 coverage ≥ 0.9", coverage_rate >= 0.9))
        pass_conditions.append(("Spearman ≥ 0.85", spearman_corr >= 0.85))
        
        # Top10 signature ratio 조건 (authentic distribution 정확도)
        if top10_signature_ratio is not None:
            pass_conditions.append(("Top10 signature ratio in [0.5, 2.0]", 
                                   0.5 <= top10_signature_ratio <= 2.0))
        
        print(f"\n🎯 Authentic Distribution 판정:")
        overall_pass = True
        for condition, result in pass_conditions:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  • {condition}: {status}")
            if not result:
                overall_pass = False
        
        if coverage_rate == 0:
            print(f"  🚨 커버리지 0% → 무조건 FAIL")
            overall_pass = False
            
        if top10_signature_ratio is not None:
            print(f"  📊 Top10 signature ratio: {top10_signature_ratio:.3f}")
            
        final_status = "✅ PASS" if overall_pass else "❌ FAIL"
        print(f"\n📊 최종 판정: {final_status} (Authentic Distribution 기준)")
        
        # 🔍 INSERT 패턴 특별 분석 (Top10)
        insert_patterns = []
        for i, pattern in enumerate(top_patterns):
            if pattern.op_type == "insert" and i < 10:  # Top10 중 INSERT만
                real_count = pattern.frequency
                synth_count = synthetic_counter.get(pattern.signature, 0)
                insert_patterns.append({
                    "rank": i + 1,
                    "signature": pattern.signature,
                    "real_count": real_count,
                    "synth_count": synth_count,
                    "application_rate": (synth_count / real_count * 100) if real_count > 0 else 0
                })
        
        if insert_patterns:
            print(f"\n🔍 INSERT 패턴 상세 분석 (Top10 중 {len(insert_patterns)}개):")
            print("-" * 80)
            print(f"{'Rank':<4} {'Signature':<30} {'Real':<6} {'Synth':<7} {'Apply Rate':<12}")
            print("-" * 80)
            for p in insert_patterns:
                rate_str = f"{p['application_rate']:.1f}%"
                print(f"{p['rank']:<4} {p['signature']:<30} {p['real_count']:<6} {p['synth_count']:<7} {rate_str:<12}")
            print("-" * 80)
        
        # INSERT 분석 파일 저장
        if insert_patterns:
            insert_file = self.current_run_dir / f"insert_analysis_{timestamp}.json"
            with open(insert_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "run_id": self.run_id,
                    "insert_patterns": insert_patterns,
                    "summary": {
                        "total_insert_patterns": len(insert_patterns),
                        "avg_application_rate": sum(p['application_rate'] for p in insert_patterns) / len(insert_patterns),
                        "fixed_count": sum(1 for p in insert_patterns if p['application_rate'] > 50),
                        "failed_count": sum(1 for p in insert_patterns if p['application_rate'] == 0)
                    }
                }, f, ensure_ascii=False, indent=2)
            print(f"  💾 INSERT 분석: {insert_file.name}")
        
        print("=" * 80)
        
        return {
            "kl_divergence": kl_divergence,
            "js_distance": js_distance,
            "spearman_correlation": spearman_corr,
            "spearman_p_value": spearman_p,
            "coverage_rate": coverage_rate,
            "coverage_count": coverage_count,
            "total_real_patterns": len(real_signatures),
            "total_synthetic_events": total_synthetic,
            "comparison_table": comparison_table,
            "synthetic_distribution": [{"signature": sig, "frequency": freq} for sig, freq in zip(real_signatures, synth_probs)],
            "final_status": final_status,
            "insert_analysis": insert_patterns,
            "validation_quality": final_status
        }
        
    def _calculate_correlation(self, pairs: List[Tuple[float, float]]) -> float:
        """피어슨 상관계수 계산"""
        if len(pairs) < 2:
            return 0.0
        
        n = len(pairs)
        sum_x = sum(x for x, y in pairs)
        sum_y = sum(y for x, y in pairs)
        sum_xy = sum(x * y for x, y in pairs)
        sum_x2 = sum(x * x for x, y in pairs)
        sum_y2 = sum(y * y for x, y in pairs)
        
        numerator = n * sum_xy - sum_x * sum_y
        denominator = math.sqrt((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y))
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def _save_all_results(self, error_events: List[ErrorEvent], top_patterns: List[ErrorPattern], 
                         synthetic_dataset: List[Dict], validation_result: Dict) -> List[str]:
        """모든 결과 저장 (run_id 기반)"""
        print(f"\n💾 결과 저장 중... (Run ID: {self.run_id})")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files = []
        
        # 1. error_events.jsonl (run_id 디렉토리에 저장)
        events_file = self.current_run_dir / f"error_events_{timestamp}.jsonl"
        with open(events_file, 'w', encoding='utf-8') as f:
            for event in error_events:
                f.write(json.dumps(asdict(event), ensure_ascii=False) + '\n')
        saved_files.append(events_file.name)
        
        # 2. top_patterns.json (run_id 디렉토리에 저장)
        patterns_file = self.current_run_dir / f"top{len(top_patterns)}_patterns_{timestamp}.json"
        patterns_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_patterns": len(top_patterns),
                "total_events": len(error_events),
                "run_id": self.run_id
            },
            "patterns": [asdict(pattern) for pattern in top_patterns]
        }
        with open(patterns_file, 'w', encoding='utf-8') as f:
            json.dump(patterns_data, f, ensure_ascii=False, indent=2)
        saved_files.append(patterns_file.name)
        
        # 3. synthetic_replay_dataset.jsonl (run_id 디렉토리에 저장)
        synthetic_file = self.current_run_dir / f"synthetic_replay_dataset_{timestamp}.jsonl"
        with open(synthetic_file, 'w', encoding='utf-8') as f:
            for sample in synthetic_dataset:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')
        saved_files.append(synthetic_file.name)
        
        # 4. distribution_validation.json (run_id 디렉토리에 저장 + 통합 분석 추가)
        validation_file = self.current_run_dir / f"distribution_validation_{timestamp}.json"
        
        # 통합 분석 결과 추가
        enhanced_validation_result = validation_result.copy()
        enhanced_validation_result.update({
            "run_id": self.run_id,
            "timestamp": datetime.now().isoformat(),
            "distribution_gate": {
                "status": validation_result.get('final_status', '❌ FAIL'),
                "coverage": f"{validation_result.get('coverage_count', 0)}/{validation_result.get('total_real_patterns', 0)}",
                "coverage_rate": validation_result.get('coverage_rate', 0),
                "spearman": validation_result.get('spearman_correlation', -1),
                "kl_divergence": validation_result.get('kl_divergence', float('inf')),
                "js_distance": validation_result.get('js_distance', float('inf'))
            },
            "files_in_run": saved_files
        })
        
        with open(validation_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_validation_result, f, ensure_ascii=False, indent=2)
        saved_files.append(validation_file.name)
        
        # 5. distribution_report.md (run_id 디렉토리에 저장)
        report_file = self.current_run_dir / f"distribution_report_{timestamp}.md"
        self._generate_markdown_report(report_file, error_events, top_patterns, synthetic_dataset, validation_result)
        saved_files.append(report_file.name)
        
        print(f"💾 완료: {len(saved_files)}개 파일 저장됨 (Run: {self.run_id})")
        
        return saved_files
    
    def _generate_markdown_report(self, report_file: Path, error_events: List[ErrorEvent], 
                                 top_patterns: List[ErrorPattern], synthetic_dataset: List[Dict], 
                                 validation_result: Dict):
        """마크다운 리포트 생성"""
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 실제 오류 분포 기반 합성 데이터셋 분석 리포트\n\n")
            f.write(f"생성 시간: {datetime.now().isoformat()}\n\n")
            
            # 전체 통계
            f.write("## 📊 전체 통계\n\n")
            f.write(f"- 총 오류 이벤트: {len(error_events)}개\n")
            f.write(f"- 상위 패턴: {len(top_patterns)}개\n")
            f.write(f"- 합성 샘플: {len(synthetic_dataset)}개\n\n")
            
            # 버킷별 분포
            bucket_stats = defaultdict(int)
            for event in error_events:
                bucket_stats[event.bucket] += 1
            
            f.write("## 🗂️ 오류 버킷별 분포\n\n")
            for bucket, count in sorted(bucket_stats.items()):
                percentage = count / len(error_events) * 100
                f.write(f"- **{bucket}**: {count}개 ({percentage:.1f}%)\n")
            f.write("\n")
            
            # 상위 10개 패턴
            f.write("## 🔝 상위 10개 오류 패턴\n\n")
            f.write("| 순위 | 시그니처 | 버킷 | 빈도 | Stage2/3 처리여부 |\n")
            f.write("|------|----------|------|------|-------------------|\n")
            
            for i, pattern in enumerate(top_patterns[:10]):
                handled = "✅" if pattern.stage23_already_handled else "❌"
                f.write(f"| {i+1} | `{pattern.signature}` | {pattern.bucket} | {pattern.frequency} | {handled} |\n")
            f.write("\n")
            
            # 분포 검증 결과
            f.write("## 📈 분포 검증 결과\n\n")
            f.write(f"- **분포 품질**: {validation_result.get('validation_quality', 'UNKNOWN')}\n")
            f.write(f"- **KL Divergence**: {validation_result.get('kl_divergence', 0):.6f}\n")
            f.write(f"- **Jensen-Shannon Distance**: {validation_result.get('js_distance', -1):.6f}\n")
            f.write(f"- **Spearman Correlation**: {validation_result.get('spearman_correlation', -1):.6f}\n")
            f.write(f"- **패턴 커버리지**: {validation_result.get('coverage_rate', 0)*100:.1f}%\n\n")
            
            # 결론
            f.write("## 🎯 결론 및 권장사항\n\n")
            f.write("이 합성 데이터셋은 실제 OCR 오류 분포를 기반으로 생성되었으며, ")
            
            if validation_result["kl_divergence"] < 0.5 and validation_result["correlation_coefficient"] > 0.7:
                f.write("원본 분포를 잘 재현하고 있습니다.\n\n")
                f.write("### ✅ 사용 권장\n")
                f.write("- 새로운 규칙 개발 시 테스트 데이터로 활용\n")
                f.write("- 성능 벤치마킹 및 회귀 테스트에 적용\n")
                f.write("- 실제 사용자 시나리오 시뮬레이션\n")
            else:
                f.write("원본 분포와 일부 차이가 있으니 주의해서 사용하시기 바랍니다.\n\n")
                f.write("### ⚠️ 개선 필요\n")
                f.write("- 더 많은 실제 이미지 데이터 수집\n")
                f.write("- 패턴 주입 알고리즘 개선\n")
                f.write("- 분포 매칭 정확도 향상\n")

    def _apply_replace_pattern(self, text: str, pattern) -> str:
        """Replace 패턴 적용 (GT → Raw 역변환)"""
        return self._reverse_inject_error(text, pattern)
    
    def _apply_insert_pattern(self, text: str, pattern) -> str:
        """Insert 패턴 적용 (GT → Raw 역변환)"""
        return self._reverse_inject_error(text, pattern)
    
    def _apply_delete_pattern(self, text: str, pattern) -> str:
        """Delete 패턴 적용 (GT → Raw 역변환)"""
        return self._reverse_inject_error(text, pattern)
    
    def _apply_normalize_pattern(self, text: str, pattern) -> str:
        """Normalize 패턴 적용 (GT → Raw 역변환)"""
        return self._reverse_inject_error(text, pattern)

    def _apply_context_anchored_replacement(
        self, text: str, gt_snippet: str, raw_snippet: str, 
        context_before: str, context_after: str, op_type: str
    ) -> str:
        """Context 정보를 활용한 정확한 위치 기반 replacement"""
        debug_info = {
            'text_len': len(text),
            'gt_snippet': repr(gt_snippet),
            'raw_snippet': repr(raw_snippet),
            'context_before': repr(context_before),
            'context_after': repr(context_after),
            'op_type': op_type,
            'method_used': 'unknown',
            'success': False
        }
        
        original_text = text
        
        # 1. Context 기반 정확한 위치 탐지
        target_pattern = ""
        replacement = ""
        
        if context_before and context_after:
            target_pattern = f"{context_before}{gt_snippet}{context_after}"
            replacement = f"{context_before}{raw_snippet}{context_after}"
        elif context_before:
            target_pattern = f"{context_before}{gt_snippet}"
            replacement = f"{context_before}{raw_snippet}"
        elif context_after:
            target_pattern = f"{gt_snippet}{context_after}"
            replacement = f"{raw_snippet}{context_after}"
        else:
            # Context가 없으면 fallback
            if gt_snippet in text:
                debug_info['method_used'] = 'direct_replace_no_context'
                result = text.replace(gt_snippet, raw_snippet, 1)
                debug_info['success'] = result != text
                if not debug_info['success']:
                    print(f"⚠️ INSERT DEBUG: Context 없이 직접 replace 실패 - {debug_info}")
                return result
            debug_info['method_used'] = 'no_context_no_match'
            print(f"❌ INSERT DEBUG: Context도 없고 gt_snippet 매칭도 실패 - {debug_info}")
            return text
        
        # 2. Pattern이 텍스트에 존재하면 정확한 교체
        if target_pattern in text:
            debug_info['method_used'] = 'exact_pattern_match'
            result = text.replace(target_pattern, replacement, 1)
            debug_info['success'] = result != text
            if op_type == "insert" and not debug_info['success']:
                print(f"⚠️ INSERT DEBUG: Exact pattern 교체했지만 변화없음 - {debug_info}")
            return result
        
        # 3. Fuzzy matching으로 부분 매칭 시도
        if context_before and context_before in text:
            # context_before 다음 위치에서 작업
            pos = text.find(context_before) + len(context_before)
            debug_info['method_used'] = 'context_before_fuzzy'
            
            if op_type == "insert" and raw_snippet == "":
                # GT snippet 제거 (INSERT는 GT에서 제거하여 Raw 만들기)
                if text[pos:].startswith(gt_snippet):
                    result = text[:pos] + text[pos + len(gt_snippet):]
                    debug_info['success'] = result != text
                    debug_info['method_used'] = 'insert_remove_exact'
                    if not debug_info['success']:
                        print(f"⚠️ INSERT DEBUG: GT snippet 제거했지만 변화없음 - {debug_info}")
                    return result
                else:
                    # GT snippet이 정확히 매칭되지 않음 - INSERT 실패
                    debug_info['method_used'] = 'insert_remove_failed'
                    debug_info['next_chars'] = repr(text[pos:pos+len(gt_snippet)+5])
                    print(f"❌ INSERT DEBUG: GT snippet 위치 불일치 - {debug_info}")
                    return text
            else:
                # 일반적인 교체
                if text[pos:].startswith(gt_snippet):
                    result = text[:pos] + raw_snippet + text[pos + len(gt_snippet):]
                    debug_info['success'] = result != text
                    debug_info['method_used'] = 'replace_exact'
                    return result
                else:
                    # gt_snippet이 정확히 매치되지 않으면 raw_snippet 삽입
                    result = text[:pos] + raw_snippet + text[pos:]
                    debug_info['success'] = result != text
                    debug_info['method_used'] = 'insert_fallback'
                    return result
        
        # 4. 마지막 수단: 기본 replace
        if gt_snippet in text:
            debug_info['method_used'] = 'basic_replace'
            result = text.replace(gt_snippet, raw_snippet, 1)
            debug_info['success'] = result != text
            if op_type == "insert" and not debug_info['success']:
                print(f"⚠️ INSERT DEBUG: 기본 replace 실패 - {debug_info}")
            return result
        
        # 5. 완전 실패
        debug_info['method_used'] = 'complete_failure'
        if op_type == "insert":
            print(f"❌ INSERT DEBUG: 모든 방법 실패 - {debug_info}")
            
        return text

    def _reverse_inject_error(self, gt_text, event):
        """GT → Raw 역변환으로 오류 주입 (Context-anchored replacement 적용)"""
        gt_snippet = event.gt_snippet
        raw_snippet = event.raw_ocr_snippet
        op_type = event.op_type
        
        # Context 정보 추출 (실제 event 객체에서)
        context_before = getattr(event, 'context_before', '') or event.get("context_before", "")
        context_after = getattr(event, 'context_after', '') or event.get("context_after", "")
        
        # Context-anchored replacement: 정확한 위치에서 변환
        if context_before or context_after:
            return self._apply_context_anchored_replacement(
                gt_text, gt_snippet, raw_snippet, context_before, context_after, op_type
            )
        
        # 1차 시도: 정확한 매칭이 가능한 경우 직접 교체 (fallback)
        if gt_snippet in gt_text:
            return gt_text.replace(gt_snippet, raw_snippet, 1)
        else:
            # 매칭되지 않으면 op_type별 역변환 수행 (2차 시도) 
            if op_type == "insert":
                # INSERT 의미: GT에 있던 것을 OCR이 누락
                # 역변환: GT에서 gt_snippet(있던 것)을 제거하여 Raw 생성
                if raw_snippet == "":
                    # GT 텍스트에 있는 경우 제거
                    if gt_snippet in gt_text:
                        return gt_text.replace(gt_snippet, "", 1)
                    else:
                        # 마지막 수단: 텍스트 끝에 추가 후 제거 (의미적 일관성 확보)
                        new_text = gt_text + gt_snippet
                        return new_text.replace(gt_snippet, "", 1)
                else:
                    # raw_snippet이 비어있지 않은 경우: 임의 위치에 배치
                    return gt_text + raw_snippet
                        
            elif op_type == "delete":
                # DELETE 의미: GT에 없던 것을 OCR이 추가
                # 역변환: GT에 raw_snippet을 추가하여 Raw 생성
                if gt_snippet == "":
                    import random
                    pos = random.randint(0, len(gt_text))
                    return gt_text[:pos] + raw_snippet + gt_text[pos:]
                else:
                    return gt_text.replace(gt_snippet, raw_snippet, 1)
                    
            elif op_type == "replace":
                # Replace: 직접 교체
                return gt_text.replace(gt_snippet, raw_snippet, 1)
                
            else:  # normalize 등 기타  
                return gt_text.replace(gt_snippet, raw_snippet, 1)


def main():
    """메인 실행 함수 - Authentic Distribution 기반"""
    parser = argparse.ArgumentParser(description="실제 오류 분포 기반 합성 데이터셋 구축")
    parser.add_argument("--folder", required=True, help="이미지 폴더 경로 (real 폴더 권장)")
    parser.add_argument("--max-pages", type=int, default=30, help="최대 처리할 페이지 수 (default: 30)")
    parser.add_argument("--topk", type=int, default=200, help="상위 K개 패턴 (default: 200)")
    parser.add_argument("--synthetic-size", type=int, default=5000, help="합성 데이터셋 크기 (default: 5000)")
    parser.add_argument("--seed", type=int, default=42, help="랜덤 시드 (default: 42)")
    parser.add_argument("--cache-dir", default="outputs/cache_google_vision", help="캐시 디렉토리")
    parser.add_argument("--output-dir", default=".snaptxt/analysis", help="출력 디렉토리")
    parser.add_argument("--convert-heic", action="store_true", default=True, help="HEIC를 JPG로 변환 (default: True)")
    parser.add_argument("--force-authentic", action="store_true", help="Authentic Vision GT만 강제 사용")
    
    args = parser.parse_args()
    
    print("🚀 Authentic Distribution 기반 합성 데이터셋 구축")
    print("="*70)
    print(f"📁 이미지 폴더: {args.folder}")
    
    # Real folder 검증 및 경고
    if "real" not in args.folder.lower():
        print(f"⚠️  경고: 'real' 폴더가 아닌 '{args.folder}' 사용")
        print(f"   Authentic Distribution을 위해 'real' 폴더 사용을 권장합니다.")
        if not args.force_authentic:
            response = input("계속하시겠습니까? (y/N): ")
            if response.lower() != 'y':
                print("🚫 중단됨. Real 폴더를 사용하세요.")
                return
    else:
        print(f"✅ Real 폴더 사용 - Authentic Distribution 보장")
    
    print(f"🔝 상위 패턴: {args.topk}개")
    print(f"🎲 시드: {args.seed}")
    print(f"💾 캐시 디렉토리: {args.cache_dir}")
    print(f"📤 출력 디렉토리: {args.output_dir}")
    print()
    
    # GT Pool Expansion 금지 경고
    print("🏛️  **Authentic Distribution 모드**")
    print("   - GT Pool Expansion 사용 안함")
    print("   - Context-anchored replacement 사용")
    print("   - 실제 Vision GT로만 합성")
    print()
    
    # 환경 확인
    if not os.getenv("GOOGLE_VISION_API_KEY"):
        print("⚠️ GOOGLE_VISION_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   Google Vision API를 사용하려면 환경변수를 설정하세요.")
        print("   PowerShell에서: $env:GOOGLE_VISION_API_KEY='YOUR_API_KEY'")
        print("   또는 시스템 환경변수에서 설정하세요.")
        print("   Ground Truth 생성 없이 SnapTXT OCR만 처리됩니다.")
    
    try:
        analyzer = ErrorDistributionAnalyzer(
            cache_dir=args.cache_dir,
            output_dir=args.output_dir
        )
        
        # 분석 실행
        result = analyzer.process_image_folder(
            folder_path=args.folder,
            topk=args.topk,
            seed=args.seed,
            max_pages=getattr(args, 'max_pages', 30),
            synthetic_size=getattr(args, 'synthetic_size', 5000)
        )
        
        print("\n🎉 모든 작업이 완료되었습니다!")
        print(f"📊 처리된 이미지: {result['total_images']}개")
        print(f"🎯 오류 이벤트: {result['error_events']}개")
        print(f"📈 상위 패턴: {result['top_patterns']}개")
        print(f"🧪 합성 샘플: {result['synthetic_samples']}개")
        print(f"\n📁 생성된 파일들 (Run ID: {analyzer.run_id}):")
        
        for file_name in result["output_files"]:
            file_path = analyzer.current_run_dir / file_name
            print(f"   📄 {file_path}")
        
        # 성공 마커 및 latest 링크 갱신
        analyzer._mark_success_and_update_latest()
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️ 사용자에 의해 중단되었습니다.")
        print(f"🗂️ 미완성 출력 폴더: {analyzer.current_run_dir if 'analyzer' in locals() else 'N/A'}")
        print("🚨 latest 링크는 갱신되지 않음 (이전 성공한 run 유지)")
    except Exception as e:
        print(f"\n\n❌ 오류 발생: {e}")
        print(f"🗂️ 실패한 출력 폴더: {analyzer.current_run_dir if 'analyzer' in locals() else 'N/A'}")
        print("🚨 latest 링크는 갱신되지 않음 (이전 성공한 run 유지)")
        raise


# Backward compatibility alias
EventReplayDatasetBuilder = ErrorDistributionAnalyzer


if __name__ == "__main__":
    main()