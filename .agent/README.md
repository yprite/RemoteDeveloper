# Project Context for AI Assistants

이 디렉토리는 AI 어시스턴트가 프로젝트를 이해하는 데 필요한 핵심 문서를 포함합니다.

## 문서 구조

### 필수 참조 (개발 시작 전 반드시 읽기)
- **[FAILURE_REGISTRY.md](./FAILURE_REGISTRY.md)**: 이전 반복에서의 실패 패턴과 교훈

### 작업중 참조
- **workflows/**: 반복적인 작업에 대한 워크플로우 정의

## AI 어시스턴트를 위한 지침

```yaml
# 새 기능 개발 시
before_coding:
  - read: FAILURE_REGISTRY.md
  - check: "Section 1 - 이 패턴을 반복하고 있지 않은가?"
  - check: "Section 4 - 권장 아키텍처를 따르고 있는가?"

during_coding:
  - rule: "에이전트는 순수 함수여야 함 (사이드 이펙트 없음)"
  - rule: "파일당 200 라인 이하"
  - rule: "단일 책임 원칙"

after_coding:
  - update: FAILURE_REGISTRY.md (새로 발견된 문제가 있다면)
```

## 다음 반복 개발 가이드

1. **시작 전**: `FAILURE_REGISTRY.md` 읽기
2. **설계 시**: 3-4개 에이전트로 시작, 레이어 분리 유지
3. **구현 시**: 에이전트는 순수 함수로, 사이드 이펙트는 Orchestrator에서
4. **완료 시**: 새로운 교훈을 `FAILURE_REGISTRY.md`에 추가
