# OpenSpec Archive

이 디렉토리는 완료된 OpenSpec change 이력을 보관합니다.
현재 archive된 change는 없습니다.

## Archive 조건

Change는 다음 조건을 만족한 뒤 archive합니다.

- accepted spec이 필요한 경우 `openspec/specs/**/spec.md`에 반영되어 있습니다.
- implementation task가 완료되었거나 남은 항목이 명시적인 follow-up으로 분리되어 있습니다.
- verification 결과 또는 미검증 범위가 `tasks.md` 또는 PR body에 기록되어 있습니다.
- `openspec/specs/README.md` inventory가 필요한 경우 갱신되어 있습니다.

## 디렉토리 이름

완료된 change는 다음 형식으로 이동합니다.

```text
openspec/archive/<YYYY-MM-DD>-<change-id>/
```

Archive는 완료 이력입니다. 새 요구사항 변경은 archive를 직접 수정하지 말고 새 `openspec/changes/<change-id>/`를 만듭니다.
