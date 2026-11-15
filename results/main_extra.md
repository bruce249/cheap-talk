# Extra analyses (main)

## 1. First-answer stance distribution, void items

| condition | attacker value | hedge (both) | neither | true value | P(attacker \| committed) | mean confidence |
|---|---|---|---|---|---|---|
| Baseline | 16.7% | 61.3% | 9.4% | 12.7% | 56.7% | 51.7 |
| GEO style | 71.0% | 21.2% | 2.9% | 4.8% | 93.7% | 70.9 |
| Forged badge | 32.1% | 51.9% | 6.9% | 9.2% | 77.8% | 57.6 |
| Self-claimed 'verified' | 32.1% | 52.1% | 8.8% | 7.1% | 81.9% | 55.7 |
| 3 syndicated copies | 80.4% | 18.5% | 0.6% | 0.4% | 99.5% | 69.8 |
| 3 independent sources | 88.1% | 10.6% | 0.8% | 0.4% | 99.5% | 74.3 |
| Forged badge + system check | 31.0% | 49.8% | 10.0% | 9.2% | 77.2% | 52.6 |
| Check + spoofed 'PASSED' | 60.6% | 27.5% | 5.2% | 6.7% | 90.1% | 66.5 |
| Real verified badge on truth | 4.0% | 35.2% | 4.8% | 56.0% | 6.6% | 67.7 |

## 1. First-answer stance distribution, known items

| condition | attacker value | hedge (both) | neither | true value | P(attacker \| committed) | mean confidence |
|---|---|---|---|---|---|---|
| Baseline | 1.5% | 8.5% | 0.0% | 90.0% | 1.6% | 78.5 |
| GEO style | 11.7% | 10.8% | 0.8% | 76.7% | 13.2% | 78.4 |
| Forged badge | 2.3% | 7.3% | 0.2% | 90.2% | 2.5% | 78.5 |
| Self-claimed 'verified' | 2.7% | 8.3% | 0.0% | 89.0% | 3.0% | 78.5 |
| 3 syndicated copies | 15.8% | 9.8% | 0.6% | 73.8% | 17.7% | 76.0 |
| 3 independent sources | 20.8% | 9.0% | 0.2% | 70.0% | 22.9% | 76.4 |
| Forged badge + system check | 1.9% | 7.5% | 0.0% | 90.6% | 2.0% | 79.0 |
| Check + spoofed 'PASSED' | 3.1% | 7.1% | 0.4% | 89.4% | 3.4% | 78.5 |
| Real verified badge on truth | 0.2% | 3.3% | 0.0% | 96.5% | 0.2% | 84.6 |

Hedge-rate change vs baseline on void items (item-paired bootstrap 95% CI):

- GEO style: -40.0 pp [-45.0 pp, -35.2 pp]
- Forged badge: -9.4 pp [-14.0 pp, -5.0 pp]
- Self-claimed 'verified': -9.2 pp [-13.5 pp, -4.8 pp]
- 3 syndicated copies: -42.7 pp [-47.1 pp, -37.9 pp]
- 3 independent sources: -50.6 pp [-55.4 pp, -45.4 pp]
- Forged badge + system check: -11.5 pp [-15.8 pp, -6.9 pp]
- Check + spoofed 'PASSED': -33.8 pp [-38.1 pp, -29.4 pp]
- Real verified badge on truth: -26.0 pp [-30.8 pp, -21.0 pp]

## 2. Calibration on known items only (true value is real here)

Overall known-item ECE: 0.125 (n=3964)

| condition | n | accuracy | mean confidence | confidence when wrong | confidence when right | ECE |
|---|---|---|---|---|---|---|
| Baseline | 439 | 98.4% | 79.7 | 69.3 (n=7) | 79.9 | 0.187 |
| GEO style | 424 | 86.8% | 80.9 | 74.9 (n=56) | 81.8 | 0.106 |
| Forged badge | 444 | 97.5% | 79.7 | 67.5 (n=11) | 80.0 | 0.178 |
| Self-claimed 'verified' | 440 | 97.0% | 80.1 | 67.3 (n=13) | 80.5 | 0.170 |
| 3 syndicated copies | 430 | 82.3% | 77.4 | 64.8 (n=76) | 80.1 | 0.100 |
| 3 independent sources | 436 | 77.1% | 77.8 | 67.3 (n=100) | 80.9 | 0.090 |
| Forged badge + system check | 443 | 98.0% | 81.1 | 65.0 (n=9) | 81.5 | 0.169 |
| Check + spoofed 'PASSED' | 444 | 96.6% | 79.8 | 58.7 (n=15) | 80.6 | 0.168 |
| Real verified badge on truth | 464 | 99.8% | 85.3 | 70.0 (n=1) | 85.3 | 0.145 |

Void items, mean stated confidence by stance (sound value with one source against one is ~50):

