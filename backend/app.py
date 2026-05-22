import os
import json
import math
import random
import sqlite3
import hashlib
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv


# ---------------- BASIC SETUP ---------------- #

load_dotenv()

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")
DB_PATH = os.path.join(BASE_DIR, "database.db")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

current_admin_otp = None

FACE_MATCH_THRESHOLD = 0.60


# ---------------- DATABASE HELPERS ---------------- #

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def add_column_if_missing(cursor, table_name, column_name, column_definition):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()

    existing_columns = [column[1] for column in columns]

    if column_name not in existing_columns:
        cursor.execute(f"""
        ALTER TABLE {table_name}
        ADD COLUMN {column_name} {column_definition}
        """)


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # ---------------- VOTERS TABLE ---------------- #

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        face_descriptor TEXT,
        has_voted INTEGER DEFAULT 0
    )
    """)

    add_column_if_missing(cursor, "voters", "face_descriptor", "TEXT")
    add_column_if_missing(cursor, "voters", "has_voted", "INTEGER DEFAULT 0")

    # ---------------- CANDIDATES TABLE ---------------- #

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_name TEXT NOT NULL,
        party_name TEXT NOT NULL,
        symbol TEXT
    )
    """)

    add_column_if_missing(cursor, "candidates", "symbol", "TEXT")

    # ---------------- VOTES TABLE ---------------- #

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter_id TEXT NOT NULL,
        candidate_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    add_column_if_missing(cursor, "votes", "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")

    # ---------------- FRAUD LOGS TABLE ---------------- #

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fraud_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter_id TEXT NOT NULL,
        reason TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    add_column_if_missing(cursor, "fraud_logs", "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")

    # ---------------- CUSTOM BLOCKCHAIN TABLE ---------------- #

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blockchain_blocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        block_index INTEGER NOT NULL,
        voter_id TEXT NOT NULL,
        candidate_id INTEGER NOT NULL,
        candidate_name TEXT,
        timestamp TEXT NOT NULL,
        previous_hash TEXT NOT NULL,
        current_hash TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


# ---------------- CUSTOM BLOCKCHAIN FUNCTIONS ---------------- #

def calculate_block_hash(block_index, voter_id, candidate_id, candidate_name, timestamp, previous_hash):
    block_data = f"{block_index}|{voter_id}|{candidate_id}|{candidate_name}|{timestamp}|{previous_hash}"
    return hashlib.sha256(block_data.encode()).hexdigest()


def get_last_block_hash():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT current_hash FROM blockchain_blocks
    ORDER BY block_index DESC
    LIMIT 1
    """)

    result = cursor.fetchone()
    conn.close()

    if result:
        return result["current_hash"]

    return "0"


def get_next_block_index():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT MAX(block_index) AS max_index FROM blockchain_blocks
    """)

    result = cursor.fetchone()
    conn.close()

    if result and result["max_index"] is not None:
        return result["max_index"] + 1

    return 1


def add_vote_to_custom_blockchain(voter_id, candidate_id, candidate_name):
    block_index = get_next_block_index()
    previous_hash = get_last_block_hash()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    current_hash = calculate_block_hash(
        block_index,
        voter_id,
        candidate_id,
        candidate_name,
        timestamp,
        previous_hash
    )

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO blockchain_blocks
    (block_index, voter_id, candidate_id, candidate_name, timestamp, previous_hash, current_hash)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        block_index,
        voter_id,
        candidate_id,
        candidate_name,
        timestamp,
        previous_hash,
        current_hash
    ))

    conn.commit()
    conn.close()

    return {
        "block_index": block_index,
        "timestamp": timestamp,
        "previous_hash": previous_hash,
        "current_hash": current_hash
    }


