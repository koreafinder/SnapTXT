from comma_subtype_experiment import CommaContextInserter, CommaInsertType
inserter = CommaContextInserter()

# Test some examples to find correct positions
test_cases = [
    ('사과 오렌지 바나나를 샀다', CommaInsertType.LIST_SEPARATION),
    ('서울 한국에 살고 있다', CommaInsertType.GEOGRAPHIC),
    ('저자 김철수가 발표했다', CommaInsertType.APPOSITION),
    ('그가 말했다 안녕하세요', CommaInsertType.QUOTATION)
]

for text, insert_type in test_cases:
    result, context, confidence, pos = inserter.context_aware_insert_by_type(text, insert_type)
    print(f'{insert_type.value}: "{text}" → pos {pos} → "{result}"')