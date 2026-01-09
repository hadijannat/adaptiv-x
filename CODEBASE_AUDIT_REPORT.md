# Adaptiv-X Codebase Audit Report

**Date:** 2026-01-09
**Auditor:** Claude Code
**Scope:** Full codebase review for bugs, issues, placeholders, and TODOs

---

## Executive Summary

The Adaptiv-X codebase is well-structured and follows modern best practices for Python/FastAPI and React/TypeScript development. The code quality is generally high with proper type hints, comprehensive error handling, and clean architecture. However, several issues were identified that should be addressed before production deployment.

**Total Issues Found:** 18
- **Critical:** 0
- **High:** 3
- **Medium:** 8
- **Low:** 7

---

## Issues by Category

### 1. Configuration Issues

#### 1.1 Port Mismatch Between Services (HIGH)
**Location:** `services/skill-broker/src/skill_broker/config.py:15` and `services/job-dispatcher/src/job_dispatcher/config.py:10`

**Issue:** Both skill-broker and job-dispatcher default to port 8000, which will cause conflicts if both services are run on the same host without configuration changes.

```python
# skill-broker/config.py
port: int = 8000  # Should be 8002 per docker-compose

# job-dispatcher/config.py
port: int = 8000  # Should be 8003 per docker-compose
```

**Expected Ports (per docker-compose.yml):**
- adaptiv-monitor: 8011
- skill-broker: 8002
- job-dispatcher: 8003
- fault-injector: 8004

**Recommendation:** Update default ports to match docker-compose expectations or document that PORT environment variable must be set.

---

#### 1.2 Hardcoded MinIO Credentials (MEDIUM)
**Location:** `services/adaptiv-monitor/src/adaptiv_monitor/config.py:27-28`

**Issue:** Default MinIO credentials are hardcoded in the source code.

```python
minio_access_key: str = "adaptivx"
minio_secret_key: str = "adaptivx123"
```

**Recommendation:** While acceptable for development, production deployments should require these via environment variables without defaults, or use a secrets management solution.

---

### 2. Code Quality Issues

#### 2.1 Unused Import in FMU Runner (LOW)
**Location:** `services/adaptiv-monitor/src/adaptiv_monitor/fmu_runner.py:18`

**Issue:** `download_file` from `fmpy.util` is imported but never used.

```python
from fmpy.util import download_file  # Never used
```

**Recommendation:** Remove the unused import.

---

#### 2.2 Unused `numpy` Import (LOW)
**Location:** `services/adaptiv-monitor/src/adaptiv_monitor/fmu_runner.py:17`

**Issue:** `numpy` is imported as `np` but never used in the file.

```python
import numpy as np  # np is never used
```

**Recommendation:** Remove the unused import.

---

#### 2.3 Potential Race Condition in Periodic Evaluation (MEDIUM)
**Location:** `services/skill-broker/src/skill_broker/main.py:200-216`

**Issue:** The `_periodic_evaluation()` function runs in an infinite loop without proper exception handling for individual asset evaluations.

```python
async def _periodic_evaluation() -> None:
    while True:
        await asyncio.sleep(settings.polling_interval_seconds)
        # ... exception in one asset could affect others
        for asset_id in assets:
            health_index = await aas_patcher.get_health_index(asset_id)
            # No try/except around individual asset processing
```

**Recommendation:** Wrap individual asset processing in try/except to prevent one failing asset from blocking others.

---

#### 2.4 Missing Input Validation for Tolerance Parsing (MEDIUM)
**Location:** `services/job-dispatcher/src/job_dispatcher/main.py:342-357`

**Issue:** The `_parse_tolerance_mm()` function uses a regex but doesn't fully validate input format.

```python
def _parse_tolerance_mm(value: str) -> float | None:
    value = value.strip().lower()
    match = re.search(r"([0-9]*\\.?[0-9]+)", value)  # Regex has escaped backslash issue
```

**Note:** The regex `r"([0-9]*\\.?[0-9]+)"` has an incorrectly escaped backslash. Should be `r"([0-9]*\.?[0-9]+)"`.

**Recommendation:** Fix the regex pattern.

---

### 3. Potential Runtime Issues

#### 3.1 Global State in Services (MEDIUM)
**Location:** All service `main.py` files

**Issue:** Services use global variables for state management (e.g., `basyx_client`, `mqtt_client`). While acceptable for single-instance deployments, this can cause issues with testing and multi-worker configurations.

```python
# Global instances
settings = Settings()
basyx_client: BasyxClient | None = None
fmu_runner: FMURunner | None = None
```

**Recommendation:** Consider using FastAPI's dependency injection system or a proper state management pattern for better testability.

---

#### 3.2 Missing Graceful Shutdown for MQTT (MEDIUM)
**Location:** `services/adaptiv-monitor/src/adaptiv_monitor/mqtt_client.py:63-68`

**Issue:** The MQTT client uses `loop_stop()` but doesn't wait for pending messages to be published before disconnecting.

```python
async def disconnect(self) -> None:
    if self._client:
        self._client.loop_stop()
        self._client.disconnect()  # May drop pending messages
```

**Recommendation:** Add a brief wait or flush pending messages before disconnect.

---

#### 3.3 Unbounded In-Memory Lists (MEDIUM)
**Location:** `services/job-dispatcher/src/job_dispatcher/main.py:106`

**Issue:** `job_history` is an unbounded list that will grow indefinitely.

```python
job_history: list[JobAssignment] = []
# ... later:
job_history.append(assignment)  # No limit
```

