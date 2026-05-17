from flask import Flask, request
import sqlite3

app = Flask(__name__)

# DATABASE SETUP
def init_db():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # VOTERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter_id TEXT,
        name TEXT,
        email TEXT,
        has_voted INTEGER DEFAULT 0
    )
    """)

    # CANDIDATES TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_name TEXT,
        party_name TEXT,
        symbol TEXT
    )
    """)

    # VOTES TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter_id TEXT,
        candidate_id INTEGER
    )
    """)

    # FRAUD LOGS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fraud_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter_id TEXT,
        reason TEXT
    )
    """)

    conn.commit()
    conn.close()


# HOME ROUTE
@app.route("/")
def home():
    return "Backend Running Successfully"


# REGISTER VOTER API
@app.route("/register_voter", methods=["POST"])
def register_voter():

    data = request.json

    voter_id = data["voter_id"]
    name = data["name"]
    email = data["email"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO voters (voter_id, name, email)
    VALUES (?, ?, ?)
    """, (voter_id, name, email))

    conn.commit()
    conn.close()

    return {
        "message": "Voter Registered Successfully"
    }


# ADD CANDIDATE API
@app.route("/add_candidate", methods=["POST"])
def add_candidate():

    data = request.json

    candidate_name = data["candidate_name"]
    party_name = data["party_name"]
    symbol = data["symbol"]

    conn = sqlite3.connect("database.db")
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

    return {
        "message": "Candidate Added Successfully"
    }


# VOTE API
@app.route("/vote", methods=["POST"])
def vote():

    data = request.json

    voter_id = data["voter_id"]
    candidate_id = data["candidate_id"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # CHECK IF VOTER EXISTS
    cursor.execute("""
    SELECT has_voted FROM voters
    WHERE voter_id = ?
    """, (voter_id,))

    voter = cursor.fetchone()

    # VOTER NOT REGISTERED
    if voter is None:

        conn.close()

        return {
            "message": "Voter Not Registered"
        }

    # DUPLICATE VOTE DETECTION
    if voter[0] == 1:

        # STORE FRAUD LOG
        cursor.execute("""
        INSERT INTO fraud_logs (voter_id, reason)
        VALUES (?, ?)
        """, (
            voter_id,
            "Duplicate Vote Attempt"
        ))

        conn.commit()
        conn.close()

        return {
            "message": "Duplicate Vote Detected"
        }

    # STORE VOTE
    cursor.execute("""
    INSERT INTO votes (voter_id, candidate_id)
    VALUES (?, ?)
    """, (
        voter_id,
        candidate_id
    ))

    # UPDATE VOTER STATUS
    cursor.execute("""
    UPDATE voters
    SET has_voted = 1
    WHERE voter_id = ?
    """, (voter_id,))

    conn.commit()
    conn.close()

    return {
        "message": "Vote Cast Successfully"
    }


# RUN SERVER
if __name__ == "__main__":

    init_db()

    app.run(debug=True)