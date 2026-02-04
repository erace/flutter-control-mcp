# Flutter Control MCP - Integration Test Report

**Generated:** 2026-02-04T13:51:14

## 3-Backend Comparison

| Operation | Platform | Unified (ms) | Maestro (ms) | Driver (ms) | Notes |
|-----------|----------|--------------|--------------|-------------|-------|
| assert_not_visible | ios | 909 | 899 | 6 | Unified → Maestro |
| assert_visible | ios | 11843 | 348 | 15 |  |
| assert_visible_btn | ios | 329 | 321 | 19 | Unified → Maestro |
| assert_visible_key | ios | 5 | N/A | 3 | Unified → Driver |

## Maestro-Only Operations

| Operation | Android (ms) | iOS (ms) |
|-----------|--------------|----------|
| double_tap | N/A | 28435 |
| double_tap_btn | N/A | 5635 |
| long_press | N/A | 39490 |
| swipe_down | N/A | 2041 |
| swipe_left | N/A | 1336 |
| swipe_right | N/A | 1448 |
| swipe_up | N/A | 2192 |

## Driver-Only Operations

| Operation | Android (ms) | iOS (ms) |
|-----------|--------------|----------|
| assert_not_visible_key | N/A | 3 |
| driver_connect | N/A | 8 |
| driver_disconnect | N/A | 2 |
| driver_discover | N/A | 13 |
| get_text_key | N/A | 5 |
| get_text_text | N/A | 3 |
| version | N/A | 23 |
| widget_tree | N/A | 102 |

## Summary

- **Total operations:** 26
- **Successful:** 26
- **Failed:** 0