**Recommendation:** Add a maximum size limit similar to the audit_log in skill-broker (which properly uses `MAX_AUDIT_LOG = 1000`).

---

### 4. Documentation/Placeholder Issues

#### 4.1 Placeholder FMU URL in AAS Package (LOW)
**Location:** `aas/packages/milling-01.json:271`

**Issue:** The FMU file URL references the internal Docker network name `minio:9000` which won't work from outside containers.

```json
"value": "http://minio:9000/adaptivx-fmu/bearing_wear.fmu"
```

**Recommendation:** Document that this URL should be updated for non-Docker deployments or use configurable URL.

---

#### 4.2 Commented-Out Docker Services (LOW)
**Location:** `deploy/compose/docker-compose.yml:133-229`

**Issue:** All Adaptiv-X application services are commented out in docker-compose.yml.

**Recommendation:** Consider providing a separate `docker-compose.dev.yml` or `docker-compose.override.yml` for the full stack, or document how to enable services.

---

### 5. Security Considerations

#### 5.1 No Authentication on API Endpoints (HIGH)
**Location:** All service `main.py` files

**Issue:** All API endpoints are exposed without authentication. While Keycloak is mentioned in the deploy structure, it's not integrated.

**Recommendation:** For production, implement JWT authentication using the Keycloak infrastructure that's already prepared in `deploy/keycloak/`.

---

#### 5.2 CORS Wildcard in Docker Compose (HIGH)
**Location:** `deploy/compose/docker-compose.yml:19-20`

**Issue:** BaSyx services are configured with `BASYX_CORS_ALLOWED_ORIGINS: "*"` which allows any origin.

```yaml
BASYX_CORS_ALLOWED_ORIGINS: "*"
BASYX_CORS_ALLOWED_METHODS: "GET,POST,PATCH,PUT,DELETE,OPTIONS,HEAD"
```

**Recommendation:** Restrict to specific origins in production.

---

#### 5.3 Debug Mode Available in Config (LOW)
**Location:** All service config.py files

**Issue:** All services have a `debug: bool = False` setting that enables Uvicorn reload mode. Ensure this is never enabled in production.

**Recommendation:** Add documentation warning about debug mode implications.

---

### 6. Frontend Issues

#### 6.1 Console Logging in Production Code (LOW)
**Location:** `dashboard/src/api/aas.ts:30`, `dashboard/src/hooks/useMqtt.ts:22,43,48`

**Issue:** Multiple `console.log` and `console.error` calls remain in production code.

```typescript
console.error('Failed to list assets:', error);
console.log('MQTT connected');
console.error('Failed to parse MQTT message:', e);
```

**Recommendation:** Replace with proper logging infrastructure or remove for production builds.

---

#### 6.2 Hardcoded MQTT Broker URL (LOW)
**Location:** `dashboard/src/hooks/useMqtt.ts:6`

**Issue:** MQTT broker URL has a hardcoded fallback.

```typescript
const MQTT_BROKER = import.meta.env.VITE_MQTT_BROKER_URL ?? 'ws://localhost:9883';
```

**Recommendation:** Document that `VITE_MQTT_BROKER_URL` must be set in production.

---

### 7. Missing Features / Incomplete Implementations

#### 7.1 Bidding Mode Configuration Unused (MEDIUM)
**Location:** `services/job-dispatcher/src/job_dispatcher/config.py:21-22`

**Issue:** `enable_bidding_mode` and `bid_timeout_seconds` are defined but not used in the codebase.

```python
enable_bidding_mode: bool = True
bid_timeout_seconds: float = 5.0
```

**Recommendation:** Either implement the feature or remove the configuration.

---

## Positive Observations

The codebase demonstrates several excellent practices:

1. **Strong Type Hints:** Comprehensive Python type hints throughout the codebase
2. **Pydantic Models:** Well-structured data validation using Pydantic v2
3. **Async/Await:** Proper async patterns for I/O operations
4. **FastAPI Lifespan:** Correct use of async context managers for startup/shutdown
5. **Error Handling:** Generally good exception handling with proper logging
6. **Modular Architecture:** Clean separation of concerns across services
7. **AAS Compliance:** Proper Asset Administration Shell structure following IDTA standards
8. **Redux State Management:** Well-organized Redux slices in the frontend
9. **Proper Audit Logging:** skill-broker implements bounded audit log with MAX_AUDIT_LOG limit

---

## Recommendations Summary

### Immediate Actions (Before Production)
1. Fix port defaults in skill-broker and job-dispatcher configs
2. Implement authentication on API endpoints
3. Restrict CORS origins in production
4. Fix the regex pattern in tolerance parsing

### Short-term Improvements
1. Remove unused imports
2. Add graceful MQTT shutdown
3. Add size limits to job_history list
4. Add try/except around individual asset processing in periodic evaluation

### Long-term Improvements
1. Replace global state with dependency injection
2. Implement proper logging infrastructure for frontend
3. Consider secrets management for credentials
4. Complete bidding mode implementation or remove unused config

---

## Files Reviewed

- `services/adaptiv-monitor/src/adaptiv_monitor/*.py` (7 files)
- `services/skill-broker/src/skill_broker/*.py` (5 files)
- `services/job-dispatcher/src/job_dispatcher/*.py` (4 files)
- `services/fault-injector/src/fault_injector/*.py` (3 files)
- `dashboard/src/**/*.{ts,tsx}` (9 files)
- `aas/packages/*.json` (2 files)
- `aas/submodels/**/*.json` (3 files)
- `deploy/compose/docker-compose.yml`
- Configuration files across all services

---

*Report generated by Claude Code - Codebase Audit Tool*