def verify_custom_blockchain():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT block_index, voter_id, candidate_id, candidate_name, timestamp, previous_hash, current_hash
    FROM blockchain_blocks
    ORDER BY block_index ASC
    """)

    blocks = cursor.fetchall()
    conn.close()

    previous_hash = "0"

    for block in blocks:
        block_index = block["block_index"]
        voter_id = block["voter_id"]
        candidate_id = block["candidate_id"]
        candidate_name = block["candidate_name"]
        timestamp = block["timestamp"]
        stored_previous_hash = block["previous_hash"]
        stored_current_hash = block["current_hash"]

        recalculated_hash = calculate_block_hash(
            block_index,
            voter_id,
            candidate_id,
            candidate_name,
            timestamp,
            stored_previous_hash
        )

        if stored_previous_hash != previous_hash:
            return {
                "valid": False,
                "message": f"Blockchain broken at block {block_index}. Previous hash mismatch."
            }

        if stored_current_hash != recalculated_hash:
            return {
                "valid": False,
                "message": f"Blockchain broken at block {block_index}. Data was changed."
            }

        previous_hash = stored_current_hash

    return {
        "valid": True,
        "message": "Blockchain is valid. No tampering detected."
    }


# ---------------- FACE MATCHING FUNCTIONS ---------------- #

def calculate_face_distance(face1, face2):
    if not face1 or not face2:
        return 999

    if len(face1) != len(face2):
        return 999

    total = 0

    for i in range(len(face1)):
        total += (float(face1[i]) - float(face2[i])) ** 2

    return math.sqrt(total)


def is_face_matching(stored_descriptor_text, scanned_descriptor):
    try:
        stored_descriptor = json.loads(stored_descriptor_text)

        distance = calculate_face_distance(stored_descriptor, scanned_descriptor)

        return distance <= FACE_MATCH_THRESHOLD

    except Exception as error:
        print("Face matching error:", error)
        return False


# ---------------- FRAUD LOG FUNCTION ---------------- #

def add_fraud_log(voter_id, reason):
    conn = get_db_connection()
    cursor = conn.cursor()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO fraud_logs (voter_id, reason, created_at)
    VALUES (?, ?, ?)
    """, (voter_id, reason, created_at))

    conn.commit()
    conn.close()


# ---------------- EMAIL OTP FUNCTION ---------------- #

def send_email_otp(receiver_email, otp):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD or not receiver_email:
        print("Email not configured. Admin OTP is:", otp)
        return True

    try:
        subject = "Blockchain Voting System Admin OTP"
        body = f"Your admin login OTP is: {otp}"

        message = MIMEText(body)
        message["Subject"] = subject
        message["From"] = GMAIL_USER
        message["To"] = receiver_email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, receiver_email, message.as_string())
        server.quit()

        return True

    except Exception as error:
        print("Email sending error:", error)
        print("Admin OTP is:", otp)
        return False


# ---------------- FRONTEND ROUTES ---------------- #

@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/frontend/<path:filename>")
def serve_frontend_folder(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.route("/api-health")
def api_health():
    return "Blockchain Voting Backend Running Successfully"


@app.route("/<path:filename>")
def serve_frontend_files(filename):
    file_path = os.path.join(FRONTEND_DIR, filename)

    if os.path.exists(file_path):
        return send_from_directory(FRONTEND_DIR, filename)

    return jsonify({
        "success": False,
        "message": "Page or file not found"
    }), 404


# ---------------- REGISTER VOTER API ---------------- #

@app.route("/register_voter", methods=["POST"])
def register_voter():
    data = request.get_json()

    voter_id = str(data.get("voter_id", "")).strip()
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    face_descriptor = data.get("face_descriptor")

    if not voter_id or not name or not email:
        return jsonify({
            "success": False,
            "message": "Please fill all voter details"
        })

    if not face_descriptor:
        return jsonify({
            "success": False,
            "message": "Face descriptor missing. Please capture face first."
        })

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT voter_id FROM voters
    WHERE voter_id = ?
    """, (voter_id,))

    existing_voter = cursor.fetchone()

    if existing_voter:
        conn.close()

        return jsonify({
            "success": False,
            "message": "Voter ID already registered"
        })

    cursor.execute("""
    INSERT INTO voters (voter_id, name, email, face_descriptor, has_voted)
    VALUES (?, ?, ?, ?, ?)
    """, (
        voter_id,
        name,
        email,
        json.dumps(face_descriptor),
        0
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Voter registered successfully"
    })


# ---------------- ADD CANDIDATE API ---------------- #

@app.route("/add_candidate", methods=["POST"])
def add_candidate():
    data = request.get_json()

    candidate_name = str(data.get("candidate_name", "")).strip()
    party_name = str(data.get("party_name", "")).strip()
    symbol = str(data.get("symbol", "")).strip()

    if not candidate_name or not party_name:
        return jsonify({
            "success": False,
            "message": "Please fill candidate name and party name"
        })

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO candidates (candidate_name, party_name, symbol)
    VALUES (?, ?, ?)
    """, (candidate_name, party_name, symbol))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Candidate added successfully"
    })


# ---------------- GET CANDIDATES API ---------------- #

