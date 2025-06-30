from flask import Flask, request, jsonify
from flask_cors import CORS
from recom_song import recommend

app = Flask(__name__)
CORS(app)  # ✅ This must be above app.run()

@app.route("/", methods=["GET"])
def health():
    return "✅ Flask server is running"

@app.route("/recommend", methods=["POST"])
def recommend_route():
    data = request.get_json()
    diary_text = data.get("diary_text", "")
    rec_n = data.get("rec_n", 10)  # get rec_n from request, default 10
    print("✅ Received diary_text:", diary_text)  # helpful for debugging
    print("✅ Received rec_n:", rec_n)

    result = recommend(diary_text, rec_n=rec_n)
    return jsonify(result.to_dict(orient="records"))

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
