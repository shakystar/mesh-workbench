# Project instructions

- Read README.md and docs/STATUS.md before implementation.
- This is a standalone open-source Blender tool. Keep character/reference assets, private data, credentials and machine-specific paths out of tracked files.
- Preserve inputs. Topology edits and model combinations create new objects; deformation edits use reversible layers. Do not silently invalidate selections or masks.
- Use factory-startup background Blender for tests. Do not modify user preferences or install global add-ons.
- 검증은 요청된 변경에 직접 관련된 기하학적 효과와 실패 경로로 제한합니다. `tests/blender_tests.py`와 예제 레시피도 변경 영향에 필요한 범위만 실행합니다.
- 사용자의 명시적 요청 없이 OS별·Blender 버전별 호환성 검증, 전체 회귀 검사, 추가 렌더 비교 등으로 검증 범위를 확대하지 않습니다. 프로젝트의 일반 검증 지침을 확대 검증의 근거로 삼지 않습니다.
- 관련 검증이 통과하면 종료합니다. 새 변경이나 구체적인 실패 근거 없이 검사를 반복하거나 검증 항목을 추가하지 않습니다. 문서만 수정한 경우 Blender나 테스트를 실행하지 않습니다.
- Blender 렌더와 무거운 형상 검증은 동시에 실행하지 않습니다. Blender는 한 번에 1개만 실행하고 CPU 스레드는 2개로 제한합니다. 수치 라이브러리의 스레드 수도 함께 제한합니다.
- Record tested Blender versions and remaining limits. Do not claim arbitrary retopology, collision-free patterns or production-ready rigs.
- Generated runs belong in ignored `runs/`. Public preview images must come only from included procedural examples.
- 인체 예제·설정은 `examples/human/`에 모읍니다. 익명 테스트 산출물은 `runs/_archive/tests/`에 저장합니다.
- `.git`과 사용자가 제외한 `.venv` 외에는 폴더별 직접 파일 수를 10개 이하로 유지합니다. 하위 폴더는 개수에 포함하지 않습니다. 모델·기능·파일 유형별로 분류하고, 파일 추가·산출물 생성 후 `python scripts/check_layout.py`로 확인합니다. 경로 이동 시 코드·문서 참조도 갱신합니다.
- 모델 형상을 변경한 결과 보고에는 현재 저장 모델의 대표 렌더 1~2장을 함께 보여줍니다. 도구 수치 검증을 시각적 완성도 검증으로 표현하지 않습니다. 코드·문서만 바꾼 경우에는 렌더하지 않습니다.
