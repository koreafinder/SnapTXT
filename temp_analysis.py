import json

# 데이터 로드
with open('.snaptxt/analysis/runs/20260304_194119_240bf3e7/distribution_validation_20260304_194216.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('=== ① REVERSE-CHECK 문제 분석 ===')
print('Target Distribution vs Success Distribution')
print(f'{"Pattern":<30} {"Real":<5} {"Target":<7} {"Success":<8} {"T_Ratio":<7} {"S_Ratio":<7} {"Bucket":<12}')
print('-' * 100)

total_real = sum(item['real_count'] for item in data['comparison_table'][:20])  
expected_expansion = 500/246  # 2.03배
total_success = sum(item['synth_count'] for item in data['comparison_table'][:20])

space_count_target = 0
space_count_success = 0

for i, item in enumerate(data['comparison_table'][:20]):
    sig = item['signature'][:29]
    real = item['real_count'] 
    target = int(real * expected_expansion)
    success = item['synth_count']
    
    t_ratio = target / (total_real * expected_expansion) * 100
    s_ratio = success / total_success * 100
    
    # Space 패턴 구분
    is_space = ('U+0020' in sig or 'DELETE' in sig or 'INSERT' in sig and (' ' in sig or '\n' in sig))
    bucket = 'space' if is_space else 'other'
    
    if is_space:
        space_count_target += target
        space_count_success += success
    
    print(f'{sig:<30} {real:<5} {target:<7} {success:<8} {t_ratio:<6.1f}% {s_ratio:<6.1f}% {bucket:<12}')

print(f'\nSUMMARY:')
print(f'Total Real: {total_real}')
print(f'Expected Target: {int(total_real * expected_expansion)}')
print(f'Actual Success: {total_success}')
print(f'Space Target: {space_count_target} ({space_count_target/(total_real*expected_expansion)*100:.1f}%)')
print(f'Space Success: {space_count_success} ({space_count_success/total_success*100:.1f}%)')

# Reverse-check 계산
reverse_check = 0
valid_patterns = 0
for item in data['comparison_table'][:20]:
    expected = item['real_count'] * expected_expansion
    actual = item['synth_count']
    if expected > 0 and actual > 0:
        ratio = min(actual/expected, expected/actual)
        reverse_check += ratio
        valid_patterns += 1
    elif expected > 0:  # actual이 0인 경우
        valid_patterns += 1

reverse_check = reverse_check / valid_patterns if valid_patterns > 0 else 0
print(f'Calculated Reverse-check: {reverse_check:.3f} (based on {valid_patterns} valid patterns)')