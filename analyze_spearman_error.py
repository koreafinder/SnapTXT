#!/usr/bin/env python3
"""
Spearman correlation 저하 원인 분석 도구
Top50 기준으로 real vs synth rank 비교 및 원인 분류
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import spearmanr

def analyze_spearman_error():
    """Top50 Spearman correlation 저하 원인 상세 분석"""
    
    # 최신 분포 검증 결과 로드
    analysis_dir = Path(".snaptxt/analysis")
    latest_validation = analysis_dir / "distribution_validation_20260304_074842.json"
    latest_top50 = analysis_dir / "top50_patterns_20260304_074842.json"
    
    with open(latest_validation, 'r', encoding='utf-8') as f:
        validation_data = json.load(f)
    
    with open(latest_top50, 'r', encoding='utf-8') as f:
        patterns_data = json.load(f)
    
    print("📊 Top50 Spearman correlation 저하 원인 분석")
    print("=" * 80)
    
    # 1. Real vs Synth rank 비교 테이블 생성
    comparison_table = validation_data['comparison_table']
    
    rank_data = []
    for row in comparison_table:
        signature = row['signature'] 
        real_count = row['real_count']
        synth_count = row['synth_count']
        real_rank = row['rank']
        
        # Synth rank 계산 (count 기준 내림차순)
        synth_ranks = {}
        sorted_synth = sorted(comparison_table, key=lambda x: x['synth_count'], reverse=True)
        for i, item in enumerate(sorted_synth):
            if item['signature'] not in synth_ranks:
                synth_ranks[item['signature']] = i + 1
        
        synth_rank = synth_ranks.get(signature, 51)  # 없으면 최하위
        rank_diff = abs(real_rank - synth_rank)
        count_ratio = (synth_count + 1) / (real_count + 1)
        
        rank_data.append({
            'signature': signature,
            'real_count': real_count,
            'real_rank': real_rank,
            'synth_count': synth_count, 
            'synth_rank': synth_rank,
            'rank_diff': rank_diff,
            'count_ratio': count_ratio,
            'is_match': row['is_match']
        })
    
    # DataFrame으로 변환
    df = pd.DataFrame(rank_data)
    
    # CSV 저장
    csv_file = analysis_dir / "real_vs_synth_rank_top50.csv"
    df.to_csv(csv_file, index=False, encoding='utf-8')
    print(f"📄 CSV 저장: {csv_file}")
    
    # Top10 rank_diff 기준 최대 기여자들
    top_contributors = df.nlargest(10, 'rank_diff')
    
    print(f"\n🔍 Spearman 저하 Top10 기여자:")
    print("-" * 100)
    print(f"{'Rank':<4} {'Signature':<35} {'Real':<6} {'Synth':<6} {'RankDiff':<8} {'Ratio':<7} {'원인분류'}")
    print("-" * 100)
    
    # 원인 분류 로직
    error_contributors = []
    
    for i, (_, row) in enumerate(top_contributors.iterrows()):
        signature = row['signature'] 
        real_count = int(row['real_count'])
        synth_count = int(row['synth_count'])
        rank_diff = int(row['rank_diff'])
        count_ratio = row['count_ratio']
        
        # 원인 분류
        if signature.startswith('INSERT['):
            if synth_count == 0:
                cause = "INSERT 적용 실패 (apply bug)"
                category = "apply_bug"
            else:
                cause = "INSERT 과소 샘플링"
                category = "weight_bug"
        elif synth_count == 0:
            cause = "완전 누락 (필터링 또는 적용 실패)"
            category = "filter_bug"
        elif count_ratio > 3.0:
            cause = "과대 샘플링 (weight 문제)" 
            category = "weight_bug"
        elif count_ratio < 0.3:
            cause = "과소 샘플링 (weight 문제)"
            category = "weight_bug"
        else:
            cause = "순위 역전 (빈도는 비슷하나 순서 틀림)"
            category = "rank_bug"
        
        print(f"{i+1:<4} {signature:<35} {real_count:<6} {synth_count:<6} {rank_diff:<8} {count_ratio:<7.2f} {cause}")
        
        error_contributors.append({
            "rank": i + 1,
            "signature": signature,
            "real_count": real_count,
            "synth_count": synth_count, 
            "real_rank": int(row['real_rank']),
            "synth_rank": int(row['synth_rank']),
            "rank_diff": rank_diff,
            "count_ratio": count_ratio,
            "cause": cause,
            "category": category
        })
    
    print("-" * 100)
    
    # 원인별 요약
    categories = {}
    for contributor in error_contributors:
        cat = contributor['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(contributor)
    
    print(f"\n📋 원인별 분류:")
    for category, items in categories.items():
        print(f"  • {category}: {len(items)}개")
        for item in items[:3]:  # 처음 3개만
            print(f"    - {item['signature']}: rank_diff={item['rank_diff']}")
    
    # JSON 저장
    json_file = analysis_dir / "spearman_error_contributors.json"
    result_data = {
        "analysis_timestamp": "2026-03-04T07:48:42",
        "spearman_correlation": validation_data['spearman_correlation'],
        "target_correlation": 0.85,
        "top10_contributors": error_contributors,
        "category_summary": {cat: len(items) for cat, items in categories.items()},
        "primary_causes": {
            "INSERT_apply_failures": len([c for c in error_contributors if c['category'] == 'apply_bug']),
            "weight_issues": len([c for c in error_contributors if c['category'] == 'weight_bug']),
            "filter_issues": len([c for c in error_contributors if c['category'] == 'filter_bug'])
        }
    }
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"📄 JSON 저장: {json_file}")
    
    # 핵심 문제 식별
    insert_failures = [c for c in error_contributors if c['category'] == 'apply_bug']
    if insert_failures:
        print(f"\n🚨 핵심 문제: INSERT 계열 적용 실패")
        print(f"   INSERT 실패 패턴: {len(insert_failures)}개")
        for failure in insert_failures:
            print(f"   • {failure['signature']}: real={failure['real_count']} synth={failure['synth_count']}")
    
    return result_data

if __name__ == "__main__":
    analyze_spearman_error()