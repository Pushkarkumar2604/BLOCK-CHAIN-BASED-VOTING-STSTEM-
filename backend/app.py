import sqlite3
import random
import smtplib
import os
import time
import json
import math

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from web3 import Web3


# ---------------- LOAD ENV ---------------- #

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)
CORS(app)


ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


admin_otp_data = {
    "otp": None,
    "created_at": None
}


# ---------------- BLOCKCHAIN SETUP ---------------- #

BLOCKCHAIN_URL = "http://127.0.0.1:8545"

web3 = Web3(Web3.HTTPProvider(BLOCKCHAIN_URL))

contract = None
blockchain_account = None


def load_blockchain_contract():
    global contract
    global blockchain_account

    try:
        contract_path = os.path.join(
            BASE_DIR,
            "..",
            "blockchain",
            "contract-info.json"
        )

        with open(contract_path, "r") as file:
            contract_info = json.load(file)

        contract_address = contract_info["address"]
        contract_abi = contract_info["abi"]

        if not web3.is_connected():
            print("Blockchain not connected. Start Hardhat node first.")
            return

        blockchain_account = web3.eth.accounts[0]

        contract = web3.eth.contract(
            address=contract_address,
            abi=contract_abi
        )

        print("Blockchain connected successfully")
        print("Contract Address:", contract_address)

    except Exception as e:
        print("Blockchain loading error:", e)


def store_vote_on_blockchain(voter_id, candidate_id):
    if contract is None:
        return {
            "success": False,
            "tx_hash": None,
            "message": "Blockchain contract not loaded"
        }

    try:
        voter_hash = web3.keccak(text=str(voter_id))

        transaction = contract.functions.storeVote(
            voter_hash,
            int(candidate_id)
        ).transact({
            "from": blockchain_account
        })

        web3.eth.wait_for_transaction_receipt(transaction)

        return {
            "success": True,
            "tx_hash": transaction.hex(),
            "message": "Vote stored on blockchain successfully"
        }

    except Exception as e:
        print("Blockchain vote error:", e)

        return {
            "success": False,
            "tx_hash": None,
            "message": "Failed to store vote on blockchain"
        }


# ---------------- DATABASE SETUP ---------------- #

def init_db():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter_id TEXT UNIQUE,
        name TEXT,
        email TEXT,
        face_descriptor TEXT,
        has_voted INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_name TEXT,
        party_name TEXT,
        symbol TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter_id TEXT,
        candidate_id INTEGER,
        blockchain_tx_hash TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fraud_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter_id TEXT,
        reason TEXT,
        created_at TEXT
    )
    """)

    # Add missing voter columns if old database already exists
    cursor.execute("PRAGMA table_info(voters)")
    voter_columns = cursor.fetchall()
    voter_column_names = [column[1] for column in voter_columns]

    if "face_descriptor" not in voter_column_names:
        cursor.execute("""
        ALTER TABLE voters
        ADD COLUMN face_descriptor TEXT
        """)

    # Add missing vote columns if old database already exists
    cursor.execute("PRAGMA table_info(votes)")
    vote_columns = cursor.fetchall()
    vote_column_names = [column[1] for column in vote_columns]

    if "blockchain_tx_hash" not in vote_column_names:
        cursor.execute("""
        ALTER TABLE votes
        ADD COLUMN blockchain_tx_hash TEXT
        """)

    # Add missing fraud log timestamp column if old database already exists
    cursor.execute("PRAGMA table_info(fraud_logs)")
    fraud_columns = cursor.fetchall()
    fraud_column_names = [column[1] for column in fraud_columns]

    if "created_at" not in fraud_column_names:
        cursor.execute("""
        ALTER TABLE fraud_logs
        ADD COLUMN created_at TEXT
        """)

    conn.commit()
    conn.close()


# ---------------- FACE MATCHING FUNCTION ---------------- #

def calculate_face_distance(face1, face2):

    if len(face1) != len(face2):
        return 999

    total = 0

    for i in range(len(face1)):
        total += (face1[i] - face2[i]) ** 2

    distance = math.sqrt(total)

    return distance


# ---------------- HOME ROUTE ---------------- #

@app.route("/")
def home():
    return "Blockchain Voting Backend Running Successfully"


# ---------------- REGISTER VOTER API ---------------- #

@app.route("/register_voter", methods=["POST"])
def register_voter():

    data = request.get_json()

    voter_id = data.get("voter_id")
    name = data.get("name")
    email = data.get("email")
    face_descriptor = data.get("face_descriptor")

    if not voter_id or not name or not email:
        return jsonify({
            "success": False,
            "message": "All fields are required"
        })

    if not face_descriptor:
        return jsonify({
            "success": False,
            "message": "Face data is required. Please capture face first."
        })

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM voters
    WHERE voter_id = ?
    """, (voter_id,))

    existing_voter = cursor.fetchone()

    if existing_voter:
        conn.close()
        return jsonify({
            "success": False,
            "message": "Voter already registered"
        })

    face_descriptor_json = json.dumps(face_descriptor)

    cursor.execute("""
    INSERT INTO voters (
        voter_id,
        name,
        email,
        face_descriptor
    )
    VALUES (?, ?, ?, ?)
    """, (
        voter_id,
        name,
        email,
        face_descriptor_json
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Voter Registered Successfully With Face"
    })


# ---------------- GET ALL VOTERS API ---------------- #

@app.route("/voters", methods=["GET"])
def get_voters():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        voter_id,
        name,
        email,
        has_voted
    FROM voters
    ORDER BY id DESC
    """)

    voters = cursor.fetchall()

    conn.close()

    voter_list = []

    for voter in voters:
        voter_list.append({
            "id": voter[0],
            "voter_id": voter[1],
            "name": voter[2],
            "email": voter[3],
            "has_voted": voter[4]
        })

    return jsonify({
        "success": True,
        "voters": voter_list
    })


# ---------------- DELETE SINGLE VOTER API ---------------- #

@app.route("/delete_voter/<voter_id>", methods=["DELETE"])
def delete_voter(voter_id):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM voters
    WHERE voter_id = ?
    """, (voter_id,))

    voter = cursor.fetchone()

    if voter is None:
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

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Voter deleted successfully"
    })


# ---------------- DELETE ALL VOTERS API ---------------- #

@app.route("/delete_all_voters", methods=["DELETE"])
def delete_all_voters():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM voters
    """)

    cursor.execute("""
    DELETE FROM votes
    """)

    cursor.execute("""
    DELETE FROM fraud_logs
    """)

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "All registered voters, local votes, and fraud logs deleted successfully"
    })


# ---------------- ADD CANDIDATE API ---------------- #

@app.route("/add_candidate", methods=["POST"])
def add_candidate():

    data = request.get_json()

    candidate_name = data.get("candidate_name")
    party_name = data.get("party_name")
    symbol = data.get("symbol")

    if not candidate_name or not party_name or not symbol:
        return jsonify({
            "success": False,
            "message": "All fields are required"
        })

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO candidates (
        candidate_name,
        party_name,
        symbol
    )
    VALUES (?, ?, ?)
    """, (
        candidate_name,
        party_name,
        symbol
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Candidate Added Successfully"
    })


# ---------------- GET ALL CANDIDATES API ---------------- #

@app.route("/candidates", methods=["GET"])
def get_candidates():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM candidates
    """)

    candidates = cursor.fetchall()

    conn.close()

    candidate_list = []

    for candidate in candidates:
        candidate_list.append({
            "id": candidate[0],
            "candidate_name": candidate[1],
            "party_name": candidate[2],
            "symbol": candidate[3]
        })

    return jsonify({
        "success": True,
        "candidates": candidate_list
    })


# ---------------- DELETE CANDIDATE API ---------------- #

@app.route("/delete_candidate/<int:candidate_id>", methods=["DELETE"])
def delete_candidate(candidate_id):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM candidates
    WHERE id = ?
    """, (candidate_id,))

    candidate = cursor.fetchone()

    if candidate is None:
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

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Candidate deleted successfully"
    })
# ---------------- DELETE ALL CANDIDATES API ---------------- #

@app.route("/delete_all_candidates", methods=["DELETE"])
def delete_all_candidates():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM candidates
    """)

    cursor.execute("""
    DELETE FROM votes
    """)

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "All candidates and local vote records deleted successfully"
    })


# ---------------- VOTE API WITH FACE + BLOCKCHAIN ---------------- #

@app.route("/vote", methods=["POST"])
def vote():

    data = request.get_json()

    voter_id = data.get("voter_id")
    candidate_id = data.get("candidate_id")
    live_face_descriptor = data.get("face_descriptor")

    if not voter_id or not candidate_id:
        return jsonify({
            "success": False,
            "message": "Voter ID and Candidate ID are required"
        })

    if not live_face_descriptor:
        return jsonify({
            "success": False,
            "message": "Please scan your face before voting"
        })

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT has_voted, face_descriptor FROM voters
    WHERE voter_id = ?
    """, (voter_id,))

    voter = cursor.fetchone()

    if voter is None:
        conn.close()
        return jsonify({
            "success": False,
            "message": "Voter Not Found"
        })

    cursor.execute("""
    SELECT * FROM candidates
    WHERE id = ?
    """, (candidate_id,))

    candidate = cursor.fetchone()

    if candidate is None:
        conn.close()
        return jsonify({
            "success": False,
            "message": "Candidate Not Found"
        })

    has_voted = voter[0]
    registered_face_json = voter[1]

    if registered_face_json is None:
        conn.close()
        return jsonify({
            "success": False,
            "message": "No registered face found for this voter"
        })

    registered_face_descriptor = json.loads(registered_face_json)

    face_distance = calculate_face_distance(
        registered_face_descriptor,
        live_face_descriptor
    )

    print("Face Distance:", face_distance)

    if face_distance > 0.6:

        cursor.execute("""
        INSERT INTO fraud_logs (
            voter_id,
            reason,
            created_at
        )
        VALUES (?, ?, datetime('now', 'localtime'))
        """, (
            voter_id,
            "Unauthorized person detected: face mismatch"
        ))

        conn.commit()
        conn.close()

        return jsonify({
            "success": False,
            "message": "Unauthorized Person Detected. Face does not match registered voter.",
            "alert": True
        })

    if has_voted == 1:

        cursor.execute("""
        INSERT INTO fraud_logs (
            voter_id,
            reason,
            created_at
        )
        VALUES (?, ?, datetime('now', 'localtime'))
        """, (
            voter_id,
            "Duplicate voting attempt"
        ))

        conn.commit()
        conn.close()

        return jsonify({
            "success": False,
            "message": "Duplicate Vote Detected",
            "alert": True
        })

    blockchain_result = store_vote_on_blockchain(voter_id, candidate_id)

    if blockchain_result["success"] is False:
        conn.close()

        return jsonify({
            "success": False,
            "message": "Face verified but blockchain storage failed. Please check Hardhat node.",
            "blockchain_message": blockchain_result["message"]
        })

    cursor.execute("""
    INSERT INTO votes (
        voter_id,
        candidate_id,
        blockchain_tx_hash
    )
    VALUES (?, ?, ?)
    """, (
        voter_id,
        candidate_id,
        blockchain_result["tx_hash"]
    ))

    cursor.execute("""
    UPDATE voters
    SET has_voted = 1
    WHERE voter_id = ?
    """, (voter_id,))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Face Verified. Vote Cast Successfully and Stored on Blockchain",
        "transaction_hash": blockchain_result["tx_hash"]
    })


# ---------------- RESULTS API ---------------- #

@app.route("/results", methods=["GET"])
def results():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        candidates.id,
        candidates.candidate_name,
        candidates.party_name,
        candidates.symbol,
        COUNT(votes.candidate_id) as total_votes
    FROM candidates
    LEFT JOIN votes
    ON candidates.id = votes.candidate_id
    GROUP BY candidates.id
    """)

    results = cursor.fetchall()

    conn.close()

    final_results = []

    for row in results:
        final_results.append({
            "candidate_id": row[0],
            "candidate_name": row[1],
            "party_name": row[2],
            "symbol": row[3],
            "total_votes": row[4]
        })

    return jsonify({
        "success": True,
        "results": final_results
    })


# ---------------- FRAUD LOGS API WITH TIMING ---------------- #

@app.route("/fraud_logs", methods=["GET"])
def fraud_logs():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        voter_id,
        reason,
        created_at
    FROM fraud_logs
    ORDER BY id DESC
    """)

    logs = cursor.fetchall()

    conn.close()

    fraud_list = []

    for log in logs:
        fraud_list.append({
            "id": log[0],
            "voter_id": log[1],
            "reason": log[2],
            "created_at": log[3] if log[3] else "Time not available"
        })

    return jsonify({
        "success": True,
        "fraud_logs": fraud_list
    })


# ---------------- DELETE ALL FRAUD LOGS API ---------------- #

@app.route("/delete_all_fraud_logs", methods=["DELETE"])
def delete_all_fraud_logs():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM fraud_logs
    """)

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "All fraud logs deleted successfully"
    })


# ---------------- LOCAL DATABASE BLOCKCHAIN TRANSACTIONS API ---------------- #

@app.route("/vote_transactions", methods=["GET"])
def vote_transactions():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        votes.id,
        votes.voter_id,
        votes.candidate_id,
        candidates.candidate_name,
        votes.blockchain_tx_hash
    FROM votes
    LEFT JOIN candidates
    ON votes.candidate_id = candidates.id
    ORDER BY votes.id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    transactions = []

    for row in rows:
        transactions.append({
            "vote_id": row[0],
            "voter_id": row[1],
            "candidate_id": row[2],
            "candidate_name": row[3],
            "blockchain_tx_hash": row[4]
        })

    return jsonify({
        "success": True,
        "transactions": transactions
    })


# ---------------- BLOCKCHAIN VOTES API ---------------- #

@app.route("/blockchain_votes", methods=["GET"])
def blockchain_votes():

    if contract is None:
        return jsonify({
            "success": False,
            "message": "Blockchain contract not loaded"
        })

    try:
        total_votes = contract.functions.getTotalVotesOnChain().call()

        vote_list = []

        for index in range(total_votes):
            vote_data = contract.functions.getVote(index).call()

            vote_list.append({
                "index": index,
                "voter_hash": vote_data[0].hex(),
                "candidate_id": vote_data[1],
                "timestamp": vote_data[2]
            })

        return jsonify({
            "success": True,
            "total_votes_on_chain": total_votes,
            "votes": vote_list
        })

    except Exception as e:
        print("Blockchain votes read error:", e)

        return jsonify({
            "success": False,
            "message": "Unable to read blockchain votes"
        })


# ---------------- SEND EMAIL FUNCTION ---------------- #

def send_email_otp(receiver_email, otp):

    subject = "Admin Login OTP - Blockchain Voting System"

    body = f"""
Your admin login OTP is: {otp}

This OTP is valid for 5 minutes.

If you did not request this OTP, please ignore this email.
"""

    message = MIMEMultipart()
    message["From"] = GMAIL_USER
    message["To"] = receiver_email
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()

    server.login(GMAIL_USER, GMAIL_APP_PASSWORD)

    server.sendmail(GMAIL_USER, receiver_email, message.as_string())

    server.quit()


# ---------------- SEND ADMIN OTP API ---------------- #

@app.route("/send_admin_otp", methods=["POST"])
def send_admin_otp():

    data = request.get_json()

    entered_password = data.get("password")

    if entered_password != ADMIN_PASSWORD:
        return jsonify({
            "success": False,
            "message": "Wrong admin password"
        })

    otp = str(random.randint(100000, 999999))

    admin_otp_data["otp"] = otp
    admin_otp_data["created_at"] = time.time()

    try:
        send_email_otp(ADMIN_EMAIL, otp)

        return jsonify({
            "success": True,
            "message": "OTP sent to admin email"
        })

    except Exception as e:

        print("Email Error:", e)

        return jsonify({
            "success": False,
            "message": "Failed to send OTP. Check Gmail app password."
        })


# ---------------- VERIFY ADMIN OTP API ---------------- #

@app.route("/verify_admin_otp", methods=["POST"])
def verify_admin_otp():

    data = request.get_json()

    entered_otp = data.get("otp")

    saved_otp = admin_otp_data["otp"]
    created_at = admin_otp_data["created_at"]

    if saved_otp is None or created_at is None:
        return jsonify({
            "success": False,
            "message": "No OTP generated. Please request OTP first."
        })

    current_time = time.time()

    if current_time - created_at > 300:

        admin_otp_data["otp"] = None
        admin_otp_data["created_at"] = None

        return jsonify({
            "success": False,
            "message": "OTP expired. Please request a new OTP."
        })

    if entered_otp == saved_otp:

        admin_otp_data["otp"] = None
        admin_otp_data["created_at"] = None

        return jsonify({
            "success": True,
            "message": "Admin login successful"
        })

    return jsonify({
        "success": False,
        "message": "Invalid OTP"
    })


# ---------------- MAIN ---------------- #

if __name__ == "__main__":

    init_db()

    load_blockchain_contract()

    app.run(debug=True)