# Flutter Control MCP - Integration Test Report

**Generated:** 2026-02-03T23:21:01

## 3-Backend Comparison

| Operation | Platform | Unified (ms) | Maestro (ms) | Driver (ms) | Notes |
|-----------|----------|--------------|--------------|-------------|-------|
| assert_not_visible | ios | 839 | 798 | 6 | Unified → Maestro |
| assert_visible | ios | 6297 | 333 | 12 |  |
| assert_visible_btn | ios | 313 | 326 | 4 | Unified → Maestro |
| assert_visible_key | ios | 4 | N/A | 3 | Unified → Driver |
| tap_key | ios | 411 | N/A | 391 | Unified → Driver |
| tap_text | ios | 15004 | 20986 | 402 |  |
| tap_text_decrement | ios | 19254 | 6082 | 9 |  |
| tap_type | ios | 394 | N/A | 396 | Unified → Driver |

## Maestro-Only Operations

| Operation | Android (ms) | iOS (ms) |
|-----------|--------------|----------|
| clear_text | N/A | 4042 |
| double_tap | N/A | 29692 |
| double_tap_btn | N/A | 6138 |
| enter_text | N/A | 7206 |
| enter_text_finder | N/A | 35280 |
| enter_text_special | N/A | 7734 |
| long_press | N/A | 20429 |
| long_press_btn | N/A | 21854 |
| screenshot_maestro | N/A | 2708 |
| swipe_down | N/A | 2039 |
| swipe_left | N/A | 1391 |
| swipe_right | N/A | 1345 |
| swipe_up | N/A | 2035 |

## Driver-Only Operations

| Operation | Android (ms) | iOS (ms) |
|-----------|--------------|----------|
| assert_not_visible_key | N/A | 4 |
| driver_connect | N/A | 4 |
| driver_disconnect | N/A | 2 |
| driver_discover | N/A | 12 |
| driver_tap_key | N/A | 400 |
| driver_tap_text | N/A | 402 |
| get_text_key | N/A | 5 |
| get_text_text | N/A | 4 |
| version | N/A | 17 |
| widget_tree | N/A | 106 |

## Screenshot Comparison

| Method | Android (ms) | iOS (ms) |
|--------|--------------|----------|
| Maestro | N/A | 2708 |

## Summary

- **Total operations:** 50
- **Successful:** 50
- **Failed:** 0
