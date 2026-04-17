from flask import Flask, request, jsonify
import urllib.request
import urllib.parse
import csv
import io

app = Flask(__name__)

SHEET_ID = "1VyaFjCajpbbBzyxS6OgCYpSV_XC5gNmSicm5NrmQqZQ"
BLOCK_빌딩목록 = "69e07bc89c9e621312f79868"
BLOCK_공실현황 = "69e07c062f86b41b354c42ac"
BLOCK_상담연결 = "69e07c60717504b55e562a65"
BLOCK_상세보기 = "69e0b4374609e56adc714886"
BLOCK_메인메뉴 = "69e081dd9c9e621312f79a3b"
BLOCK_건물카드 = "69e1cd74d2b391b64c5f990e"

def get_sheet_data(sheet_name):
    encoded_sheet = urllib.parse.quote(sheet_name)
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_sheet}"
    with urllib.request.urlopen(url) as response:
        content = response.read().decode("utf-8")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        return rows

def get_building_id(body, client_extra):
    building_id = client_extra.get("building_id", "")
    if building_id:
        return building_id
    contexts = body.get("contexts", [])
    building_context = next((c for c in contexts if c["name"] == "building_context"), None)
    if building_context:
        building_id = building_context.get("params", {}).get("building_id", {}).get("value", "")
    return building_id

def search_buildings(utterance, rows):
    return [r for r in rows if utterance in r[1] or utterance in r[2]]

