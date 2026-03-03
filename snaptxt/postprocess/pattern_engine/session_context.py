"""Session Context Generator - 책별 세션 컨텍스트 생성

Phase 1.5에서 추가된 세션 인식 기능
책별, 촬영환경별 패턴 학습을 위한 컨텍스트 생성기
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import hashlib
import json
from pathlib import Path
import re


@dataclass
class SessionContext:
    """세션 컨텍스트 정보"""
    book_session_id: str      # "20260302_bookA_batch1"
    device_id: str            # "iphone12_user1"  
    capture_batch_id: str     # "batch_20260302_140530"
    book_domain: str          # "novel", "textbook", "magazine"
    image_quality: float      # 이미지 품질 지표 (0.0~1.0)
    
    created_at: datetime
    session_start: datetime
    estimated_book_id: str    # 책 추정 ID


class SessionContextGenerator:
    """세션 컨텍스트 자동 생성기"""
    
    def __init__(self, session_config_path: str = "logs/session_config.json"):
        self.config_path = Path(session_config_path)
        self.active_sessions: Dict[str, SessionContext] = {}
        self.session_history: List[SessionContext] = []
        
        # 세션 유지 시간 (분)
        self.session_timeout = 30  # 30분 후 세션 만료
        
        self._load_session_history()
        
    def generate_session_context(self, 
                                text: str, 
                                image_bytes: Optional[bytes] = None,
                                manual_book_id: Optional[str] = None) -> SessionContext:
        """텍스트와 이미지로부터 세션 컨텍스트 생성"""
        
        # 1. 책 Domain 추정
        book_domain = self._estimate_book_domain(text)
        
        # 2. 이미지 품질 계산
        image_quality = self._calculate_image_quality(image_bytes) if image_bytes else 0.7
        
        # 3. 책 ID 추정
        estimated_book_id = manual_book_id or self._estimate_book_id(text)
        
        # 4. Device ID 생성 (간단히 고정값, 실제로는 디바이스별 고유 ID)
        device_id = "device_001"  # TODO: 실제 디바이스 ID 수집
        
        # 5. 기존 세션 확인 또는 새 세션 생성
        session_key = f"{estimated_book_id}_{device_id}_{book_domain}"
        
        if self._should_continue_session(session_key):
            # 기존 세션 계속
            context = self.active_sessions[session_key] 
            context.image_quality = (context.image_quality + image_quality) / 2  # 평균
        else:
            # 새 세션 생성
            now = datetime.now()
            
            context = SessionContext(
                book_session_id=self._generate_book_session_id(estimated_book_id),
                device_id=device_id,
                capture_batch_id=self._generate_batch_id(),
                book_domain=book_domain,
                image_quality=image_quality,
                created_at=now,
                session_start=now,
                estimated_book_id=estimated_book_id
            )
            
            self.active_sessions[session_key] = context
        
        return context
    
    def _estimate_book_domain(self, text: str) -> str:
        """텍스트로부터 책 도메인 추정"""
        
        # 간단한 규칙 기반 분류
        text_lower = text.lower()
        
        # 교재/학습서 패턴
        textbook_patterns = ['문제', '연습', '해답', '정답', '단원', '챕터', '예제', '공식', '정리']
        if any(pattern in text for pattern in textbook_patterns):
            return "textbook"
            
        # 소설 패턴  
        novel_patterns = ['그는', '그녀는', '말했다', '생각했다', '"', '"', '라고', '였다']
        if any(pattern in text for pattern in novel_patterns):
            return "novel"
            
        # 잡지/뉴스 패턴
        magazine_patterns = ['기자', '보도', '발표', '회사', '업계', '시장', '올해', '지난해']
        if any(pattern in text for pattern in magazine_patterns):
            return "magazine"
        
        # 기본값
        return "general"
    
    def _estimate_book_id(self, text: str) -> str:
        """텍스트 특성으로부터 책 ID 추정"""
        
        # 텍스트의 첫 50글자로 간단한 해시 생성
        text_sample = text[:50].replace(' ', '').replace('\\n', '')
        
        # 해시 기반 책 ID (실제로는 더 정교한 방식 필요)
        book_hash = hashlib.md5(text_sample.encode('utf-8')).hexdigest()[:8]
        
        return f"book_{book_hash}"
    
    def _generate_book_session_id(self, book_id: str) -> str:
        """책별 세션 ID 생성"""
        today = datetime.now().strftime("%Y%m%d")
        session_count = len([s for s in self.session_history 
                           if s.estimated_book_id == book_id 
                           and s.created_at.date() == datetime.now().date()]) + 1
        
        return f"{today}_{book_id}_session{session_count:02d}"
    
    def _generate_batch_id(self) -> str:
        """배치 ID 생성"""
        return f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _calculate_image_quality(self, image_bytes: bytes) -> float:
        """이미지 품질 간단 추정 (실제로는 더 정교한 분석 필요)"""
        
        # 간단히 이미지 크기 기반 품질 추정
        image_size = len(image_bytes)
        
        if image_size > 1024 * 1024:  # 1MB 이상
            return 0.9
        elif image_size > 512 * 1024:  # 512KB 이상  
            return 0.7
        elif image_size > 100 * 1024:  # 100KB 이상
            return 0.5
        else:
            return 0.3
    
    def _should_continue_session(self, session_key: str) -> bool:
        """기존 세션을 계속할지 판단"""
        
        if session_key not in self.active_sessions:
            return False
            
        last_session = self.active_sessions[session_key]
        
        # 세션 타임아웃 체크
        time_diff = datetime.now() - last_session.created_at
        if time_diff > timedelta(minutes=self.session_timeout):
            # 만료된 세션은 히스토리로 이동
            self.session_history.append(last_session)
            del self.active_sessions[session_key]
            return False
        
        return True
    
    def _load_session_history(self):
        """세션 히스토리 로드"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # TODO: 세션 히스토리 복원 로직
            except Exception:
                pass
                
    def _save_session_history(self):
        """세션 히스토리 저장"""
        try:
            self.config_path.parent.mkdir(exist_ok=True)
            data = {
                "active_sessions_count": len(self.active_sessions),
                "total_sessions": len(self.session_history),
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def get_session_stats(self) -> Dict:
        """세션 통계 반환"""
        return {
            "active_sessions": len(self.active_sessions),
            "total_sessions": len(self.session_history),
            "domains": list(set(s.book_domain for s in self.session_history)),
            "average_quality": sum(s.image_quality for s in self.session_history) / max(len(self.session_history), 1)
        }


# 글로벌 세션 생성기 인스턴스
_session_generator = SessionContextGenerator()

def get_session_context(text: str, 
                       image_bytes: Optional[bytes] = None,
                       manual_book_id: Optional[str] = None) -> SessionContext:
    """편의 함수: 세션 컨텍스트 생성"""
    return _session_generator.generate_session_context(text, image_bytes, manual_book_id)

def get_session_stats() -> Dict:
    """편의 함수: 세션 통계 조회"""  
    return _session_generator.get_session_stats()