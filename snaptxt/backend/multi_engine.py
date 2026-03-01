#!/usr/bin/env python3
"""Multi OCR Processor - 다중 OCR 엔진 통합 처리기."""

import time
import cv2
import numpy as np
import os
from PIL import Image
import logging
from functools import lru_cache
from typing import Dict, List, Union, Optional
from pathlib import Path

from snaptxt.preprocess import apply_default_filters, smart_preprocess_image
from .logging import get_json_logger, log_event

logger = logging.getLogger(__name__)


class MultiOCRProcessor:
    """다중 OCR 엔진을 통합한 텍스트 추출 프로세서"""
    
    def __init__(self):
        # GUI 환경에서 PyTorch DLL 로딩 문제 완전 해결
        self._setup_torch_dll_environment()
        self.engines = {}
        self.init_engines()
        # JSON 구조 로그는 별도 로거 이름을 사용해 일반 콘솔 로그가 끊기지 않도록 한다.
        self.audit_logger = get_json_logger(f"{__name__}.audit")
    
    def _setup_torch_dll_environment(self):
        """PyQt5 GUI 환경에서 PyTorch DLL 로딩 문제 해결 (MultiOCRProcessor용)"""
        print("🔍 [DEBUG] _setup_torch_dll_environment() 호출됨!")
        
        try:
            import os
            import sys

            from pathlib import Path

            print(f"🔍 [DEBUG] Python 실행 경로: {sys.executable}")

            exe_path = Path(sys.executable).resolve()
            candidates = [
                exe_path.parent / "Lib" / "site-packages" / "torch" / "lib",
                exe_path.parent.parent / "Lib" / "site-packages" / "torch" / "lib",
                Path(sys.prefix) / "Lib" / "site-packages" / "torch" / "lib",
            ]

            torch_dll_path = next((str(path) for path in candidates if path.exists()), None)

            print(f"🔍 [DEBUG] torch DLL 후보 경로: {[str(p) for p in candidates]}")

            if torch_dll_path and os.path.exists(torch_dll_path):
                print("🔍 [DEBUG] torch DLL 경로 존재 확인됨!")
                
                # PATH 환경변수에 torch/lib 추가 (최우선 순위)
                current_path = os.environ.get('PATH', '')
                if torch_dll_path not in current_path:
                    os.environ['PATH'] = f"{torch_dll_path}{os.pathsep}{current_path}"
                    print(f"🔧 [DEBUG] 워커 스레드에서 PyTorch DLL 경로 PATH 추가: {torch_dll_path}")
                    logger.info(f"🔧 워커 스레드에서 PyTorch DLL 경로 PATH 추가: {torch_dll_path}")
                
                # Windows DLL 디렉토리 명시적 등록
                if hasattr(os, 'add_dll_directory'):
                    try:
                        os.add_dll_directory(torch_dll_path)
                        print("🔧 [DEBUG] Windows DLL 디렉토리 등록 완료")
                        logger.info("🔧 워커 스레드에서 Windows DLL 디렉토리 등록 완료")
                    except Exception as e:
                        print(f"⚠️ [DEBUG] DLL 디렉토리 등록 경고: {e}")
                        logger.warning(f"⚠️ 워커 스레드 DLL 디렉토리 등록 경고: {e}")
                
                # c10.dll 미리 로드 시도 (워커 스레드에서 EasyOCR 초기화 전)
                c10_dll_path = os.path.join(torch_dll_path, "c10.dll")
                if os.path.exists(c10_dll_path):
                    try:
                        import ctypes
                        dll_handle = ctypes.CDLL(c10_dll_path)
                        print("🔧 [DEBUG] c10.dll 미리 로드 성공!")
                        logger.info("🔧 워커 스레드에서 c10.dll 미리 로드 성공")
                        
                        # 추가 PyTorch DLL들도 미리 로드
                        torch_cpu_path = os.path.join(torch_dll_path, "torch_cpu.dll")
                        if os.path.exists(torch_cpu_path):
                            ctypes.CDLL(torch_cpu_path)
                            print("🔧 [DEBUG] torch_cpu.dll 미리 로드 성공!")
                            logger.info("🔧 torch_cpu.dll 미리 로드 성공")
                            
                    except Exception as e:
                        print(f"⚠️ [DEBUG] DLL 미리 로드 경고: {e}")
                        logger.warning(f"⚠️ 워커 스레드 DLL 미리 로드 경고: {e}")
                        
                # PyTorch import 테스트
                try:
                    import torch
                    print(f"🔧 [DEBUG] PyTorch 로드 성공: {torch.__version__}")
                    logger.info(f"🔧 워커 스레드에서 PyTorch 로드 성공: {torch.__version__}")
                except Exception as e:
                    print(f"❌ [DEBUG] PyTorch 로드 실패: {e}")
                    logger.error(f"❌ 워커 스레드에서 PyTorch 로드 실패: {e}")
            else:
                print("❌ [DEBUG] torch DLL 경로를 찾을 수 없음!")
            
        except Exception as e:
            print(f"❌ [DEBUG] DLL 환경 설정 실패: {e}")
            logger.error(f"❌ 워커 스레드 DLL 환경 설정 실패: {e}")
        
        # 작은 지연으로 DLL 로딩 안정화
        import time
        time.sleep(0.1)
        print("🔍 [DEBUG] _setup_torch_dll_environment() 완료!")
        
    def init_engines(self):
        """사용 가능한 OCR 엔진들을 초기화"""
        
        # EasyOCR 초기화 (프로세스 분리 방식)
        try:
            # EasyOCR 워커 스크립트 존재 확인
            worker_script = Path(__file__).parent / "worker" / "easyocr_worker.py"
            if worker_script.exists():
                # DLL 충돌을 피하기 위해 subprocess 방식으로 EasyOCR 사용
                self.engines['easyocr'] = 'subprocess'  # 플래그로 표시
                logger.info("✅ EasyOCR 엔진 초기화 완료 (프로세스 분리 모드)")
            else:
                logger.error("❌ EasyOCR 워커 스크립트를 찾을 수 없습니다")
        except Exception as e:
            logger.error(f"❌ EasyOCR 초기화 실패: {e}")
            logger.warning("⚠️ EasyOCR 엔진을 사용할 수 없습니다.")
        
        logger.info("✅ EasyOCR 전용 모드로 초기화 완료 - 단순화된 고성능 OCR 시스템")
    
    def preprocess_image(self, image: Union[np.ndarray, Image.Image], 
                        preprocessing_level: int = 1, use_scientific: bool = False) -> np.ndarray:
        """
        이미지 전처리를 통한 OCR 정확도 향상
        
        Args:
            image: 입력 이미지
            preprocessing_level: 레거시 전처리 레벨 (1-3)
            use_scientific: 과학적 전처리 시스템 사용 여부
            
        Returns:
            전처리된 이미지
        """
        if use_scientific:
            logger.info("🔬 과학적 전처리 시스템 사용")
            processed_image, metrics, plan = smart_preprocess_image(image)
            
            # 품질 정보 로깅
            logger.info(f"   품질 점수: {metrics.overall_quality:.3f}")
            logger.info(f"   적용 액션: {len(plan.actions)}개")
            logger.info(f"   근거: {plan.rationale}")
            logger.info(f"   신뢰도: {plan.confidence:.3f}")
            
            return processed_image
        else:
            logger.info(f"🏗️ 레거시 전처리 시스템 사용 (레벨 {preprocessing_level})")
            
            return apply_default_filters(
                image,
                level=preprocessing_level,
                logger_override=logger,
            )
    
    def extract_text_easyocr(self, image: np.ndarray, language: str = 'ko,en') -> str:
        """EasyOCR을 사용한 텍스트 추출 (프로세스 분리 방식)"""
        if 'easyocr' not in self.engines:
            return ""
            
        try:
            import subprocess
            import json
            import tempfile
            import sys
            
            # 임시 이미지 파일 생성
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_path = tmp_file.name
                
            # 이미지를 임시 파일에 저장
            cv2.imwrite(tmp_path, image)
            
            # EasyOCR 워커 스크립트 실행
            worker_script = Path(__file__).parent / "worker" / "easyocr_worker.py" 
            worker_module = "snaptxt.backend.worker.easyocr_worker"
            
            # 디버깅: 사용할 worker script 경로 확인
            logger.info(f"🔍 EasyOCR 워커 스크립트 경로: {worker_script}")
            logger.info(f"🔍 워커 스크립트 존재 확인: {worker_script.exists()}")
            if worker_script.exists():
                import os
                mtime = os.path.getmtime(worker_script)
                import datetime
                mod_time = datetime.datetime.fromtimestamp(mtime)
                logger.info(f"🔍 워커 스크립트 수정 시간: {mod_time}")
            
            # 가상환경 우선 순위로 워커 해상도 결정 (필요 시 현재 해석기 사용)
            import os
            import sys
            project_dir = Path(__file__).resolve().parents[2]
            venv_python = project_dir / '.venv_new' / 'Scripts' / 'python.exe'
            python_candidates = []
            if venv_python.exists():
                python_candidates.append(("venv_new", str(venv_python)))
            python_candidates.append(("current", sys.executable))
            python_executable = None
            for label, candidate in python_candidates:
                if candidate and os.path.exists(candidate):
                    python_executable = candidate
                    logger.info(f"🐍 EasyOCR 워커 Python 선택: {label} -> {candidate}")
                    break
            if not python_executable:
                raise RuntimeError("사용 가능한 Python 실행 파일을 찾을 수 없습니다.")
            
            # 기본 EasyOCR 처리 (multi_ocr_processor에서 이미 전처리했으므로 추가 전처리 안함)
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            project_root = project_dir
            env_path = env.get("PYTHONPATH", "")
            if str(project_root) not in env_path.split(os.pathsep):
                env["PYTHONPATH"] = f"{project_root}{os.pathsep}{env_path}" if env_path else str(project_root)

            result = subprocess.run([
                python_executable,
                "-m",
                worker_module,
                tmp_path,
                language
            ], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, cwd=str(project_root), env=env)
            
            # 임시 파일 삭제
            Path(tmp_path).unlink(missing_ok=True)
            
            # Stage 2 디버깅: stderr 출력 확인
            if result.stderr:
                logger.info(f"📝 EasyOCR 워커 stderr: {result.stderr}")
            
            if result.returncode == 0:
                try:
                    response = json.loads(result.stdout)
                    if response['success']:
                        response_text = response['text']
                        response_len = len(response_text)
                        logger.info("EasyOCR 프로세스 분리 처리 성공")
                        logger.info(f"🔍 디버깅: JSON 응답 텍스트 길이 = {response_len}자")
                        logger.info(f"🔍 디버깅: 응답 텍스트 샘플 = '{response_text[:100]}...'")
                        return response_text
                    else:
                        logger.error(f"EasyOCR 워커 오류: {response.get('error', '알 수 없는 오류')}")
                        return ""
                except json.JSONDecodeError as e:
                    logger.error(f"EasyOCR 워커 JSON 파싱 오류: {e}")
                    logger.error(f"원본 stdout: {result.stdout[:500]}...")
                    return ""
            else:
                logger.error(f"EasyOCR 워커 프로세스 실패 (코드 {result.returncode}): {result.stderr}")
                return ""
                
        except subprocess.TimeoutExpired:
            logger.error("EasyOCR 워커 프로세스 시간 초과")
            return ""
        except Exception as e:
            logger.error(f"EasyOCR 프로세스 분리 처리 실패: {e}")
            return ""
    

    

    

    
    def combine_results(self, results: Dict[str, str]) -> str:
        """여러 OCR 결과를 결합하여 최적의 텍스트 추출"""
        if not results:
            return ""
            
        # 빈 결과 제거
        valid_results = {k: v.strip() for k, v in results.items() if v.strip()}
        
        if not valid_results:
            return ""
            
        # 결과가 하나뿐인 경우
        if len(valid_results) == 1:
            return list(valid_results.values())[0]
        
        # 여러 결과가 있는 경우 - 가장 긴 결과 + 품질 평가
        logger.info(f"📊 OCR 결과 비교:")
        for engine, text in valid_results.items():
            korean_chars = len([c for c in text if '\uac00' <= c <= '\ud7af'])
            english_chars = len([c for c in text if c.isalpha() and ord(c) < 128])
            logger.info(f"  {engine}: {len(text)}자 (한글:{korean_chars}, 영어:{english_chars})")
        
        # 가장 긴 결과 선택
        best_result = max(valid_results.items(), key=lambda x: len(x[1]))
        logger.info(f"🏆 최종 선택: {best_result[0]} ({len(best_result[1])}자)")
        
        return best_result[1]
    
    def process_file(self, file_path: str, settings: Dict) -> str:
        """파일에 대한 OCR 처리 수행"""
        start_time = time.perf_counter()
        try:
            # 이미지 로드
            image_path = Path(file_path)
            if not image_path.exists():
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
                
            logger.info(f"📸 이미지 처리 시작: {image_path.name}")
            log_event(
                self.audit_logger,
                "multi_engine.process.start",
                source=str(image_path),
                settings=settings,
            )
            
            # PIL로 이미지 열기 (한글 경로 지원)
            pil_image = Image.open(image_path)
            logger.info(f"   이미지 크기: {pil_image.size}")
            
            # PIL → numpy → OpenCV 변환 (한글 경로 문제 해결)
            image_array = np.array(pil_image)
            
            # RGB → BGR 변환 (OpenCV 형식)
            if len(image_array.shape) == 3:
                cv_image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            else:
                cv_image = image_array
            
            # 이미지 전처리 - 과학적 전처리 시스템 활성화
            use_scientific = settings.get('use_scientific', True)  # 기본값: 과학적 전처리 사용
            preprocessing_level = settings.get('preprocessing_level', 2)  # 기본값: 중간 레벨
            
            if use_scientific:
                logger.info("🔬 과학적 전처리 시스템으로 이미지 처리 중...")
                processed_image = self.preprocess_image(cv_image, use_scientific=True)
            elif preprocessing_level > 0:
                logger.info(f"🏗️ 레거시 전처리 시스템으로 이미지 처리 중 (레벨 {preprocessing_level})...")
                processed_image = self.preprocess_image(cv_image, preprocessing_level=preprocessing_level, use_scientific=False)
            else:
                logger.info("🔧 원본 이미지 사용 (전처리 비활성화)...")
                processed_image = cv_image
            
            # 선택된 OCR 엔진들로 처리
            results = {}
            
            # EasyOCR 전용 처리
            if 'easyocr' in self.engines:
                logger.info("🔍 EasyOCR 처리 중...")
                easy_start = time.perf_counter()
                easy_text = self.extract_text_easyocr(processed_image, settings.get('language', 'ko,en'))
                results['EasyOCR'] = easy_text
                log_event(
                    self.audit_logger,
                    "multi_engine.easyocr.complete",
                    duration=round(time.perf_counter() - easy_start, 3),
                    text_length=len(easy_text),
                    success=bool(easy_text.strip()),
                    language=settings.get('language', 'ko,en'),
                    source=str(image_path),
                )
                logger.info(f"   EasyOCR 결과: {len(results['EasyOCR'])}자")
            else:
                logger.error("❌ EasyOCR 엔진을 사용할 수 없습니다.")
                log_event(
                    self.audit_logger,
                    "multi_engine.easyocr.unavailable",
                    source=str(image_path),
                )
                return "❌ EasyOCR 엔진을 초기화할 수 없습니다. snaptxt/backend/worker/easyocr_worker.py 파일을 확인하세요."
            
            # 결과 결합
            logger.info("🎯 결과 결합 중...")
            final_text = self.combine_results(results)

            log_event(
                self.audit_logger,
                "multi_engine.process.complete",
                source=str(image_path),
                success=bool(final_text.strip()),
                text_length=len(final_text),
                duration=round(time.perf_counter() - start_time, 3),
            )
            
            if not final_text.strip():
                logger.warning(f"⚠️  '{image_path.name}'에서 텍스트를 찾을 수 없습니다.")
                
                # 디버깅 정보 추가
                debug_info = f"""
⚠️ '{image_path.name}'에서 텍스트 인식 실패

🔧 디버깅 정보:
- 사용된 엔진: {', '.join(results.keys()) if results else '없음'}
- 전처리 레벨: 3 (최고급)
- 이미지 크기: {pil_image.size}

📝 개별 엔진 결과:"""
                
                for engine, text in results.items():
                    debug_info += f"\n  • {engine}: '{text[:50]}{'...' if len(text) > 50 else ''}' ({len(text)}자)"
                
                debug_info += f"""

💡 개선 제안:
1. 더 선명한 이미지 시도
2. 다른 OCR 엔진 조합 시도  
3. Tesseract 설치 확인 (현재 {'설치됨' if 'tesseract' in self.engines else '미설치'})
4. 이미지 밝기/대비 조정
"""
                return debug_info
                
            logger.info(f"✅ 처리 완료: {len(final_text)}자 추출")
            return final_text
            
        except Exception as e:
            error_msg = f"❌ 파일 처리 중 오류 발생: {str(e)}"
            logger.error(f"파일 처리 실패 {file_path}: {e}")
            log_event(
                self.audit_logger,
                "multi_engine.process.error",
                source=file_path,
                error=str(e),
            )
            return error_msg
    
    def get_engine_info(self) -> Dict[str, bool]:
        """사용 가능한 OCR 엔진 정보 반환"""
        return {
            'easyocr': 'easyocr' in self.engines
        }


# 테스트 코드 및 헬퍼

@lru_cache(maxsize=1)
def load_default_engine() -> "MultiOCRProcessor":
    """Return a cached instance to mirror the legacy helper."""

    return MultiOCRProcessor()


def main() -> None:
    """Simple CLI hook used by legacy scripts and debugging helpers."""

    processor = MultiOCRProcessor()
    print("🔍 사용 가능한 OCR 엔진:")
    engine_info = processor.get_engine_info()
    for engine, available in engine_info.items():
        status = "✅" if available else "❌"
        print(f"  {status} {engine}")

    test_settings = {'language': 'ko,en'}
    _ = test_settings  # Keep placeholder for future interactive samples
    print("\n✅ MultiOCRProcessor 초기화 완료!")


if __name__ == "__main__":
    main()