@app.route("/candidates", methods=["GET"])
def get_candidates():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, candidate_name, party_name, symbol
    FROM candidates
    ORDER BY id ASC
    """)

    candidates = cursor.fetchall()
    conn.close()

    candidate_list = []

    for candidate in candidates:
        candidate_list.append({
            "id": candidate["id"],
            "candidate_name": candidate["candidate_name"],
            "party_name": candidate["party_name"],
            "symbol": candidate["symbol"]
        })

    return jsonify({
        "success": True,
        "candidates": candidate_list
    })


# ---------------- VOTE API ---------------- #

@app.route("/vote", methods=["POST"])
def vote():
    data = request.get_json()

    voter_id = str(data.get("voter_id", "")).strip()
    candidate_id = data.get("candidate_id")
    scanned_face_descriptor = data.get("face_descriptor")

    if not voter_id or not candidate_id:
        return jsonify({
            "success": False,
            "message": "Voter ID and candidate ID are required"
        })

    if not scanned_face_descriptor:
        return jsonify({
            "success": False,
            "message": "Face scan missing. Please scan face before voting."
        })

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check voter exists
    cursor.execute("""
    SELECT voter_id, name, email, face_descriptor, has_voted
    FROM voters
    WHERE voter_id = ?
    """, (voter_id,))

    voter = cursor.fetchone()

    if not voter:
        conn.close()

        return jsonify({
            "success": False,
            "message": "Voter not registered"
        })

    # Check duplicate vote
    if voter["has_voted"] == 1:
        conn.close()

        add_fraud_log(voter_id, "Duplicate voting attempt")

        return jsonify({
            "success": False,
            "alert": True,
            "message": "Duplicate voting attempt detected. This voter has already voted."
        })

    # Check face match
    face_match = is_face_matching(voter["face_descriptor"], scanned_face_descriptor)

    if not face_match:
        conn.close()

        add_fraud_log(voter_id, "Face verification failed")

        return jsonify({
            "success": False,
            "alert": True,
            "message": "Fraud detected. Face does not match registered voter."
        })

    # Check candidate exists
    cursor.execute("""
    SELECT candidate_name
    FROM candidates
    WHERE id = ?
    """, (candidate_id,))

    candidate = cursor.fetchone()

    if not candidate:
        conn.close()

        return jsonify({
            "success": False,
            "message": "Candidate not found"
        })

    candidate_name = candidate["candidate_name"]

    # Save vote in normal votes table
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO votes (voter_id, candidate_id, created_at)
    VALUES (?, ?, ?)
    """, (voter_id, candidate_id, created_at))

    # Mark voter as voted
    cursor.execute("""
    UPDATE voters
    SET has_voted = 1
    WHERE voter_id = ?
    """, (voter_id,))

    conn.commit()
    conn.close()

    # Save vote in custom blockchain
    block_info = add_vote_to_custom_blockchain(
        voter_id,
        candidate_id,
        candidate_name
    )

    return jsonify({
        "success": True,
        "message": "Vote cast successfully and stored in custom blockchain",
        "block_info": block_info
    })


# ---------------- RESULTS API ---------------- #

@app.route("/results", methods=["GET"])
def get_results():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        candidates.id AS candidate_id,
        candidates.candidate_name AS candidate_name,
        candidates.party_name AS party_name,
        candidates.symbol AS symbol,
        COUNT(votes.id) AS total_votes
    FROM candidates
    LEFT JOIN votes ON candidates.id = votes.candidate_id
    GROUP BY candidates.id, candidates.candidate_name, candidates.party_name, candidates.symbol
    ORDER BY candidates.id ASC
    """)

    results = cursor.fetchall()
    conn.close()

    result_list = []

    for result in results:
        result_list.append({
            "candidate_id": result["candidate_id"],
            "candidate_name": result["candidate_name"],
            "party_name": result["party_name"],
            "symbol": result["symbol"],
            "total_votes": result["total_votes"]
        })

    return jsonify({
        "success": True,
        "results": result_list
    })


# ---------------- VOTERS API ---------------- #

@app.route("/voters", methods=["GET"])
def get_voters():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, voter_id, name, email, has_voted
    FROM voters
    ORDER BY id DESC
    """)

    voters = cursor.fetchall()
    conn.close()

    voter_list = []

    for voter in voters:
        voter_list.append({
            "id": voter["id"],
            "voter_id": voter["voter_id"],
            "name": voter["name"],
            "email": voter["email"],
            "has_voted": voter["has_voted"]
        })

    return jsonify({
        "success": True,
        "voters": voter_list
    })


# ---------------- FRAUD LOGS API ---------------- #

@app.route("/fraud_logs", methods=["GET"])
def get_fraud_logs():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, voter_id, reason, created_at
    FROM fraud_logs
    ORDER BY id DESC
    """)

    fraud_logs = cursor.fetchall()
    conn.close()

    fraud_list = []

    for log in fraud_logs:
        fraud_list.append({
            "id": log["id"],
            "voter_id": log["voter_id"],
            "reason": log["reason"],
            "created_at": log["created_at"] if log["created_at"] else "Time not available"
        })

    return jsonify({
        "success": True,
        "fraud_logs": fraud_list
    })


# ---------------- CUSTOM BLOCKCHAIN RECORDS API ---------------- #

@app.route("/blockchain_records", methods=["GET"])
def blockchain_records():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT block_index, voter_id, candidate_id, candidate_name, timestamp, previous_hash, current_hash
    FROM blockchain_blocks
    ORDER BY block_index ASC
    """)

    blocks = cursor.fetchall()
    conn.close()

    blockchain_data = []

    for block in blocks:
        blockchain_data.append({
            "block_index": block["block_index"],
            "voter_id": block["voter_id"],
            "candidate_id": block["candidate_id"],
            "candidate_name": block["candidate_name"],
            "timestamp": block["timestamp"],
            "previous_hash": block["previous_hash"],
            "current_hash": block["current_hash"]
        })

    verification = verify_custom_blockchain()

    return jsonify({
        "success": True,
        "blockchain_valid": verification["valid"],
        "verification_message": verification["message"],
        "blocks": blockchain_data
    })


