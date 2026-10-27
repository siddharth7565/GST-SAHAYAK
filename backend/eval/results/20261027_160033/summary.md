# GST Sahayak evaluation (2026-10-27 16:00)

Retrieved top_k=8 chunks once per question; every provider got the same prompt. Providers: (retrieval only).

## Retrieval

| Question | Type | Best score | Evidence | Expected-section recall | Retrieved sections |
|---|---|---|---|---|---|
| q01_flagship | answerable | 0.4131 | weak | 100% | IGST 2, IGST 13, CGST 24, CGST 22, CGST 2, IGST 16 |
| q02_threshold_local | answerable | 0.4659 | weak | 100% | IGST 12, CGST 24, CGST 22, IGST 8, IGST 13, CGST 2 |
| q03_itc_conditions | answerable | 0.9165 | strong | 100% | CGST 16 |
| q04_itc_depreciation | answerable | 0.588 | weak | 100% | CGST 16, CGST 17, CGST 31, CGST 18 |
| q05_voluntary | answerable | 0.4268 | weak | 100% | CGST 24, CGST 22, CGST 2, CGST 25, CGST 23 |
| q06_not_liable | answerable | 0.5826 | weak | 100% | CGST 24, CGST 22, CGST 2, CGST 23, CGST 25 |
| q07_zero_rated | answerable | 0.5757 | weak | 100% | IGST 2, IGST 13, IGST 16, IGST 12 |
| q08_pos_outside_india | answerable | 0.7179 | strong | 100% | IGST 2, IGST 13, IGST 16, IGST 12 |
| q09_interstate | answerable | 0.6664 | strong | 100% | CGST 24, IGST 7, IGST 5, IGST 8, IGST 2 |
| q10_time_of_supply | answerable | 0.5912 | weak | 100% | CGST 13, CGST 9, CGST 7, CGST 15, CGST 2 |
| q11_tax_invoice | answerable | 0.7239 | strong | 100% | CGST 31, CGST 24, CGST 37, CGST 16, CGST 2, CGST 9 |
| q12_value_of_supply | answerable | 0.6003 | weak | 100% | CGST 15, CGST 13, CGST 18, CGST 9, CGST 31, CGST 16 |
| q13_returns | answerable | 0.3732 | insufficient | 0% | CGST 24, CGST 22, CGST 2, CGST 25, CGST 23 |
| q14_reverse_charge | answerable | 0.4617 | weak | 100% | IGST 5, CGST 2, CGST 9, CGST 16, CGST 24, IGST 2 |
| q15_weather | out_of_scope | 0.2251 | insufficient | - | CGST 2, IGST 2, IGST 13, IGST 12, CGST 13 |
| q16_income_tax | out_of_scope | 0.4241 | weak | - | CGST 39, CGST 37, CGST 25, CGST 16, CGST 2 |
| q17_mutual_funds | out_of_scope | 0.2283 | insufficient | - | CGST 2 |
| q18_rate_borderline | borderline | 0.2715 | insufficient | - | CGST 9, CGST 7, CGST 15, CGST 2, CGST 31, IGST 5 |

Threshold calibration: lowest answerable best_score = 0.3732, highest out-of-scope = 0.4241.
They OVERLAP, so no single threshold separates them; improve retrieval or rely on the model's own refusal.
Refusal by the retrieval guard (no LLM call): 3/4 of the questions that should be refused.
