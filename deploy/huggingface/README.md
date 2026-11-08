# Hugging Face Spaces 공개 배포 (분석 전용)

> **주의 (2026-11 확인)**: Docker Space를 무료 CPU에서 운영하려면 이제 Hugging Face **PRO 구독**이 필요합니다(Space 생성 시 402 오류). 비용 없이 공개하려면 저장소 루트의 `Start-PublicTunnel.ps1`(이 PC + Cloudflare Tunnel)을 쓰세요. 모델 저장소 `seelhwan/deeptector-model`(비공개)은 이미 올라가 있습니다.

게임은 끄고 영상 분석만 공개합니다. 게임 영상(FaceForensics++ 계열)의 재배포 권한이 확인되지 않았기 때문입니다.

## 구성

| 위치 | 내용 |
|---|---|
| Space (공개, Docker) | 프론트엔드 + FastAPI + 분석 워커. 소스 코드만 포함 |
| 모델 저장소 (비공개 권장) | `infer.py`, `xai.py`, `models/**` (가중치 약 420MB) |

컨테이너가 시작될 때 `entrypoint.sh`가 모델 저장소에서 가중치를 받아옵니다. 그래서 Space 저장소에는 모델 코드와 가중치가 올라가지 않습니다.

공개 설정(Dockerfile의 환경 변수):

- `DEEPTECTOR_ENABLE_GAMES=0`: 게임 API 제거, 화면에서 게임 메뉴 숨김
- `DEEPTECTOR_SESSION_RATE_PER_IP_HOUR=30`: IP당 시간당 새 세션 30개까지 허용
- 업로드는 50MB까지, 세션당 대기 작업 2개, 결과는 24시간 후 삭제

## 배포 순서

모든 명령은 `Service` 폴더(저장소 루트)에서 실행합니다.

1. **Hugging Face 로그인**: write 권한 토큰이 필요합니다.
   ```powershell
   deeptector-backend\.venv-model\Scripts\hf.exe auth login
   ```
2. **모델 업로드**: 비공개 모델 저장소를 만들고 올립니다.
   ```powershell
   deeptector-backend\.venv-model\Scripts\python.exe deploy\huggingface\upload_model.py --repo <계정>/deeptector-model --model-dir AI-Generated-Media-Detection\deepfake_detector
   ```
3. **Space 생성**: https://huggingface.co/new-space 에서 SDK는 **Docker**, 하드웨어는 **CPU basic**(PRO 필요), 공개 여부는 **Public**으로 선택합니다.
4. **Space 설정 (Settings → Variables and secrets)**
   - Variable `MODEL_REPO` = `<계정>/deeptector-model`
   - Secret `HF_TOKEN` = 모델 저장소를 읽을 수 있는 **read 권한** 토큰
5. **Space 폴더 조립 후 push**
   ```powershell
   git clone https://huggingface.co/spaces/<계정>/deeptector ..\deeptector-space
   .\deploy\huggingface\prepare-space.ps1 -Target ..\deeptector-space
   cd ..\deeptector-space; git add -A; git commit -m "Deploy DeepTector analysis"; git push
   ```
6. Space의 **Logs** 탭에서 빌드를 확인합니다. 첫 빌드는 torch 설치 때문에 10~20분 걸립니다. `DeepTector (real)` 줄이 보이면 접속할 수 있습니다.

코드를 바꾼 뒤에는 5번만 다시 하면 됩니다.

## 알아둘 점

- **데이터는 영구 저장되지 않습니다.** 무료 Space는 재시작하면 디스크가 초기화되므로 분석 이력이 사라집니다. 결과가 원래 24시간 뒤 삭제되는 구조라 시연에는 지장이 없습니다.
- **오래 쓰지 않으면 잠듭니다.** 일정 시간 접속이 없으면 Space가 잠들고, 다음 접속 때 다시 깨어나는 데 시간이 걸립니다. 깨어날 때마다 가중치를 다시 받습니다.
- **분석 속도**: 무료 CPU는 2코어라 영상 하나에 1~2분 정도 예상됩니다. 이 PC(8코어)에서는 25~30초였습니다.
- **요청 제한의 범위**: IP별 세션 제한은 API 프로세스 메모리에 저장됩니다. 단일 컨테이너 기준이고, 재시작하면 초기화됩니다.
