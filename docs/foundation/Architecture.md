# SnapTXT 아키텍처

이 문서는 Project_Memory에 정의된 “책 촬영 → PC 추출 → 웹 업로드 → 읽기/듣기” 목표를 시스템 관점에서 풀어낸다.

## 1. 사용자 흐름 요약
1. **촬영**: 사용자가 Office Lens 등으로 책 페이지를 찍고 이미지를 PC에 전송한다.
2. **추출**: PC 앱(`pc_app.py`)에서 이미지를 선택하면 공용 OCR 파이프라인이 텍스트를 만든다.
3. **업로드**: 추출 결과를 웹 페이지(사용자 제작 뷰어)에 업로드한다.
4. **소비**: 크롬/사파리 등 브라우저에서 텍스트를 읽거나 Web TTS로 바로 듣는다.

## 2. 시스템 구성
- **데스크톱 앱 (SnapTXT PC)**
   - PyQt UI + 워커 스레드로 구성.
   - 사용자는 파일 선택, 진행률 확인, 결과 복사/저장 작업을 수행.
- **공용 OCR 파이프라인**
   - `snaptxt.backend.multi_engine.MultiOCRProcessor` 한 곳에서 전처리 → EasyOCR 서브프로세스 → Stage2/Stage3 후처리까지 책임.
   - 모든 진입점(PyQt, Flask, CLI)이 동일 API를 호출해 품질을 일관되게 유지.
- **후처리 엔진**
   - Stage2/Stage3가 YAML 규칙과 형태소 기반 로직으로 띄어쓰기·문단·깨진 문자 복원을 담당.
   - `reload_stage*_rules()`로 현장 피드백을 바로 반영 가능.
- **웹 전달 계층**
   - 사용자가 직접 만드는 정적/동적 웹 페이지.
   - SnapTXT에서 생성한 텍스트를 기반으로 TTS, 하이라이트, 히스토리 기능을 제공.

## 3. 데이터 흐름
```
이미지 선택 → preprocess (apply_default_filters)
                → 임시 PNG 저장 → `python -m snaptxt.backend.worker.easyocr_worker`
                → EasyOCR 인식 결과 → Stage2/Stage3 후처리
                → 최종 텍스트 + JSON 메타데이터 → UI 표시/파일 저장
                → 사용자가 웹에 업로드
```

## 4. 품질·운영 포인트
- **실용적 OCR**: 고비용 API 대신 CPU EasyOCR + 후처리로 읽기 자연성 확보.
- **시간 기준**: 촬영 후 1분 내 웹에서 읽기/듣기가 가능해야 하므로, 파이프라인은 배치보다 단일 요청 지연을 최소화하도록 설계.
- **로그 & 재현성**: `snaptxt/backend/logging.py`가 JSONL 로그를 남기며, `scripts/run_regression.ps1`으로 Stage3 회귀를 일괄 실행.
- **환경 제어**: `.venv_new`에서 DLL 경로를 선제 세팅하고, UTF-8 입출력 옵션을 토글할 수 있게 해 디버깅/배포를 단순화.

## 5. 확장 포인트
- **웹 자동 업로드**: 현재는 수동 업로드지만, 향후 REST API 혹은 클라우드 싱크를 통해 텍스트가 바로 웹 뷰어로 전송되도록 확장한다.
- **품질 대시보드**: 후처리 품질 점수와 사용 이력을 시각화해 “읽을 수 있는 텍스트” 기준 충족 여부를 확인한다.
- **패키징**: PyInstaller 기반 데스크톱 배포 시 Qt 플러그인·PyTorch DLL을 번들링하고, EasyOCR 워커를 `python -m` 형태로 유지한다.

이 구조를 통해 SnapTXT는 비용을 최소화하면서도 “책을 찍으면 곧바로 읽고 들을 수 있는” 흐름을 유지한다.
