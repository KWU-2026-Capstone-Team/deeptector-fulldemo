---
title: DeepTector
emoji: 🔍
colorFrom: gray
colorTo: green
sdk: docker
app_port: 7860
pinned: false
short_description: 딥페이크 의심 영상 분석 · 2026 캡스톤 시연
---

# DeepTector

영상을 올리면 공간(ConvNeXt ×5)·시간(MC3-18 ×6) 두 갈래 모델이 조작 신호를 분석하고,
판단 근거가 된 영역을 XAI 이미지로 보여 줍니다.

- 모델 점수는 조작 확률이나 확정적 증거가 아닙니다.
- 업로드한 원본 영상은 분석이 끝나면 즉시 삭제되고, 결과는 24시간 후 자동 삭제됩니다.
- 무료 CPU에서 동작하므로 영상 하나에 30초~2분 정도 걸리며, 사용자가 많으면 순서대로 처리됩니다.
