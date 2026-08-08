#!/usr/bin/env python3
"""
Example agent-callable backend service. AgentGate sits in front of this —
agents never reach it directly. Three endpoints of deliberately different
sensitivity, so the policy allowlists in policy/data.json have something
real to differentiate between.
"""
from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/get_weather", methods=["POST"])
def get_weather():
    return jsonify({"tool": "get_weather", "result": "72F, clear skies"})


@app.route("/list_files", methods=["POST"])
def list_files():
    return jsonify({"tool": "list_files", "result": ["report.csv", "notes.md"]})


@app.route("/delete_file", methods=["POST"])
def delete_file():
    # Deliberately not in any agent's allowed_tools in policy/data.json —
    # demonstrates the deny path for a destructive tool no demo agent
    # should reach.
    return jsonify({"tool": "delete_file", "result": "deleted (demo only, no real file touched)"})


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)