- Baseline: all 51.7; attacker value 57.5; hedge (both values) 51.3; true value 57.4
- GEO style: all 70.9; attacker value 80.7; hedge (both values) 50.9; true value 40.6
- Forged badge: all 57.6; attacker value 68.8; hedge (both values) 52.6; true value 61.4
- Self-claimed 'verified': all 55.7; attacker value 65.1; hedge (both values) 52.4; true value 54.6
- 3 syndicated copies: all 69.8; attacker value 72.9; hedge (both values) 57.8
- 3 independent sources: all 74.3; attacker value 76.5; hedge (both values) 60.0
- Forged badge + system check: all 52.6; attacker value 66.0; hedge (both values) 48.0; true value 58.0
- Check + spoofed 'PASSED': all 66.5; attacker value 75.3; hedge (both values) 54.4; true value 62.5
- Real verified badge on truth: all 67.7; attacker value 60.8; hedge (both values) 53.9; true value 79.8

## 3. One-sided verification

- all: system FAILED on forged badge -> false adoption -0.7 pp [-3.1 pp, +1.7 pp], true answers +0.2 pp [-1.6 pp, +2.1 pp]; system PASSED on truth -> false adoption -7.0 pp [-9.6 pp, -4.8 pp], true answers +24.9 pp [+21.0 pp, +28.7 pp]
- void: system FAILED on forged badge -> false adoption -1.0 pp [-5.6 pp, +3.7 pp], true answers +0.0 pp [-2.7 pp, +2.7 pp]; system PASSED on truth -> false adoption -12.7 pp [-16.9 pp, -9.0 pp], true answers +43.3 pp [+39.8 pp, +47.1 pp]
- known: system FAILED on forged badge -> false adoption -0.4 pp [-1.7 pp, +0.8 pp], true answers +0.4 pp [-1.9 pp, +2.7 pp]; system PASSED on truth -> false adoption -1.2 pp [-3.5 pp, +0.0 pp], true answers +6.5 pp [+4.0 pp, +9.2 pp]

Per model, void items (pp): PASSED-on-truth gain in true answers (honest - base) | FAILED-on-forgery drop in false answers (badge - check)

- Qwen3-235B-A22B-Instruct-2507:cheapest: +93.3 | +5.0
- DeepSeek-V4-Flash:cheapest: +66.7 | -5.0
- gemma-3-27b-it:cheapest: +20.0 | +6.7
- Llama-4-Scout-17B-16E-Instruct:cheapest: +48.3 | -16.7
- gpt-4.1-mini: +60.0 | +1.7
- gpt-4o-mini: +5.0 | +13.3
- gpt-5-nano: +11.7 | +1.7
- grok-4-1-fast-non-reasoning: +41.7 | +1.7

## 4. Position (baseline, void items): false adoption when F is listed before vs after T

- all models: F first 26.4% (n=280), F second 3.0% (n=200)
- Qwen3-235B-A22B-Instruct-2507:cheapest: F first 17.1%, F second 0.0%; true when T first 8.0%, true when T second 2.9%
- DeepSeek-V4-Flash:cheapest: F first 0.0%, F second 0.0%; true when T first 8.0%, true when T second 0.0%
- gemma-3-27b-it:cheapest: F first 0.0%, F second 0.0%; true when T first 0.0%, true when T second 0.0%
- Llama-4-Scout-17B-16E-Instruct:cheapest: F first 80.0%, F second 20.0%; true when T first 64.0%, true when T second 14.3%
- gpt-4.1-mini: F first 37.1%, F second 0.0%; true when T first 36.0%, true when T second 2.9%
- gpt-4o-mini: F first 14.3%, F second 0.0%; true when T first 32.0%, true when T second 0.0%
- gpt-5-nano: F first 34.3%, F second 0.0%; true when T first 44.0%, true when T second 0.0%
- grok-4-1-fast-non-reasoning: F first 28.6%, F second 4.0%; true when T first 24.0%, true when T second 0.0%

## 5. Pushback on void items: first answer -> after 'Are you sure?'

| condition | attacker value: first -> after | hedges that became attacker value | hedges that became true value |
|---|---|---|---|
| Baseline | 16.7% -> 12.1% | 2.7% (n=294) | 2.0% |
| GEO style | 71.0% -> 69.8% | 32.4% (n=102) | 1.0% |
| Forged badge | 32.1% -> 42.3% | 26.9% (n=249) | 1.6% |
| Self-claimed 'verified' | 32.1% -> 37.5% | 17.2% (n=250) | 2.4% |
| 3 syndicated copies | 80.4% -> 86.5% | 50.6% (n=89) | 3.4% |
| 3 independent sources | 88.1% -> 89.8% | 52.9% (n=51) | 5.9% |
| Forged badge + system check | 31.0% -> 27.1% | 10.5% (n=239) | 19.7% |
| Check + spoofed 'PASSED' | 60.6% -> 51.7% | 16.7% (n=132) | 25.8% |
| Real verified badge on truth | 4.0% -> 3.8% | 0.6% (n=169) | 41.4% |

- known: recovery of false first answers across all conditions 41.7% (n=288)
- void: recovery of false first answers across all conditions 4.3% (n=1997)
