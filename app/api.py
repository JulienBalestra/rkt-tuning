from flask import Flask, request, json, jsonify
from werkzeug.contrib.cache import FileSystemCache

APP = APPLICATION = Flask(__name__)
CACHE = FileSystemCache("/tmp/werkzeug")


@APP.route("/api/results", methods=["POST"])
def new_results():
    new_res = json.loads(request.get_data())
    data = CACHE.get("results")
    if not data:
        data = []
    data.append(new_res)
    CACHE.set("results", data, 0)
    return "", 200


@APP.route("/api/results", methods=["GET"])
def get_results():
    data = CACHE.get("results")
    if not data:
        data = []
    return jsonify(data)


@APP.route("/api/results/total", methods=["GET"])
def get_summary_results():
    data = CACHE.get("results")
    if not data:
        data = []
    summary = dict()
    summary["results"] = len(data)
    for i in data:
        for j in i:
            try:
                summary[j["__name__"]] += j["total"]
            except KeyError:
                summary[j["__name__"]] = j["total"]
    return jsonify(summary)


if __name__ == '__main__':
    APP.run()