def make_building_card_item(row, from_source="list"):
    return {
        "title": row[1],
        "description": f"📍 {row[2]}\n🏗 {row[4]}\n🚗 주차 {row[10]}",
        "thumbnail": {
            "imageUrl": row[18] if row[18] else "https://t1.kakaocdn.net/openbuilder/sample/lj3JUcmrz9.jpg"
        },
        "buttons": [
            {
                "action": "block",
                "label": "📋 상세보기",
                "blockId": BLOCK_상세보기,
                "extra": {"building_id": row[0], "from": from_source}
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
    }

@app.route("/", methods=["GET", "POST"])
def kakao():
    if request.method == "GET":
        return "OK", 200
    try:
        body = request.get_json()
        block_id = body["userRequest"]["block"]["id"]
        utterance = body["userRequest"]["utterance"]
        client_extra = body["action"].get("clientExtra", {}) or {}
        building_id = get_building_id(body, client_extra)
        from_source = client_extra.get("from", "list")

        # ─── 빌딩_목록 (listCard) ───
        if block_id == BLOCK_빌딩목록:
            rows = get_sheet_data("건물 마스터")
            rows = rows[1:]

            page = int(client_extra.get("page", 1))
            page_size = 5
            start = (page - 1) * page_size
            end = start + page_size
            total = len(rows)
            paged_rows = rows[start:end]

            # listCard 항목 구성
            list_items = []
            for row in paged_rows:
                if len(row) < 22:
                    continue
                list_items.append({
                    "title": row[1],
                    "description": f"📍 {row[2]}",
                    "action": "block",
                    "blockId": BLOCK_건물카드,
                    "extra": {"building_id": row[0]}
                })

            # 페이지네이션 버튼
            buttons = []
            if page > 1:
                buttons.append({
                    "action": "block",
                    "label": "◀ 이전",
                    "blockId": BLOCK_빌딩목록,
                    "extra": {"page": page - 1}
                })
            if end < total:
                buttons.append({
                    "action": "block",
                    "label": "다음 ▶",
                    "blockId": BLOCK_빌딩목록,
                    "extra": {"page": page + 1}
                })

            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{
                        "listCard": {
                            "header": {
                                "title": f"🏢 교보생명사옥 목록 ({start+1}-{min(end, total)} / 전체 {total}개)"
                            },
                            "items": list_items,
                            "buttons": buttons
                        }
                    }]
                }
            })

        # ─── 건물_카드 (listCard 항목 클릭 시) ───
        if block_id == BLOCK_건물카드:
            rows = get_sheet_data("건물 마스터")
            rows = rows[1:]
            row = next((r for r in rows if r[0] == building_id), None)

            if not row:
                return jsonify({
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": "건물 정보를 찾을 수 없습니다."}}]
                    }
                })

            card = make_building_card_item(row, from_source="list")

            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{"basicCard": {
                        "title": card["title"],
                        "description": card["description"],
                        "thumbnail": card["thumbnail"],
                        "buttons": card["buttons"]
                    }}],
                    "quickReplies": [
                        {
                            "action": "block",
                            "label": "🏢 빌딩 목록 보기",
                            "blockId": BLOCK_빌딩목록
                        }
                    ]
                }
            })

        # ─── 상세보기 ───
        if block_id == BLOCK_상세보기:
            rows = get_sheet_data("건물 마스터")
            rows = rows[1:]
            row = next((r for r in rows if r[0] == building_id), None)

            if not row:
                return jsonify({
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": "건물 정보를 찾을 수 없습니다."}}],
                        "quickReplies": [
                            {
                                "action": "block",
                                "label": "🏢 빌딩 목록 보기",
                                "blockId": BLOCK_빌딩목록
                            }
                        ]
                    }
                })

            detail_text = (
                f"🏢 {row[1]}\n"
                f"─────────────────\n"
                f"📍 주소: {row[2]}\n"
                f"🗓 준공: {row[3]}\n"
                f" 규모: {row[4]}\n"
                f" 연면적: {row[5]}\n"
                f" 임대면적: {row[6]}\n"
                f" 전용률: {row[8]}\n"
                f"🚗 주차: {row[10]}\n"
                f"❄️ 냉난방: {row[16]}\n"
                f"─────────────────\n"
                f"💬 '종료'를 입력하면 챗봇을 종료합니다."
            )

            photo_items = []
            if row[19]:
                photo_urls = [u.strip() for u in row[19].split(",") if u.strip()]
                for i, photo_url in enumerate(photo_urls[:5]):
                    photo_items.append({
                        "title": f"📸 세부사진 {i+1}",
                        "thumbnail": {"imageUrl": photo_url}
                    })
            if row[20]:
                plan_urls = [u.strip() for u in row[20].split(",") if u.strip()]
                for i, plan_url in enumerate(plan_urls[:3]):
                    photo_items.append({
                        "title": f"📐 도면",
                        "thumbnail": {"imageUrl": plan_url}
                    })
            photo_items = photo_items[:10]

            outputs = [{
                "basicCard": {
                    "description": detail_text,
                    "buttons": [
                        {
                            "action": "block",
                            "label": "📊 공실 현황",
                            "blockId": BLOCK_공실현황,
                            "extra": {"building_id": building_id}
                        },
                        {
                            "action": "block",
                            "label": "📞 상담 연결",
                            "blockId": BLOCK_상담연결
                        }
                    ]
                }
            }]

            if photo_items:
                outputs.append({
                    "carousel": {"type": "basicCard", "items": photo_items}
                })

            if from_source == "search":
                back_button = {
                    "action": "block",
                    "label": "🔙 처음으로",
                    "blockId": BLOCK_메인메뉴
                }
            else:
                back_button = {
                    "action": "block",
                    "label": "🏢 빌딩 목록 보기",
                    "blockId": BLOCK_빌딩목록
                }

            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": outputs,
                    "quickReplies": [back_button]
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
                                "label": "🏢 빌딩 목록 보기",
                                "blockId": BLOCK_빌딩목록
                            },
                            {
                                "action": "block",
                                "label": "🏠 처음으로",
                                "blockId": BLOCK_메인메뉴
                            }
                        ]
                    }
                })

            if filtered[0][1] == "":
                return jsonify({
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": (
                            "🏢 현재 해당 건물은 공실이 없습니다.\n\n"
                            "임대 문의는 상담 연결을 이용해주세요.\n"
                            "─────────────────\n"
                            "💬 '종료'를 입력하면 챗봇을 종료합니다."
                        )}}],
                        "quickReplies": [
                            {
                                "action": "block",
                                "label": "📞 상담 연결",
                                "blockId": BLOCK_상담연결
                            },
                            {
                                "action": "block",
                                "label": "🏢 빌딩 목록 보기",
                                "blockId": BLOCK_빌딩목록
                            },
                            {
                                "action": "block",
                                "label": "🏠 처음으로",
                                "blockId": BLOCK_메인메뉴
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
                            "label": "🏢 빌딩 목록 보기",
                            "blockId": BLOCK_빌딩목록
                        },
                        {
                            "action": "block",
                            "label": "🏠 처음으로",
                            "blockId": BLOCK_메인메뉴
                        }
                    ]
                }
            })

        # ─── 키워드 검색 (폴백) ───
        rows = get_sheet_data("건물 마스터")
        rows = rows[1:]
        matched = search_buildings(utterance, rows)

        if matched:
            items = [make_building_card_item(r, from_source="search") for r in matched[:10]]
            carousel_items = []
            for item in items:
                carousel_items.append({
                    "title": item["title"],
                    "description": item["description"],
                    "thumbnail": item["thumbnail"],
                    "buttons": item["buttons"]
                })
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{"carousel": {"type": "basicCard", "items": carousel_items}}],
                    "quickReplies": [
                        {
                            "action": "block",
                            "label": "🏢 빌딩 목록 보기",
                            "blockId": BLOCK_빌딩목록
                        },
                        {
                            "action": "block",
                            "label": "🏠 처음으로",
                            "blockId": BLOCK_메인메뉴
                        }
                    ]
                }
            })

        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": (
                    f"'{utterance}'에 해당하는 건물을 찾지 못했습니다.\n\n"
                    "다른 검색어를 입력하시거나\n"
                    "전체 목록을 확인해주세요."
                )}}],
                "quickReplies": [
                    {
                        "action": "block",
                        "label": "🏢 빌딩 목록 보기",
                        "blockId": BLOCK_빌딩목록
                    },
                    {
                        "action": "block",
                        "label": "🏠 처음으로",
                        "blockId": BLOCK_메인메뉴
                    }
                ]
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