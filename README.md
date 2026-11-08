# DeepTector 풀 데모 (deeptector-fulldemo)

팀 [Service](https://github.com/KWU-2026-Capstone-Team/Service) 저장소의 `main`(`3a44aa3`)에서 갈라져 나온 **통합 데모 저장소**입니다. 팀 Service 저장소는 수정하지 않았습니다. 실제 모델 분석(영상·사진), 사람 vs AI 대결 게임, 교육 콘텐츠, 공개 링크를 한 번에 재현합니다.

## 새 PC에서 시작하기

**필요한 것**: Git, Windows Python 3.11, Node.js 20 이상.
```powershell
winget install --id Python.Python.3.11 -e
winget install --id OpenJS.NodeJS.LTS -e
```

**설치** (처음 한 번만, 10~20분)
```powershell
git clone https://github.com/KWU-2026-Capstone-Team/deeptector-fulldemo.git
cd deeptector-fulldemo
powershell -ExecutionPolicy Bypass -File .\Setup-Workspace.ps1
```
`Setup-Workspace.ps1`이 하는 일:
- 팀 모델 저장소를 이 폴더 안 `AI-Generated-Media-Detection\`에 clone합니다. 가중치가 git에 포함돼 있습니다.
- 게임 저장소를 이 폴더와 나란한 `..\deepGame\`에 clone합니다.
- 가상환경 2개(`.venv`는 API용, `.venv-model`은 모델용)를 만듭니다.
- 프론트엔드를 빌드합니다.
- 게임 영상 24개와 저장된 AI 점수(`deeptector-backend/seeds/`)를 등록합니다.

다시 실행해도 안전합니다. 이미 끝난 단계는 건너뜁니다.

**실행**
```powershell
powershell -ExecutionPolicy Bypass -File .\Start-Service.ps1 -Mode real     # 게임 + 분석 → http://127.0.0.1:5173/
powershell -ExecutionPolicy Bypass -File .\Start-PublicTunnel.ps1           # 분석 전용 공개 링크(게임 꺼짐)
```
- 공개 링크를 쓰려면 먼저 `winget install --id Cloudflare.cloudflared -e`로 cloudflared를 설치하세요.
- 공개 링크는 켤 때마다 주소가 바뀌고, 이 PC가 켜져 있는 동안만 접속됩니다. 주소는 `.public\current-url.txt`에도 저장됩니다.
- 공개 링크에는 게임이 없습니다. 게임 영상(FaceForensics++ 계열)의 공개 재배포 권한을 확인하지 못했기 때문입니다.

**팀 Service `main` 대비 추가된 것**
| 기능 | 위치 |
|---|---|
| 사람 vs AI 대결 게임 (실시간 스코어, 결과 스코어보드, 라운드별 AI 판정) | `frontend/src/app/game`, `result`, `deeptector-backend/app/game.py` |
| 난이도별 영상이 부족하면 라운드 수 자동 조정 | `app/game.py` |
| 사진 분석 (공간 모델만 사용, 한계 표시) | `app/inference.py`, `app/policy.py`, `frontend/src/app/analysis` |
| 교육 콘텐츠 (나의 판별 리포트, 확인 체크리스트, 대응 요령, 신고처) | `frontend/src/lib/education.ts` (문구는 여기서 수정) |
| 공개 모드 (게임 끄기, IP별 세션 제한, 개인정보 안내) | `DEEPTECTOR_ENABLE_GAMES`, `DEEPTECTOR_SESSION_RATE_PER_IP_HOUR`, `Start-PublicTunnel.ps1` |
| Hugging Face Spaces 배포 파일 (PRO 구독 필요해 보류) | `deploy/huggingface/` |
| GAN 사진 추가 학습 실험 (서비스에는 미적용) | `experiments/gan-finetune/` (`RESULTS.md` 참고) |
| 게임 AI 점수 내보내기·가져오기 | `python -m app.evaluate_games --export / --import-json` |

## 통합 서비스 (DeepGame + 영상 분석)

`integration/deepgame-service` 브랜치의 통합판은 Next.js 화면과 FastAPI를 **한 로컬 주소**에서 제공합니다. [통합 실행·검증 안내](deeptector-backend/docs/INTEGRATED_SERVICE.md)를 참고하세요. 기존 GitHub Pages 화면은 유지되며 이 브랜치를 만들었다고 자동으로 교체되지 않습니다.

```powershell
# 이 저장소 루트에서 최초 준비 + 실행
.\Start-Service.ps1 -Setup
# 다음부터 실행 (설치/빌드가 끝난 경우)
.\Start-Service.ps1
```

브라우저: `http://127.0.0.1:5173/`. 기본 영상 분석은 고정 점수인 demo입니다. 게임은 데이터셋 정답으로 서버 채점하며, 실제 모델 평가가 없는 영상의 AI 비교 점수는 표시하지 않습니다. 게임 영상은 별도 로컬 deepGame 체크아웃에서 등록해야 합니다(정답/영상은 프론트엔드에 포함하지 않음).

이 PC에는 기본 게임 영상 24개를 등록했습니다. 다른 PC에서는 `Import-Game.ps1 -Source '로컬 deepGame 경로'`를 먼저 실행하세요. [통합판 검증 기록](deeptector-backend/docs/INTEGRATION_VERIFICATION.md)에서 실제 확인 범위와 제한을 확인할 수 있습니다.

## 포함된 파일

| 경로 | 내용 |
|---|---|
| `deeptector-backend/` | FastAPI, SQLite DB 스키마, 비동기 worker, 모델 adapter, 게임 API, 테스트 |
| `deeptector-backend/docs/` | API/OpenAPI, DB 관계, 모델 정책, 검증 문서 |
| `prototype/prototype-version.html` | 팀 공유용 11개 화면 정적 프로토타입 |
| `design/deeptector.pen` | UI 디자인 원본 |
| `exports/deeptector-screens/` | 화면별 PNG 11장 |

모델 가중치, 연구 실험, 학습 데이터, 가상환경, 업로드 영상, 로컬 DB, 작업 로그 및 인증정보는 포함하지 않습니다. `requirements-model*.txt`와 `app/inference.py`는 외부 모델을 실행하기 위한 서비스 의존성/adapter이므로 포함합니다.

## 시작하기

```powershell
git clone --branch main --single-branch https://github.com/KWU-2026-Capstone-Team/Service.git
cd Service
```

실제 API 연동 화면은 https://kwu-2026-capstone-team.github.io/Service/ 입니다. **현재 PC에서 백엔드를 실행해야** 연결됩니다. [로컬 demo 실행 안내](deeptector-backend/docs/LOCAL_DEMO.md)를 따라 API와 worker를 함께 켜세요.

`index.html`과 `web/`는 업로드·상태·결과·이력·삭제·게임 API를 연결합니다. 기본 demo는 고정 시연값이며 게임은 별도 검증 데이터가 필요합니다. `prototype/prototype-version.html`은 기존 정적 시안으로 보존합니다.

백엔드 실행은 [실행 안내](deeptector-backend/README.md)를 따르세요. 모델 파일 없이도 명시적인 `demo` 모드로 API 흐름을 확인할 수 있습니다. demo 응답은 실제 탐지 결과가 아닙니다.

## 외부 모델 연결

현재 adapter는 별도 `AI-Generated-Media-Detection/deepfake_detector`의 **ConvNeXt 5개 + MC3-18 6개** 구현을 대상으로 합니다. `anseonghwan/deeptector` 저장소 `main`의 연구 모델과 자동 호환된다는 의미가 아닙니다.

실제 추론에는 신뢰된 외부 모델 폴더와 가중치가 필요하며 API/worker 환경에 `DEEPTECTOR_MODEL_DIR`를 설정하세요. 예를 들어 이 체크아웃과 `AI-Generated-Media-Detection` 폴더가 같은 상위 디렉토리에 있는 경우, 저장소 루트에서 다음과 같이 설정합니다.

```powershell
$env:DEEPTECTOR_MODEL_DIR=(Resolve-Path '..\AI-Generated-Media-Detection\deepfake_detector').Path
```

다른 환경에서는 `infer.py`, `xai.py`, `models/spatial/*.pt`, `models/temporal/*.pt` 및 `calibration.json`이 있는 외부 폴더의 절대 경로를 지정합니다. 모델 코드를 포함하지 않는 서비스 브랜치이므로 **이 브랜치만 clone해서 실제 추론을 할 수는 없습니다**.

## 구현 및 검증 범위

영상 업로드/상태/결과/XAI/삭제, 세션별 접근 권한, 대기열/업로드 제한, 만료 정리, AI vs 사람 게임 API를 제공합니다. DB 구현은 SQLite이며 PostgreSQL은 이식 계획을 문서화했습니다. 게임에는 팀이 확인한 정답 영상과 출처/사용권을 등록해야 합니다. 노랑 신호등은 시범 정책입니다.

이관 전 39개 자동 테스트와 실제 외부 가중치를 사용하는 업로드→분석→이미지 조회→삭제 통합 검증을 통과했습니다. 재현 방법과 성능 검증 한계는 [검증 기록](deeptector-backend/docs/VERIFICATION.md)을 참고하세요.

- [API 명세](deeptector-backend/docs/API.md)
- [OpenAPI JSON](deeptector-backend/docs/openapi.json)
- [DB 스키마](deeptector-backend/docs/DATABASE.md)
- [모델 output 및 신호등](deeptector-backend/docs/MODEL.md)
- [frontend API 연동 예제](deeptector-backend/examples/client.js)
