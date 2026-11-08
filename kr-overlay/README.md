# KR overlay (lumilumi486 포크 전용 보강)

이 포크는 원작자 저장소 [ddojuki-creator/dot-abyss-korean](https://github.com/ddojuki-creator/dot-abyss-korean)을
그대로 따라가면서, 이 폴더의 보강분만 그 위에 덧씌웁니다. 원작자 파일을 손으로 고치지 않습니다.

## 구조

| 경로 | 내용 |
| --- | --- |
| `additions/*.json` | 원작자 번역에 **없는** 문장만 채움. 원작자가 나중에 같은 문장을 번역하면 원작자 번역이 우선 |
| `overrides.json` | 원작자 번역을 **고치는** 항목(품질 수정). 고칠 당시의 원작자 값(`from`)을 함께 기록 |
| `tools/apply_overlay.py` | 위 두 가지를 `translations/`에 적용 |
| `tools/manifest.py` | `npm run manifest`와 같은 해시로 manifest 재생성 (원본 해시 재현 검증 완료) |
| `tools/extract_missing.py` | 게임 데이터(.dat)에서 번역 없는 원문 집계 |
| `tools/check_pairs.py` | 태그·변수·줄바꿈·일본어 잔존 검사 |
| `sync-upstream.sh` | 원작자 최신본을 받아 그대로 가져온 뒤 이 보강을 다시 적용 |

## 원작자 업데이트와의 호환 규칙

1. 동기화하면 `translations/`는 원작자 최신본으로 통째로 교체되고, 이 폴더만 유지됩니다.
2. `additions`는 빈 곳만 채웁니다. 충돌이 생기지 않습니다.
3. `overrides`는 원작자 값이 기록된 `from`과 같을 때만 적용합니다. 원작자가 그 문장을 바꿨으면 적용하지 않고
   CONFLICT로 보고합니다(원작자 값 유지). 보고된 항목은 사람이 다시 판단합니다.
4. 성적인 장면·문장은 이 보강에서 다루지 않습니다.

## additions 형식

```json
{ "m_items": { "日本語原文": "한국어" } }      // outgame + static의 해당 표 전체 필드
{ "_outgame_only": { "日本語原文": "한국어" } } // 화면 수집 문장 등 outgame 전용
```
