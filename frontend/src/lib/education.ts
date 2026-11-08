// Educational copy shown after a game or an analysis. Edit text here; components only render it.
// Contact numbers checked 2026-11 against multiple public sources; re-check before a public release.

export const CHECKLIST: { title: string; body: string }[] = [
  { title: "얼굴 경계·헤어라인", body: "얼굴 외곽, 턱선, 머리카락 경계가 흐릿하거나 번져 보이지 않는지 확인하세요." },
  { title: "피부색·조명", body: "얼굴과 목·귀의 피부색이 다르거나, 조명이 바뀔 때 얼굴만 다르게 반응하지 않는지 보세요." },
  { title: "눈과 깜빡임", body: "깜빡임이 너무 적거나 어색하고, 시선이 대화 상대와 맞지 않는 경우가 있습니다." },
  { title: "입 모양과 소리", body: "말소리와 입 모양이 어긋나거나, 치아·혀가 뭉개져 보이는지 확인하세요." },
  { title: "세부 디테일", body: "안경테, 귀걸이, 수염처럼 얼굴 가장자리에 있는 물체가 깨지거나 사라지지 않는지 보세요." },
  { title: "빠른 움직임", body: "고개를 돌리거나 빠르게 움직이는 순간 얼굴이 흔들리거나 해상도가 갑자기 달라집니다." },
];

export const ACTIONS: string[] = [
  "공유하기 전에 멈추세요. 자극적일수록 한 번 더 의심하세요.",
  "처음 올린 사람과 출처를 확인하세요. 공식 채널이나 원본이 있는지 찾아보세요.",
  "다른 언론·공식 발표와 교차 확인하고, 캡처 이미지는 역이미지 검색으로 원본을 찾아보세요.",
  "탐지 도구의 결과는 참고 자료일 뿐, 진위를 확정하는 증거가 아닙니다.",
  "피해를 입었다면 게시물 주소(URL)와 화면 캡처 같은 증거를 먼저 남긴 뒤 신고하세요.",
];

export const HELP: { name: string; contact: string; role: string }[] = [
  { name: "디지털성범죄피해자지원센터", contact: "02-735-8994", role: "상담·피해 영상 삭제 지원 (무료)" },
  { name: "경찰", contact: "112 · 사이버범죄 신고시스템(ECRM)", role: "긴급 신고·수사 의뢰" },
  { name: "여성긴급전화", contact: "1366", role: "24시간 상담·긴급 지원" },
];

export const LAW_NOTE =
  "성적 허위영상물(딥페이크)은 만들거나 퍼뜨리는 것뿐 아니라 소지·시청하는 것도 처벌 대상입니다 (성폭력처벌법, 2024년 개정).";
