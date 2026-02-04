# Issues to Fix - Flutter Control MCP

**Generated:** 2026-02-04 after full test run (57 passed, 2 skipped in 5:32)

## Critical Performance Issues

### 1. `assert_visible` unified backend extremely slow (69s)
- **Location:** `flutter_control/mcp/tools.py`
- **Symptoms:** Unified backend takes 69 seconds vs 7s Maestro, 59ms Driver
- **Likely cause:** Fallback logic trying multiple backends with full timeouts
- **Fix:** Check fallback logic, reduce timeout, or prefer Driver for this operation

### 2. `double_tap` and `long_press` very slow (28-29s)
- **Location:** `flutter_control/maestro/wrapper.py`
- **Symptoms:** Operations taking ~30s (close to timeout)
- **Likely cause:** Element not found causing timeout, or MCP `run_flow` issue
- **Fix:** Verify flow YAML format, check if test app buttons support these gestures

### 3. `enter_text_finder` timeout (42s)
- **Location:** `tests/test_text_input.py`
- **Symptoms:** Test times out looking for text field
- **Likely cause:** Test app text field not visible or has different text
- **Fix:** Verify test app UI, update finder text to match actual element

### 4. `tap_id` always times out (42s)
- **Location:** `tests/test_tap.py::TestTapById`
- **Symptoms:** Android resource ID `increment_button` not found
- **Root cause:** Flutter apps don't expose Android resource IDs by default
- **Fix:** Either:
  - Skip this test with `@pytest.mark.skip(reason="Flutter doesn't expose resource IDs")`
  - Or add `android:id` to test app via platform-specific code

### 5. `clear_text` slow (11s)
- **Location:** `flutter_control/maestro/wrapper.py`
- **Symptoms:** Clear text takes 11s via Maestro
- **Likely cause:** `eraseText` command slower than expected
- **Fix:** Low priority - works but slow

## Configuration Issues

### 6. ADB Proxy not auto-started on service restart
- **Location:** `flutter_control/mcp/server.py`
- **Symptoms:** Tests fail with "Failed to install app" when proxy not running
- **Fix:** Auto-start ADB proxy in `@app.on_event("startup")` handler

### 7. Maestro device discovery slow (~3s overhead per new connection)
- **Location:** `flutter_control/maestro/mcp_client.py`
- **Symptoms:** First Maestro operation adds 3s overhead for device lookup
- **Fix:** Pre-cache device ID during startup, similar to how we pre-start Maestro MCP

## Test Infrastructure

### 8. iOS tests cannot run from VM
- **Tests:** `test_upload_real_ios_app`, `test_boot_emulator_already_running`
- **Reason:** VM doesn't have iOS simulator
- **Fix:** Run iOS tests on host Mac (port 9227)

## Documentation Needed

### 9. Backend selection guide
- **Driver:** 50-750ms (fast, needs driver extension)
- **Maestro:** 2-7s (slower, works on any app)
- Document when to use `backend: "driver"` vs `backend: "maestro"` in finders

### 10. Timing report improvements
- Add ADB screenshot timing (~300-400ms)
- Add smart screenshot comparison (ADB vs simctl vs Maestro)

---

## Performance Summary

| Category | Fast ✓ | Slow ⚠ | Very Slow ✗ |
|----------|--------|--------|-------------|
| Driver ops | 50-750ms | - | - |
| Maestro tap | - | 2-4s | - |
| Maestro gestures | - | - | 7-30s |
| Screenshots (ADB) | 300-400ms | - | - |
| Screenshots (Maestro) | - | 2s | - |

## Priority Order

1. **P0:** Fix ADB proxy auto-start (blocks tests)
2. **P1:** Fix `assert_visible` unified slowness (69s → should be <1s)
3. **P1:** Fix `double_tap`/`long_press` (30s → should be 3-4s)
4. **P2:** Skip or fix `tap_id` test
5. **P2:** Pre-cache Maestro device ID at startup
6. **P3:** Document backend selection
