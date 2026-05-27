#!/usr/bin/env python3
"""
PixMob Show Creator - Web Server
Flask-based backend for creating, saving, and playing PixMob light shows.
"""

import os
import json
import sys
import math
import tempfile
import subprocess
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rf_codec import encode_payload_to_raw, KNOWN_COMMANDS, ANIM
import pixmob_hackrf

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
app.config["SHOWS_FOLDER"] = os.path.join(os.path.dirname(__file__), "shows")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["SHOWS_FOLDER"], exist_ok=True)

HACKRF_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "pixmob_hackrf.py")

# ====================== DASHBOARD HELPERS ======================

PRESET_COLORS = [
    ("Red",      0, 57, 0),
    ("Green",   57,  0, 0),
    ("Blue",    16,  0, 57),
    ("Gold",    51, 57, 0),
    ("White",   57, 57, 57),
    ("Turq",    57,  0, 60),
    ("Magenta", 0, 57, 57),
    ("Wine",     0, 57, 0),
    ("Orange",  51, 63, 0),
    ("Pink",     0, 63, 40),
    ("Cyan",    57,  0, 57),
    ("Off",      0,  0, 0),
]

EFFECTS = sorted(ANIM.keys())


def find_nearest_rf_color(g6, r6, b6):
    """Find the closest known color by RGB distance."""
    best = None
    best_dist = float("inf")
    for (kg, kr, kb, _), (d0, d5, d6, d8) in KNOWN_COMMANDS.items():
        d = (kg - g6) ** 2 + (kr - r6) ** 2 + (kb - b6) ** 2
        if d < best_dist:
            best_dist = d
            best = (d0, d5, d6, d8)
    return best or (0, 36, 36, 0)


def build_payload(g6, r6, b6, effect, d5=None, d6=None):
    """Build raw timing for a custom color+effect command."""
    d0, _, _, d8 = find_nearest_rf_color(g6, r6, b6)
    if d5 is None or d6 is None:
        ad5, ad6 = ANIM.get(effect, (36, 36))
    else:
        ad5, ad6 = d5 & 0x3F, d6 & 0x3F
    decoded = [d0, 0, g6, r6, b6, ad5, ad6, 0, d8]
    raw = encode_payload_to_raw(decoded)
    return raw, decoded


def transmit_raw(raw_data, repeats=3):
    """Send raw timing data via HackRF."""
    iq8 = pixmob_hackrf.generate_iq8(raw_data, repeats=repeats)
    pixmob_hackrf.transmit(iq8)



def get_command_list():
    commands = [
        {"id": "nothing", "label": "Wake Up (30s)", "category": "system", "color": "#888"},
        {"id": "gold_fade_in", "label": "Gold Fade In", "category": "gold", "color": "#FFD700"},
        {"id": "gold_fast_fade", "label": "Gold Fast Fade", "category": "gold", "color": "#FFC125"},
        {"id": "gold_blink", "label": "Gold Blink", "category": "gold", "color": "#FFB90F"},
        {"id": "gold_fade", "label": "Gold Fade", "category": "gold", "color": "#FFD700"},
        {"id": "gold_fastfade", "label": "Gold Fast Fade 2", "category": "gold", "color": "#FFC125"},
        {"id": "red_fade", "label": "Red Fade", "category": "red", "color": "#FF0000"},
        {"id": "red_fastblink", "label": "Red Fast Blink", "category": "red", "color": "#FF4444"},
        {"id": "red_fastfade", "label": "Red Fast Fade", "category": "red", "color": "#CC0000"},
        {"id": "blue_fade", "label": "Blue Fade", "category": "blue", "color": "#0066FF"},
        {"id": "white_blink", "label": "White Blink", "category": "white", "color": "#FFFFFF"},
        {"id": "white_fade", "label": "White Fade", "category": "white", "color": "#EEEEEE"},
        {"id": "white_fastfade", "label": "White Fast Fade", "category": "white", "color": "#DDDDDD"},
        {"id": "white_fastfade2", "label": "White Fast Fade 2", "category": "white", "color": "#CCCCCC"},
        {"id": "turq_blink", "label": "Turquoise Blink", "category": "turquoise", "color": "#00CED1"},
        {"id": "wine_fade_in", "label": "Wine Fade In", "category": "wine", "color": "#8B2252"},
        {"id": "magenta_fade", "label": "Magenta Fade", "category": "magenta", "color": "#FF00FF"},
        {"id": "rand_color_blinks", "label": "White/Red/Turq Blinks", "category": "effects", "color": "#FF69B4"},
        {"id": "rand_rwb", "label": "Random Red-White-Blue", "category": "effects", "color": "#FF4500"},
        {"id": "wild_combo", "label": "Wild Combo", "category": "effects", "color": "#9370DB"},
        {"id": "wine_gold_alt_fade", "label": "Wine/Gold Alt Fade", "category": "effects", "color": "#CD5C5C"},
        {"id": "wine_gold_sync_fade", "label": "Wine/Gold Sync Fade", "category": "effects", "color": "#B22222"},
        {"id": "combo_gold_white", "label": "Gold + White (alt)", "category": "combos", "color": "#FFD700"},
        {"id": "combo_red_gold", "label": "Red + Gold (alt)", "category": "combos", "color": "#FF6347"},
        {"id": "combo_rgb", "label": "Red + Gold + Blue", "category": "combos", "color": "#FF1493"},
        {"id": "combo_red_blue", "label": "Red + Blue (alt)", "category": "combos", "color": "#FF69B4"},
        {"id": "combo_white_red", "label": "White + Red (alt)", "category": "combos", "color": "#FFB6C1"},
        {"id": "combo_rwg", "label": "Red + White + Gold", "category": "combos", "color": "#FFA07A"},
    ]
    return commands


