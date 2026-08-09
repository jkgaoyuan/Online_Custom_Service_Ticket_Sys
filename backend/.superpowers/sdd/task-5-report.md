
## Fix Report — Task 5 Formula-Injection Test

**Status**: DONE
**Commit**: c82def6
**Test Summary**: 8 passed in `tests/test_export.py` — replaced ineffective `test_export_task_sanitizes_formula_injection` with direct `test_sanitize_for_export_directly` that asserts `_sanitize_for_export` correctly prefixes formula triggers (`=`, `+`, `-`, `@`) with an apostrophe and leaves normal text / non-strings unchanged.
**Concerns**: None.
