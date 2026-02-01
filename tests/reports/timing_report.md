# Flutter Control MCP - Integration Test Report

**Generated:** 2026-02-01T23:18:52

## 3-Backend Comparison

| Operation | Platform | Unified (ms) | Maestro (ms) | Driver (ms) | Notes |
|-----------|----------|--------------|--------------|-------------|-------|
| assert_not_visible | android | 12145 | 11764 | 16 |  |
| assert_visible | android | 12137 | 11502 | 45 |  |
| assert_visible_btn | android | 11695 | 11435 | 9 |  |
| assert_visible_key | android | 11 | N/A | 8 | Unified → Driver |
| tap_key | android | 667 | N/A | 652 | Unified → Driver |
| tap_text | android | 14905 | 14122 | 1071 |  |
| tap_text_decrement | android | 13886 | 13960 | 23 |  |
| tap_type | android | 25 | N/A | 15 | Unified → Driver |

## Maestro-Only Operations

| Operation | Android (ms) | iOS (ms) |
|-----------|--------------|----------|
| clear_text | 15914 | N/A |
| double_tap | 28554 | N/A |
| double_tap_btn | 14557 | N/A |
| enter_text | 13430 | N/A |
| enter_text_finder | 28222 | N/A |
| enter_text_special | 14061 | N/A |
| long_press | 28282 | N/A |
| long_press_btn | 16310 | N/A |
| screenshot_adb | 282 | N/A |
| screenshot_adb_0 | 205 | N/A |
| screenshot_adb_1 | 195 | N/A |
| screenshot_adb_2 | 196 | N/A |
| screenshot_maestro | 13082 | N/A |
| swipe_down | 12428 | N/A |
| swipe_left | 12602 | N/A |
| swipe_right | 12588 | N/A |
| swipe_up | 12484 | N/A |
| tap_id | 28541 | N/A |

## Driver-Only Operations

| Operation | Android (ms) | iOS (ms) |
|-----------|--------------|----------|
| assert_not_visible_key | 12 | N/A |
| driver_connect | 14 | N/A |
| driver_disconnect | 2 | N/A |
| driver_discover | 767 | N/A |
| driver_tap_key | 20 | N/A |
| driver_tap_text | 659 | N/A |
| get_text_key | 8 | N/A |
| get_text_text | 8 | N/A |
| get_text_type | 26 | N/A |
| version | 22 | N/A |
| widget_tree | 210 | N/A |

## Screenshot Comparison

| Method | Android (ms) | iOS (ms) |
|--------|--------------|----------|
| ADB | 282 | N/A |
| Maestro | 13082 | N/A |
| **Speedup** | **46x** | - |

## Summary

- **Total operations:** 52
- **Successful:** 52
- **Failed:** 0