@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/show-creator")
def show_creator():
    return render_template("index.html")

# ====================== DASHBOARD API ======================

@app.route("/api/dashboard/colors")
def api_dashboard_colors():
    return jsonify([
        {"name": name, "g": g, "r": r, "b": b, "hex": f"#{b << 4 | b >> 2:02x}{g << 4 | g >> 2:02x}{r << 4 | r >> 2:02x}"}
        for name, g, r, b in PRESET_COLORS
    ])

@app.route("/api/dashboard/effects")
def api_dashboard_effects():
    return jsonify(EFFECTS)

@app.route("/api/dashboard/send", methods=["POST"])
def api_dashboard_send():
    data = request.get_json()
    g = int(data.get("g", 0))
    r = int(data.get("r", 0))
    b = int(data.get("b", 0))
    effect = data.get("effect", "fade")
    repeats = int(data.get("repeats", 3))
    d5 = data.get("d5")
    d6 = data.get("d6")

    if effect not in ANIM and d5 is None:
        return jsonify({"success": False, "error": f"Unknown effect: {effect}"}), 400

    d5 = int(d5) & 0x3F if d5 is not None else None
    d6 = int(d6) & 0x3F if d6 is not None else None

    raw, decoded = build_payload(g, r, b, effect, d5, d6)
    try:
        transmit_raw(raw, repeats)
        return jsonify({
            "success": True,
            "payload": {"G": g, "R": r, "B": b, "effect": effect, "D0": decoded[0], "D5": decoded[5], "D6": decoded[6], "D8": decoded[8]},
            "repeats": repeats,
        })
    except FileNotFoundError:
        return jsonify({"success": False, "error": "hackrf_transfer not found. Install hackrf-tools."}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/dashboard/combo", methods=["POST"])
def api_dashboard_combo():
    data = request.get_json()
    steps = data.get("steps", [])
    step_repeats = int(data.get("repeats", 2))

    if not steps:
        return jsonify({"success": False, "error": "No steps"}), 400

    results = []
    for step in steps:
        g = int(step.get("g", 0))
        r = int(step.get("r", 0))
        b = int(step.get("b", 0))
        effect = step.get("effect", "fade")
        repeats = int(step.get("repeats", step_repeats))
        d5 = int(step.get("d5", -1)) & 0x3F if step.get("d5") is not None else None
        d6 = int(step.get("d6", -1)) & 0x3F if step.get("d6") is not None else None

        if effect not in ANIM and d5 is None:
            results.append({"success": False, "error": f"Unknown effect: {effect}"})
            continue
        try:
            raw, decoded = build_payload(g, r, b, effect, d5, d6)
            transmit_raw(raw, repeats)
            results.append({"success": True, "payload": {"G": g, "R": r, "B": b, "effect": effect}})
        except Exception as e:
            results.append({"success": False, "error": str(e)})

    return jsonify({"success": True, "sent": sum(1 for r in results if r["success"]), "total": len(steps), "results": results})


@app.route("/api/commands")
def api_commands():
    return jsonify(get_command_list())


@app.route("/api/send", methods=["POST"])
def api_send():
    data = request.get_json()
    cmd_name = data.get("command")
    repeats = data.get("repeats", 3)

    if not os.path.exists(HACKRF_SCRIPT):
        return jsonify({"success": False, "error": "HackRF controller not found"})

    try:
        result = subprocess.run(
            [sys.executable, HACKRF_SCRIPT, "send", cmd_name, str(repeats)],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            return jsonify({"success": True, "output": result.stdout})
        else:
            err = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            return jsonify({"success": False, "error": err})
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Command timed out"})
    except FileNotFoundError:
        return jsonify({"success": False, "error": "hackrf_transfer not found. Install hackrf-tools and ensure it's on your PATH."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/wake", methods=["POST"])
def api_wake():
    data = request.get_json()
    seconds = data.get("seconds", 30)

    if not os.path.exists(HACKRF_SCRIPT):
        return jsonify({"success": False, "error": "HackRF controller not found"})

    try:
        result = subprocess.run(
            [sys.executable, HACKRF_SCRIPT, "wake", str(seconds)],
            capture_output=True, text=True, timeout=seconds + 10
        )
        if result.returncode == 0:
            return jsonify({"success": True, "output": result.stdout})
        else:
            err = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            return jsonify({"success": False, "error": err})
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Wake command timed out"})
    except FileNotFoundError:
        return jsonify({"success": False, "error": "hackrf_transfer not found. Install hackrf-tools."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/hackrf-status", methods=["GET"])
def api_hackrf_status():
    try:
        result = subprocess.run(
            ["hackrf_info"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            return jsonify({"success": True, "info": lines})
        else:
            return jsonify({"success": False, "error": result.stderr.strip() or "HackRF not detected"})
    except FileNotFoundError:
        return jsonify({"success": False, "error": "hackrf_info not found. Install hackrf-tools."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/upload", methods=["POST"])
def api_upload():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided"})
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected"})

    ext = os.path.splitext(file.filename)[1]
    filename = str(uuid.uuid4()) + ext
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    return jsonify({"success": True, "filename": filename, "original_name": file.filename})


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/api/shows", methods=["GET"])
def api_list_shows():
    shows = []
    if os.path.exists(app.config["SHOWS_FOLDER"]):
        for fname in sorted(os.listdir(app.config["SHOWS_FOLDER"])):
            if fname.endswith(".json"):
                fpath = os.path.join(app.config["SHOWS_FOLDER"], fname)
                try:
                    with open(fpath) as f:
                        data = json.load(f)
                    shows.append({
                        "id": fname.replace(".json", ""),
                        "name": data.get("name", fname),
                        "duration": data.get("duration", 0),
                        "command_count": len(data.get("timeline", [])),
                        "has_audio": bool(data.get("audio_file")),
                        "updated": datetime.fromtimestamp(os.path.getmtime(fpath)).isoformat(),
                    })
                except (json.JSONDecodeError, KeyError):
                    pass
    return jsonify(sorted(shows, key=lambda s: s["updated"], reverse=True))


@app.route("/api/shows", methods=["POST"])
def api_save_show():
    data = request.get_json()
    show_id = data.get("id", str(uuid.uuid4()))
    fpath = os.path.join(app.config["SHOWS_FOLDER"], f"{show_id}.json")

    existing = {}
    if os.path.exists(fpath):
        with open(fpath) as f:
            existing = json.load(f)

    show_data = {
        "id": show_id,
        "name": data.get("name", existing.get("name", "Untitled Show")),
        "bpm": data.get("bpm", existing.get("bpm", 120)),
        "duration": data.get("duration", existing.get("duration", 0)),
        "audio_file": data.get("audio_file", existing.get("audio_file", None)),
        "audio_offset": data.get("audio_offset", existing.get("audio_offset", 0)),
        "timeline": data.get("timeline", existing.get("timeline", [])),
        "groups": data.get("groups", existing.get("groups", [])),
        "updated": datetime.now().isoformat(),
    }

    with open(fpath, "w") as f:
        json.dump(show_data, f, indent=2)

    return jsonify({"success": True, "id": show_id})


@app.route("/api/shows/<show_id>", methods=["GET"])
def api_get_show(show_id):
    fpath = os.path.join(app.config["SHOWS_FOLDER"], f"{show_id}.json")
    if not os.path.exists(fpath):
        return jsonify({"error": "Show not found"}), 404
    with open(fpath) as f:
        return jsonify(json.load(f))


@app.route("/api/shows/<show_id>", methods=["DELETE"])
def api_delete_show(show_id):
    fpath = os.path.join(app.config["SHOWS_FOLDER"], f"{show_id}.json")
    if os.path.exists(fpath):
        os.remove(fpath)
    audio_dir = os.path.join(app.config["UPLOAD_FOLDER"])
    for fname in os.listdir(audio_dir):
        if fname.startswith(show_id):
            os.remove(os.path.join(audio_dir, fname))
    return jsonify({"success": True})


@app.route("/api/play-timeline", methods=["POST"])
def api_play_timeline():
    data = request.get_json()
    timeline = data.get("timeline", [])
    repeats = data.get("repeats", 2)

    if not timeline:
        return jsonify({"success": False, "error": "Empty timeline"})

    if not os.path.exists(HACKRF_SCRIPT):
        return jsonify({"success": False, "error": "HackRF controller not available"})

    errors = []
    successful = 0
    for entry in timeline:
        cmd_name = entry.get("command")
        cmd_repeats = entry.get("repeats", repeats)
        try:
            result = subprocess.run(
                [sys.executable, HACKRF_SCRIPT, "send", cmd_name, str(cmd_repeats)],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                successful += 1
            else:
                errors.append({"command": cmd_name, "error": result.stderr or result.stdout})
        except Exception as e:
            errors.append({"command": cmd_name, "error": str(e)})

    return jsonify({
        "success": len(errors) == 0,
        "sent": successful,
        "total": len(timeline),
        "errors": errors,
    })


@app.route("/api/auto-generate", methods=["POST"])
def api_auto_generate():
    data = request.get_json()
    filename = data.get("filename")
    bpm = data.get("bpm", 120)
    style = data.get("style", "energetic")
    color_categories = data.get("colors", [])

    if not filename:
        return jsonify({"success": False, "error": "No audio file specified"})

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(filepath):
        return jsonify({"success": False, "error": "Audio file not found"})

    commands = get_command_list()

    if color_categories:
        pool = [c for c in commands if c["category"] in color_categories]
        if not pool:
            return jsonify({"success": False, "error": "No commands match selected colors"})
    else:
        pool = [c for c in commands if c["category"] not in ("system",)]

    color_pool = [c for c in pool if c["category"] not in ("effects", "combos")]
    effect_pool = [c for c in pool if c["category"] in ("effects", "combos")]

    beat_interval = 60.0 / bpm
    duration = data.get("duration", 30)
    total_beats = int(duration / beat_interval)

    timeline = []
    bar_size = 4

    import random
    random.seed(filename)

    for i in range(total_beats):
        t = i * beat_interval
        beat_in_bar = i % bar_size

        if style == "energetic":
            if beat_in_bar == 0 and color_pool:
                cmd = random.choice(color_pool)
                timeline.append({"time": round(t, 3), "command": cmd["id"], "repeats": 2, "duration": 0.3})
            elif beat_in_bar == 2 and color_pool:
                cmd = random.choice(color_pool)
                timeline.append({"time": round(t, 3), "command": cmd["id"], "repeats": 1, "duration": 0.15})
        elif style == "slow_fade":
            if i % 8 == 0 and color_pool:
                cmd = random.choice(color_pool)
                timeline.append({"time": round(t, 3), "command": cmd["id"], "repeats": 3, "duration": 1.0})
            if i % 16 == 8 and color_pool:
                cmd = random.choice(color_pool)
                timeline.append({"time": round(t, 3), "command": cmd["id"], "repeats": 3, "duration": 1.0})
        elif style == "party":
            if beat_in_bar in (0, 2) and color_pool:
                cmd = random.choice(color_pool)
                timeline.append({"time": round(t, 3), "command": cmd["id"], "repeats": 1, "duration": 0.2})
            if i % 16 == 0 and (effect_pool or color_pool):
                pool2 = effect_pool + color_pool
                cmd = random.choice(pool2) if pool2 else None
                if cmd:
                    timeline.append({"time": round(t, 3), "command": cmd["id"], "repeats": 2, "duration": 0.5})
        else:
            if i % 4 == 0 and color_pool:
                cmd = random.choice(color_pool)
                timeline.append({"time": round(t, 3), "command": cmd["id"], "repeats": 2, "duration": 0.3})

    timeline.sort(key=lambda e: e["time"])

    return jsonify({
        "success": True,
        "timeline": timeline,
        "bpm": bpm,
        "duration": duration,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("0.0.0.0", port))
            sock.close()
        except OSError:
            sock.close()
            subprocess.run(["bash", "-c", f"lsof -ti :{port} 2>/dev/null | xargs kill -9 2>/dev/null"])
            import time
            time.sleep(0.5)
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"
    finally:
        s.close()
    print(f"PixMob Dashboard at:")
    print(f"  Local:   http://localhost:{port}")
    print(f"  Network: http://{local_ip}:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
