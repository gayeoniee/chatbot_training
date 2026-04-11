from flask import Flask, request, jsonify
import gspread
from google.oauth2 import service_account
import json

app = Flask(__name__)

# 구글 시트 공개 접근 (키 없이)
def get_sheet_data(sheet_name):
    import urllib.request
    SHEET_ID = "1VyaFjCajpbbBzyxS6OgCYpSV_XC5gNmSicm5NrmQqZQ"
    encoded_sheet = urllib.parse.quote(sheet_name)
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_sheet}"
    with urllib.request.urlopen(url) as response:
        import csv, io
        content = response.read().decode("utf-8")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        return rows

@app.route("/", methods=["POST"])
def kakao():
    try:
        body = request.get_json()
        block_id = body["userRequest"]["block"]["id"]
        
        # 빌딩_목록
        if block_id == "69d9b082192d2e03bfe4827e":
            rows = get_sheet_data("건물 마스터")
            rows = rows[1:]  # 헤더 제거
            
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
                            "label": "📊 공실 현황 보기",
                            "blockId": "69d9b16d23db64fe52493c17",
                            "extra": {"building_id": row[0]}
                        },
                        {
                            "action": "webLink",
                            "label": "📍 위치 확인",
                            "webLinkUrl": row[21] if row[21] else "https://map.kakao.com"
                        }
                    ]
                })
            
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{"carousel": {"type": "basicCard", "items": items}}]
                }
            })
        
        # 공실_현황
        if block_id == "69d9b16d23db64fe52493c17":
            client_extra = body["action"].get("clientExtra", {}) or {}
            building_id = client_extra.get("building_id", "")
            
            rows = get_sheet_data("공실 현황")
            rows = rows[1:]  # 헤더 제거
            
            filtered = [r for r in rows if r[0] == building_id]
            
            if not filtered:
                return jsonify({
                    "version": "2.0",
                    "template": {
                        "outputs": [{"simpleText": {"text": "현재 공실 정보가 없습니다."}}]
                    }
                })
            
            text = f"🏢 공실 현황\n─────────────────\n"
            for row in filtered:
                text += f"📌 {row[1]}층\n"
                text += f"   면적: {row[2]}평\n"
                text += f"   보증금: {row[7]}원\n"
                text += f"   임대료: {row[8]}원\n"
                text += f"   관리비: {row[9]}원\n"
                text += f"   입주가능: {row[10]}\n"
                text += "─────────────────\n"
            
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [{"simpleText": {"text": text}}],
                    "quickReplies": [{"action": "block", "label": "📝 상담 신청하기", "blockId": "상담_신청_블록ID"}]
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