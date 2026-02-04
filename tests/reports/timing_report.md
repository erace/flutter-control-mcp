# Flutter Control MCP - Integration Test Report

**Generated:** 2026-02-04T19:47:13

## 3-Backend Comparison

| Operation | Platform | Unified (ms) | Maestro (ms) | Driver (ms) | Notes |
|-----------|----------|--------------|--------------|-------------|-------|
| assert_not_visible | android | 1365 | 1308 | 139 |  |
| assert_visible | android | 69089 | 7278 | 59 |  |
| assert_visible_btn | android | 592 | 485 | 22 |  |
| assert_visible_key | android | 28 | N/A | 39 | Unified → Driver |
| tap_key | android | 646 | N/A | 653 | Unified → Driver |
| tap_text | android | 2468 | 3943 | 103 |  |
| tap_text_decrement | android | 3469 | 2376 | 46 |  |
| tap_type | android | 127 | N/A | 748 |  |

## Maestro-Only Operations

| Operation | Android (ms) | iOS (ms) |
|-----------|--------------|----------|
| clear_text | 11424 | N/A |
| double_tap | 28383 | N/A |
| double_tap_btn | 7524 | N/A |
| enter_text | 5510 | N/A |
| enter_text_finder | 41941 | N/A |
| enter_text_special | 5252 | N/A |
| long_press | 29441 | N/A |
| long_press_btn | 6394 | N/A |
| screenshot_maestro | 2173 | N/A |
| swipe_down | 2262 | N/A |
| swipe_left | 2204 | N/A |
| swipe_right | 2367 | N/A |
| swipe_up | 2942 | N/A |
| tap_id | 41940 | N/A |

## Driver-Only Operations

| Operation | Android (ms) | iOS (ms) |
|-----------|--------------|----------|
| assert_not_visible_key | 115 | N/A |
| driver_connect | 48 | N/A |
| driver_disconnect | 5 | N/A |
| driver_discover | 798 | N/A |
| driver_tap_key | 745 | N/A |
| driver_tap_text | 744 | N/A |
| get_text_key | 1093 | N/A |
| get_text_text | 155 | N/A |
| version | 44 | N/A |
| widget_tree | 2980 | N/A |

## Screenshot Comparison

| Method | Android (ms) | iOS (ms) |
|--------|--------------|----------|
| Maestro | 2173 | N/A |

## Summary

- **Total operations:** 51
- **Successful:** 51
- **Failed:** 0
