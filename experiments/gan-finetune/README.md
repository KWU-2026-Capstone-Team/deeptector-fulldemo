# GAN 얼굴 추가 학습 실험 (B안, 소규모)

서비스(`Service/`)와 원래 모델 폴더는 **수정하지 않는** 독립 실험입니다. 원래 가중치는 읽기만 하고, 새 가중치는 `checkpoints/`에 따로 저장합니다.

## 왜 하나
우리 공간 모델(ConvNeXt)은 FaceForensics++ 영상의 **얼굴 바꾸기·표정 조작**으로 학습되어, 얼굴 전체를 새로 만든 **StyleGAN 사진**을 거의 잡지 못합니다. 원래 실력은 유지하면서 StyleGAN 얼굴도 잡을 수 있는지 소규모로 확인합니다.

## 데이터
- 학습·테스트: [140k Real and Fake Faces](https://huggingface.co/datasets/TheKernel01/140k-Real-and-Fake-Faces) 일부. 진짜는 FFHQ(NVIDIA), 가짜는 StyleGAN입니다. 학습 묶음 1개와 테스트 묶음 1개(약 770MB)만 받아 균형 있게 뽑습니다.
  - 라이선스는 "cc"로만 표기돼 있고, FFHQ는 비상업 연구용입니다. **내부 연구용으로만 쓰고 재배포하지 않습니다.**
- 원래 실력 점검: 로컬 게임 영상 24개(REAL 12 / FAKE 12, FF++ 계열)에서 서비스와 같은 방식으로 영상당 얼굴 16장을 뽑습니다.
- 얼굴 자르기는 서비스와 똑같이 합니다(MTCNN, 가장 확실한 얼굴, 위아래 10% 여유, 224×224).

## 방법
- 원래 5개 모델 중 **fold 1 하나만** 출발점으로 씁니다.
- 앞쪽 층은 고정하고 **마지막 ConvNeXt stage와 판별층만** 작은 학습률(1e-4)로 1 epoch 학습합니다. 원래 실력을 덜 잊게 하려는 설정입니다.
- 결과는 원래 체크포인트와 같은 형식으로 저장해서, 나중에 서비스의 fold 파일과 바꿔 끼울 수 있게 했습니다(아직 적용하지 않음).

## 실행 순서
`Service\Setup-Workspace.ps1`로 모델과 게임 저장소를 먼저 준비한 뒤, 이 폴더에서 실행합니다. 데이터·가중치·가상환경은 git에 올리지 않으므로 새 PC에서는 아래처럼 다시 만듭니다.
```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install torch==2.2.2 torchvision==0.17.2 --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe prepare_data.py          # 데이터 받고 얼굴 자르기 (약 770MB 다운로드)
.venv\Scripts\python.exe prepare_ffpp_eval.py     # 게임 영상 얼굴 (원래 실력 점검용)
.venv\Scripts\python.exe evaluate.py --name original5                 # 기준: 서비스 5-fold 앙상블
.venv\Scripts\python.exe evaluate.py --name original-fold1 --fold 1   # 기준: 학습 전 fold1
.venv\Scripts\python.exe finetune.py                                  # 추가 학습
.venv\Scripts\python.exe evaluate.py --name finetuned-fold1 --ckpt checkpoints\convnext_fold1_gan.pt
```
결과는 `results/*.json`에 저장됩니다. 결론은 `RESULTS.md`를 보세요.
