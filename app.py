from flask import Flask, request, jsonify
import urllib.request
import urllib.parse
import csv
import io

app = Flask(__name__)

SHEET_ID = "1VyaFjCajpbbBzyxS6OgCYpSV_XC5gNmSicm5NrmQqZQ"
BLOCK_빌딩목록 = "69d9b082192d2e03bfe4827e"
BLOCK_공실현황 = "69d9b16d23db64fe52493c17"
BLOCK_상담연결 = "69d9d14423db64fe5249415f"
BLOCK_연락처   = "69d9d1f8ce25e3303304750b"

def get_sheet_data(sheet_name):
    encoded_sheet = urllib.parse.quote(sheet_name)
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_sheet}"
    with urllib.request.urlopen(url) as response:
        content = response.read().decode("utf-8")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        return rows

@app.route("/", methods=["POST"])
def kakao():
    try:
        body = request.get_json()
        block_id = body["userRequest"]["block"]["id"]
        client_extra = body["action"].get("clientExtra", {}) or {}
        mode = client_extra.get("mode", "")
        building_id = client_extra.get("building_id", "")

        # ─── 빌딩_목록 또는 상세보기 ───
        if block_id == BLOCK_빌딩목록:

            # 상세보기 모드
            if mode == "detail" and building_id:
                rows = get_sheet_data("건물 마스터")
                rows = rows[1:]
                row = next((r for r in rows if r[0] == building_id), None)

                if row:
                    text = f"🏢 {row[1]}\n"
                    text += "─────────────────\n"
                    text += f"📍 주소: {row[2]}\n"
                    text += f"🗓 준공: {row[3]}\n"
                    text += f"🏗 규모: {row[4]}\n"
                    text += f"📐 연면적: {row[5]}\n"
                    text += f"📏 기준층 임대면적: {row[6]}\n"
                    text += f"📏 기준층 전용면적: {row[7]}\n"
                    text += f"💯 전용률: {row[8]}\n"
                    text += f"🚗 총주차: {row[10]}\n"
                    text += f"❄️ 냉난방: {row[16]}\n"
                    text += f"ℹ️ 기타: {row[17]}\n"
                    text += "─────────────────\n"
                    text += "💬 '종료'를 입력하면 챗봇을 종료합니다."

                    return jsonify({
                        "version": "2.0",
                        "template": {
                            "outputs": [{"simpleText": {"text": text}}],
                            "quickReplies": [
                                {
                                    "action": "block",
                                    "label": "📊 공실 현황",
                                    "blockId": BLOCK_공실현황,
                                    "extra": {"building_id": building_id}
                                },
                                {
                                    "action": "block",
                                    "label": "🔙 빌딩 목록으로",
                                    "blockId": BLOCK_빌딩목록
                                },
                                {
                                    "action": "block",
                                    "label": "📞 상담 연결",
                                    "blockId": BLOCK_상담연결
                                }
                            ]
                        }
                    })

            # 빌딩 목록 모드 (기본)
            rows = get_sheet_data("건물 마스터")
            rows = rows[1:]

            items = []
            for row in rows[:10]:
                if len(row) < 22:
                    continue
                items.append({
                    "title": row[1],
                    "description": f"📍 {row[2]}\n🏗 {row[4]}\n🚗 주차 {row[10]}",
                    "thumbnail": {
                        "imageUrl": row[18] if row[18] else "https://t1.kakaocdn.net/openbuilder/sample/lj3JUcmrz9.jpg"
                    },
                    "buttons": [
                        {
                            "action": "block",
                            "label": "📋 상세보기",
                            "blockId": BLOCK_빌딩목록,
                            "extra": {"mode": "detail", "building_id": row[0]}
                        },
                        {
                            "action": "block",
                            "label": "📊 공실 현황",
                            "blockId": BLOCK_공실현황,
                            "extra": {"building_id": row[0]}
                        },
                        {
                            "action": "webLink",
                            "label": "📍 위치 확인",
                            "webLinkUrl": row[21] if row[21] else "https://map.kakao.com"
                        },
                        {
                            "action": "block",
                            "label": "📞 상담 연결",
                            "blockId": BLOCK_상담연결
                        }
                    ]
                })

            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{"carousel": {"type": "basicCard", "items": items}}]
                }
            })

        # ─── 공실_현황 ───
        if block_id == BLOCK_공실현황:
            rows = get_sheet_data("공실 현황")
            rows = rows[1:]
            filtered = [r for r in rows if r[0] == building_id]

            if not filtered:
                return jsonify({
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": "현재 공실 정보가 없습니다."}}],
                        "quickReplies": [
                            {
                                "action": "block",
                                "label": "🔙 빌딩 목록으로",
                                "blockId": BLOCK_빌딩목록
                            }
                        ]
                    }
                })

            text = "🏢 공실 현황\n─────────────────\n"
            for row in filtered:
                text += f"📌 {row[1]}층\n"
                text += f"   면적: {row[2]}평\n"
                text += f"   보증금: {row[7]}원\n"
                text += f"   임대료: {row[8]}원\n"
                text += f"   관리비: {row[9]}원\n"
                text += f"   입주가능: {row[10]}\n"
                text += "─────────────────\n"
            text += "💬 '종료'를 입력하면 챗봇을 종료합니다."

            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{"simpleText": {"text": text}}],
                    "quickReplies": [
                        {
                            "action": "block",
                            "label": "📝 상담 신청하기",
                            "blockId": BLOCK_상담연결
                        },
                        {
                            "action": "block",
                            "label": "🔙 빌딩 목록으로",
                            "blockId": BLOCK_빌딩목록
                        }
                    ]
                }
            })

        # ─── 상담_연결 ───
        if block_id == BLOCK_상담연결:
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{"simpleText": {"text": (
                        "📞 상담 연결\n"
                        "─────────────────\n"
                        "영업시간 (평일 09:00 ~ 18:00) 중에는\n"
                        "상담원과 바로 연결됩니다.\n\n"
                        "영업시간 외에는 연락처를 남겨주시면\n"
                        "영업시간 내 연락드리겠습니다.\n"
                        "─────────────────\n"
                        "💬 '종료'를 입력하면 챗봇을 종료합니다."
                    )}}],
                    "quickReplies": [
                        {
                            "action": "block",
                            "label": "📝 연락처 남기기",
                            "blockId": BLOCK_연락처
                        },
                        {
                            "action": "block",
                            "label": "🔙 빌딩 목록으로",
                            "blockId": BLOCK_빌딩목록
                        }
                    ]
                }
            })

        # ─── 연락처_남기기 ───
        if block_id == BLOCK_연락처:
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{"simpleText": {"text": (
                        "📝 연락처 남기기\n"
                        "─────────────────\n"
                        "성함과 연락처를 아래 형식으로 입력해주세요.\n\n"
                        "예시) 홍길동 / 010-1234-5678\n\n"
                        "담당자가 영업시간 내 연락드리겠습니다.\n"
                        "(평일 09:00 ~ 18:00)\n"
                        "─────────────────\n"
                        "💬 '종료'를 입력하면 챗봇을 종료합니다."
                    )}}]
                }
            })

        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": "받은 blockId: " + block_id}}]
            }
        })

    except Exception as e:
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": "에러: " + str(e)}}]
            }
        })

if __name__ == "__main__":
    app.run(debug=True)