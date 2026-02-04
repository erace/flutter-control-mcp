# Flutter Control MCP - Integration Test Report

**Generated:** 2026-02-04T14:00:04

## 3-Backend Comparison

| Operation | Platform | Unified (ms) | Maestro (ms) | Driver (ms) | Notes |
|-----------|----------|--------------|--------------|-------------|-------|
| assert_not_visible | ios | 923 | 833 | 5 |  |
| assert_visible | ios | 500 | 407 | 4 |  |
| assert_visible_btn | ios | 308 | 319 | 3 | Unified → Maestro |
| assert_visible_key | ios | 3 | N/A | 3 | Unified → Driver |
| tap_key | ios | 398 | N/A | 400 | Unified → Driver |
| tap_text | ios | 6377 | 1549 | 27 |  |
| tap_text_decrement | ios | 1585 | 1488 | 9 |  |
| tap_type | ios | 396 | N/A | 399 | Unified → Driver |

## Driver-Only Operations

| Operation | Android (ms) | iOS (ms) |
|-----------|--------------|----------|
| assert_not_visible_key | N/A | 5 |
| driver_connect | N/A | 4 |
| driver_disconnect | N/A | 2 |
| driver_discover | N/A | 13 |
| driver_tap_key | N/A | 448 |
| driver_tap_text | N/A | 352 |
| get_text_key | N/A | 4 |
| get_text_text | N/A | 3 |
| version | N/A | 31 |
| widget_tree | N/A | 99 |

## Summary

- **Total operations:** 31
- **Successful:** 31
- **Failed:** 0
