#!/usr/bin/env python3
"""INSERT[","] 오류 이벤트 분석"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_insert_comma_events():
    """INSERT[","] 이벤트 상세 분석"""
    
    error_events_file = Path('.snaptxt/cache/error_events.jsonl')
    insert_comma_events = []
    
    if error_events_file.exists():
        with open(error_events_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    event = json.loads(line.strip())
                    if event.get('signature') == 'INSERT[","]':
                        insert_comma_events.append({
                            'line': line_num,
                            'raw_snippet': event.get('raw_snippet'),
                            'gt_snippet': event.get('gt_snippet'),
                            'page_id': event.get('page_id'),
                            'op_type': event.get('op_type'),
                            'context_before': event.get('context_before', '')[:50] + '...',
                            'context_after': event.get('context_after', '')[:50] + '...'
                        })
                        if len(insert_comma_events) >= 10:  # 처음 10개
                            break
                except json.JSONDecodeError:
                    continue
    
    print(f'📋 INSERT[","] events found: {len(insert_comma_events)}개')
    print('=' * 80)
    
    for i, event in enumerate(insert_comma_events, 1):
        print(f'{i:2d}. Line {event["line"]}: {event["page_id"]}')
        print(f'   📝 raw_snippet: "{event["raw_snippet"]}"')
        print(f'   ✅ gt_snippet:  "{event["gt_snippet"]}"')
        print(f'   🔧 op_type: {event["op_type"]}')
        print(f'   ⬅️  context_before: {event["context_before"]}')
        print(f'   ➡️  context_after: {event["context_after"]}')
        print()
    
    # 패턴 분석
    if insert_comma_events:
        raw_snippets = [event['raw_snippet'] for event in insert_comma_events]
        gt_snippets = [event['gt_snippet'] for event in insert_comma_events]
        
        print(f'🔍 패턴 분석:')
        print(f'  • 고유한 raw_snippet: {len(set(raw_snippets))}개')
        print(f'  • 고유한 gt_snippet: {len(set(gt_snippets))}개')
        print(f'  • raw_snippet 목록: {list(set(raw_snippets))[:5]}')
        print(f'  • gt_snippet 목록: {list(set(gt_snippets))[:5]}')

if __name__ == "__main__":
    analyze_insert_comma_events()