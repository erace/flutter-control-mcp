# Flutter Control MCP - Integration Test Report

**Generated:** 2026-02-04T18:46:15

## 3-Backend Comparison

| Operation | Platform | Unified (ms) | Maestro (ms) | Driver (ms) | Notes |
|-----------|----------|--------------|--------------|-------------|-------|
| assert_not_visible | android | 937 | 1055 | 41 |  |
| assert_visible | android | 1066 | 289 | 16 |  |
| assert_visible_btn | android | 258 | 312 | 9 |  |
| assert_visible_key | android | 8 | N/A | 6 | Unified → Driver |
| tap_key | android | 716 | N/A | 735 | Unified → Driver |
| tap_text | android | 4913 | 2325 | 94 |  |
| tap_text_decrement | android | 3125 | 4067 | 61 |  |
| tap_type | android | 48 | N/A | 741 |  |

## Maestro-Only Operations

| Operation | Android (ms) | iOS (ms) |
|-----------|--------------|----------|
| clear_text | 6785 | N/A |
| double_tap | 30866 | N/A |
| double_tap_btn | 3568 | N/A |
| enter_text | 2804 | N/A |
| enter_text_finder | 41006 | N/A |
| enter_text_special | 3213 | N/A |
| long_press | 32908 | N/A |
| long_press_btn | 10501 | N/A |
| screenshot_maestro | 1362 | N/A |
| swipe_down | 1861 | N/A |
| swipe_left | 2288 | N/A |
| swipe_right | 1854 | N/A |
| swipe_up | 2622 | N/A |
| tap_id | 45223 | N/A |

## Driver-Only Operations

| Operation | Android (ms) | iOS (ms) |
|-----------|--------------|----------|
| assert_not_visible_key | 33 | N/A |
| driver_connect | 31 | N/A |
| driver_disconnect | 4 | N/A |
| driver_discover | 190 | N/A |
| driver_tap_key | 706 | N/A |
| driver_tap_text | 701 | N/A |
| get_text_key | 38 | N/A |
| get_text_text | 26 | N/A |
| version | 29 | N/A |
| widget_tree | 777 | N/A |

## Screenshot Comparison

| Method | Android (ms) | iOS (ms) |
|--------|--------------|----------|
| Maestro | 1362 | N/A |

## Summary

- **Total operations:** 51
- **Successful:** 51
- **Failed:** 0
