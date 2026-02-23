#!/usr/bin/env python3
"""
SnapTXT - OCR과 TTS를 활용한 학습 도구
이미지/스크린샷에서 텍스트를 추출하고 웹에서 TTS로 듣고 공부할 수 있는 애플리케이션
"""

# 로깅 설정
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from flask import Flask, render_template, request, jsonify
import os
from PIL import Image
from ocr_processor import OCRProcessor

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# CORS 헤더 추가
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

# OCR 프로세서 초기화
ocr_processor = OCRProcessor()

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """이미지 파일 업로드 및 OCR 처리"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '파일이 선택되지 않았습니다.'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '파일이 선택되지 않았습니다.'}), 400
        
        if not file or not allowed_file(file.filename):
            return jsonify({'success': False, 'error': '지원하지 않는 파일 형식입니다.'}), 400
        
        # PIL Image로 직접 처리
        image = Image.open(file.stream)
        
        # OCR 처리
        extracted_text = ocr_processor.extract_text_from_pil_image(image)
        
        if not extracted_text.strip():
            return jsonify({
                'success': True,
                'text': '이미지에서 텍스트를 찾을 수 없습니다. 이미지가 선명하고 텍스트가 포함되어 있는지 확인해주세요.'
            })
        
        return jsonify({
            'success': True,
            'text': extracted_text
        })
        
    except Exception as e:
        logger.error(f"파일 업로드/OCR 처리 중 오류: {str(e)}")
        return jsonify({'success': False, 'error': f'파일 처리 중 오류가 발생했습니다: {str(e)}'}), 500

def allowed_file(filename):
    """허용된 파일 확장자 확인"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/status')
def server_status():
    """서버 상태 확인"""
    return jsonify({
        'status': 'running',
        'message': 'SnapTXT 서버가 정상 작동 중입니다.'
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)