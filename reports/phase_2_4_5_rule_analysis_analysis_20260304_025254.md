
# Rule Contribution Analysis Report
Generated at: 2026-03-04T02:52:54.277184
Analysis ID: analysis_20260304_025254

## Summary
- Test Dataset Size: 12 samples
- Total Rules Analyzed: 6 
- Quality Score: 33.3/100
- Overall Improvement: +0.041 CER

## Rule Classification
- ✅ Beneficial: 2 rules
- ⚠️  Neutral: 0 rules  
- ❌ Harmful: 4 rules

## Recommended Actions
### Auto-Enable Rules:
- Rule 4: ''' → '.' (ΔCER: +0.036)
- Rule 6: '갔' → '회' (ΔCER: +0.006)

### Disable Rules:
- Rule 1: '되' → '됩' (ΔCER: -0.025)
- Rule 2: '웅' → '움' (ΔCER: -0.005)
- Rule 3: '덥' → '됩' (ΔCER: -0.003)
- Rule 5: '근' → '큰' (ΔCER: -0.018)

## Detailed Analysis


### Rule 1: Harmful
- Pattern: '되' → '됩'
- Overall ΔCER: -0.0250
- Category ΔCERs:
  - Space: +0.0000
  - Punct: +0.0000 
  - Char: -0.1667
- Applications: 5 times
- False Positive Rate: 60.0%
- Coverage: 41.7%
- Confidence: 0.95
- Auto-Enable: False
- Context Dependency: 0.50
- Robustness: 0.50
- Side Effects: 높은 변동성 (std: 0.077)


### Rule 2: Harmful
- Pattern: '웅' → '움'
- Overall ΔCER: -0.0047
- Category ΔCERs:
  - Space: +0.0000
  - Punct: +0.0000 
  - Char: +0.0000
- Applications: 5 times
- False Positive Rate: 40.0%
- Coverage: 41.7%
- Confidence: 0.90
- Auto-Enable: False
- Context Dependency: 0.50
- Robustness: 0.50
- Side Effects: 높은 변동성 (std: 0.051)


### Rule 3: Harmful
- Pattern: '덥' → '됩'
- Overall ΔCER: -0.0033
- Category ΔCERs:
  - Space: +0.0000
  - Punct: +0.0000 
  - Char: +0.0000
- Applications: 2 times
- False Positive Rate: 50.0%
- Coverage: 16.7%
- Confidence: 0.90
- Auto-Enable: False
- Context Dependency: 0.40
- Robustness: 0.50
- Side Effects: None


### Rule 4: Beneficial
- Pattern: ''' → '.'
- Overall ΔCER: +0.0355
- Category ΔCERs:
  - Space: +0.0000
  - Punct: +0.4167 
  - Char: +0.0000
- Applications: 4 times
- False Positive Rate: 0.0%
- Coverage: 33.3%
- Confidence: 0.95
- Auto-Enable: True
- Context Dependency: 0.50
- Robustness: 0.50
- Side Effects: 높은 변동성 (std: 0.061)


### Rule 5: Harmful
- Pattern: '근' → '큰'
- Overall ΔCER: -0.0177
- Category ΔCERs:
  - Space: +0.0000
  - Punct: +0.0000 
  - Char: +0.0833
- Applications: 5 times
- False Positive Rate: 60.0%
- Coverage: 41.7%
- Confidence: 0.95
- Auto-Enable: False
- Context Dependency: 0.50
- Robustness: 0.50
- Side Effects: 높은 변동성 (std: 0.067)


### Rule 6: Beneficial
- Pattern: '갔' → '회'
- Overall ΔCER: +0.0060
- Category ΔCERs:
  - Space: +0.0000
  - Punct: +0.0000 
  - Char: +0.0833
- Applications: 2 times
- False Positive Rate: 0.0%
- Coverage: 16.7%
- Confidence: 0.95
- Auto-Enable: True
- Context Dependency: 0.32
- Robustness: 0.70
- Side Effects: None