@app.route("/verify_blockchain", methods=["GET"])
def verify_blockchain():
    verification = verify_custom_blockchain()

    return jsonify({
        "success": True,
        "blockchain_valid": verification["valid"],
        "message": verification["message"]
    })


# ---------------- DELETE CANDIDATE API ---------------- #

@app.route("/delete_candidate/<int:candidate_id>", methods=["DELETE"])
def delete_candidate(candidate_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id FROM candidates
    WHERE id = ?
    """, (candidate_id,))

    candidate = cursor.fetchone()

    if not candidate:
        conn.close()

        return jsonify({
            "success": False,
            "message": "Candidate not found"
        })

    cursor.execute("""
    DELETE FROM candidates
    WHERE id = ?
    """, (candidate_id,))

    cursor.execute("""
    DELETE FROM votes
    WHERE candidate_id = ?
    """, (candidate_id,))

    cursor.execute("""
    DELETE FROM blockchain_blocks
    WHERE candidate_id = ?
    """, (candidate_id,))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Candidate deleted successfully"
    })


@app.route("/delete_all_candidates", methods=["DELETE"])
def delete_all_candidates():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM candidates")
    cursor.execute("DELETE FROM votes")
    cursor.execute("DELETE FROM blockchain_blocks")

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "All candidates, votes, and blockchain records deleted successfully"
    })


# ---------------- DELETE VOTER API ---------------- #

@app.route("/delete_voter/<voter_id>", methods=["DELETE"])
def delete_voter(voter_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT voter_id FROM voters
    WHERE voter_id = ?
    """, (voter_id,))

    voter = cursor.fetchone()

    if not voter:
        conn.close()

        return jsonify({
            "success": False,
            "message": "Voter not found"
        })

    cursor.execute("""
    DELETE FROM voters
    WHERE voter_id = ?
    """, (voter_id,))

    cursor.execute("""
    DELETE FROM votes
    WHERE voter_id = ?
    """, (voter_id,))

    cursor.execute("""
    DELETE FROM fraud_logs
    WHERE voter_id = ?
    """, (voter_id,))

    cursor.execute("""
    DELETE FROM blockchain_blocks
    WHERE voter_id = ?
    """, (voter_id,))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Voter deleted successfully"
    })


@app.route("/delete_all_voters", methods=["DELETE"])
def delete_all_voters():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM voters")
    cursor.execute("DELETE FROM votes")
    cursor.execute("DELETE FROM fraud_logs")
    cursor.execute("DELETE FROM blockchain_blocks")

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "All voters, votes, fraud logs, and blockchain records deleted successfully"
    })


# ---------------- DELETE FRAUD LOGS API ---------------- #

@app.route("/delete_all_fraud_logs", methods=["DELETE"])
def delete_all_fraud_logs():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM fraud_logs")

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "All fraud logs deleted successfully"
    })


# ---------------- ADMIN OTP API ---------------- #

@app.route("/send_admin_otp", methods=["POST"])
def send_admin_otp():
    global current_admin_otp

    data = request.get_json()
    password = str(data.get("password", "")).strip()

    if password != ADMIN_PASSWORD:
        return jsonify({
            "success": False,
            "message": "Invalid admin password"
        })

    current_admin_otp = str(random.randint(100000, 999999))

    email_sent = send_email_otp(ADMIN_EMAIL, current_admin_otp)

    if email_sent:
        return jsonify({
            "success": True,
            "message": "OTP sent successfully"
        })

    return jsonify({
        "success": True,
        "message": "OTP generated. Check backend terminal because email is not configured."
    })


@app.route("/verify_admin_otp", methods=["POST"])
def verify_admin_otp():
    global current_admin_otp

    data = request.get_json()
    otp = str(data.get("otp", "")).strip()

    if not current_admin_otp:
        return jsonify({
            "success": False,
            "message": "OTP not generated. Please send OTP first."
        })

    if otp == current_admin_otp:
        current_admin_otp = None

        return jsonify({
            "success": True,
            "message": "Admin login successful"
        })

    return jsonify({
        "success": False,
        "message": "Invalid OTP"
    })


# ---------------- STARTUP ---------------- #

init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )