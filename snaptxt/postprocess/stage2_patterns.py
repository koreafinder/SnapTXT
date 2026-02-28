"""Regex-based Stage 2 helpers extracted from easyocr_worker."""

from __future__ import annotations

import re


def apply_dynamic_patterns(text: str) -> str:
    text = re.sub(
        r'([가-힣]+)([0-9]+)([가-힣]+)',
        lambda m: f"{m.group(1)} {m.group(2)} {m.group(3)}" if len(m.group(1)) > 1 and len(m.group(3)) > 1 else m.group(0),
        text,
    )
    text = re.sub(r'([0-9]+)([가-힣]{1,3})(전|후|간|째|번|개|명|일|년|월|시|분|초)(?![가-힣])', r'\1\2 \3', text)
    text = re.sub(r'([A-Za-z]+)([가-힣]{2,})(?![가-힣])', r'\1 \2', text)
    text = re.sub(r'([가-힣]{2,})([A-Z]{2,})(?![A-Za-z])', r'\1 \2', text)
    text = re.sub(r'([가-힣])([\(\)\[\]{}])([가-힣])', r'\1 \2 \3', text)
    text = re.sub(r'([\(\)\[\]{}])([가-힣])', r'\1 \2', text)
    text = re.sub(r'([가-힣])([\(\)\[\]{}])', r'\1 \2', text)
    text = re.sub(r'([가-힣])\s*([.!?])\s*([가-힣])', r'\1\2 \3', text)
    text = re.sub(r'([가-힣])\s*(["\'])\s*([가-힣])', r'\1 \2\3', text)
    text = re.sub(r'([가-힣])\s*(["\'])\s*([가-힣])', r'\1\2 \3', text)
    text = re.sub(r'(.)\1{3,}', r'\1\1', text)
    return text


def apply_contextual_patterns(text: str) -> str:
    sentences = re.split(r'[.!?]+', text)
    corrected = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > 100:
            sentence = re.sub(r'([가-힣]{3,})(에서는|로부터는|에게서는|로써는)', r'\1 \2', sentence)
        if sentence.startswith('그래서'):
            sentence = re.sub(r'^그래서([가-힣])', r'그래서 \1', sentence)
        elif sentence.startswith('하지만'):
            sentence = re.sub(r'^하지만([가-힣])', r'하지만 \1', sentence)
        elif sentence.startswith('따라서'):
            sentence = re.sub(r'^따라서([가-힣])', r'따라서 \1', sentence)
        elif sentence.startswith('즉'):
            sentence = re.sub(r'^즉([가-힣])', r'즉 \1', sentence)
        contextual_fixes = {
            '하느님': '하나님' if ('기독교' in text or '성경' in text) else '하느님',
            '부처님': '부처님' if ('불교' in text or '절' in text) else '부처님',
            '오전': '오전' if any(token in sentence for token in ['시', '분', '때']) else '오전',
            '오후': '오후' if any(token in sentence for token in ['시', '분', '때']) else '오후',
            '매우많은': '매우 많은',
            '아주좋은': '아주 좋은',
            '정말중요한': '정말 중요한',
            '너무어려운': '너무 어려운',
            '특히중요한': '특히 중요한',
        }
        for wrong, correct in contextual_fixes.items():
            if wrong in sentence:
                sentence = sentence.replace(wrong, correct)
        if sentence.count('것') > 3:
            sentence = re.sub(r'것\s*것', '것', sentence)
        if sentence.count('수') > 3:
            sentence = re.sub(r'할\s*수\s*있', '할 수 있', sentence)
            sentence = re.sub(r'될\s*수\s*있', '될 수 있', sentence)
        corrected.append(sentence)
    result = '. '.join(s.strip() for s in corrected if s.strip())
    return re.sub(r'\s+', ' ', result).strip()


def apply_spacing_refinements(text: str) -> str:
    text = re.sub(r'([가-힣]{2,})([0-9]{4})', r'\1 \2', text)
    text = re.sub(r'([0-9]{1,})([가-힣]{2,})', r'\1 \2', text)
    text = re.sub(r'([가-힣]{2,})(했습니다|합니다|됩니다|입니다|있습니다|없습니다)', r'\1 \2', text)
    text = re.sub(r'([가-힣]{2,})(지만|에서|에도|에게|로서|로써|이나|거나)', r'\1 \2', text)
    text = re.sub(r'([가-힣]{2,})(은|는|이|가|을|를|과|와|에|에서|에게|로|으로|의|도|만|부터|까지|처럼|같이)', r'\1 \2', text)
    text = re.sub(r'([가-힣]+)(고있[는다습니까])(?![가-힣])', r'\1고 있\2', text)
    text = re.sub(r'([가-힣]+)(어있[는다습니까])(?![가-힣])', r'\1어 있\2', text)
    text = re.sub(r'([가-힣]+)(아있[는다습니까])(?![가-힣])', r'\1아 있\2', text)
    text = re.sub(r'([가-힣]{2,})(하면서|하거나|하지만|한다면|했다면)', r'\1 \2', text)
    text = re.sub(r'([가-힣]{2,})(하기|되기|없이|있게|하게|되게)', r'\1 \2', text)
    text = re.sub(r'(매우|정말|아주|너무|특히|항상|절대|전혀|모든|각각|여러)([가-힣]{2,})', r'\1 \2', text)
    text = re.sub(r'([가-힣]{2,})(그리고|또한|하지만|그러나|따라서|즉|예를들어)', r'\1 \2', text)
    return text
