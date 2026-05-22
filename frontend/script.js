const API_URL = "";

let faceModelsLoaded = false;
let registrationFaceDescriptor = null;
let votingFaceDescriptor = null;
let chartObject = null;


// ---------------- PREVENT PAGE AUTO REFRESH ----------------

document.addEventListener("submit", function (event) {
    event.preventDefault();
});


// ---------------- LOAD FACE MODELS ----------------

async function loadFaceModels() {
    if (faceModelsLoaded === true) {
        return;
    }

    try {
        await faceapi.nets.tinyFaceDetector.loadFromUri("/frontend/models");
        await faceapi.nets.faceLandmark68Net.loadFromUri("/frontend/models");
        await faceapi.nets.faceRecognitionNet.loadFromUri("/frontend/models");

        faceModelsLoaded = true;
        console.log("Face models loaded successfully");

    } catch (error) {
        console.log("Face model loading error:", error);

        showVotePopup(
            "error",
            "Face Models Error",
            "Face models not loaded. Check frontend/models folder."
        );
    }
}


// ---------------- REGISTRATION CAMERA ----------------

async function startRegistrationCamera() {
    await loadFaceModels();

    const video = document.getElementById("reg_camera");

    if (!video) {
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: true
        });

        video.srcObject = stream;

    } catch (error) {
        playErrorBeep();

        showVotePopup(
            "error",
            "Camera Permission Denied",
            "Please allow camera access for face registration."
        );

        console.log(error);
    }
}


// ---------------- CAPTURE FACE FOR REGISTRATION ----------------

async function captureFaceForRegistration() {
    await loadFaceModels();

    const video = document.getElementById("reg_camera");
    const status = document.getElementById("faceRegisterStatus");

    if (!video) {
        return;
    }

    const detection = await faceapi
        .detectSingleFace(
            video,
            new faceapi.TinyFaceDetectorOptions()
        )
        .withFaceLandmarks()
        .withFaceDescriptor();

    if (!detection) {
        registrationFaceDescriptor = null;

        if (status) {
            status.innerText = "No face detected. Please try again.";
            status.style.color = "red";
        }

        playErrorBeep();

        showVotePopup(
            "error",
            "Face Not Detected",
            "Please keep your face clearly visible in the camera."
        );

        return;
    }

    registrationFaceDescriptor = Array.from(detection.descriptor);

    if (status) {
        status.innerText = "Face captured successfully";
        status.style.color = "green";
    }

    playSuccessBeep();

    showVotePopup(
        "success",
        "Face Captured Successfully",
        "Voter face has been captured successfully."
    );
}


// ---------------- VOTING CAMERA ----------------

async function startCamera() {
    await loadFaceModels();

    const video = document.getElementById("camera");

    if (!video) {
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: true
        });

        video.srcObject = stream;

    } catch (error) {
        playErrorBeep();

        showVotePopup(
            "error",
            "Camera Permission Denied",
            "Please allow camera access for voting."
        );

        console.log(error);
    }
}


// ---------------- SCAN FACE FOR VOTING ----------------

async function scanFace() {
    await loadFaceModels();

    const video = document.getElementById("camera");
    const status = document.getElementById("faceStatus");

    if (!video) {
        return;
    }

    const detection = await faceapi
        .detectSingleFace(
            video,
            new faceapi.TinyFaceDetectorOptions()
        )
        .withFaceLandmarks()
        .withFaceDescriptor();

    if (!detection) {
        votingFaceDescriptor = null;

        if (status) {
            status.innerText = "No face detected. Please try again.";
            status.style.color = "red";
        }

        playErrorBeep();

        showVotePopup(
            "error",
            "Face Not Detected",
            "Please scan your face clearly before voting."
        );

        return;
    }

    votingFaceDescriptor = Array.from(detection.descriptor);

    if (status) {
        status.innerText = "Face scanned successfully";
        status.style.color = "green";
    }

    playSuccessBeep();

    showVotePopup(
        "success",
        "Face Scanned Successfully",
        "Face scanned successfully. You can now vote."
    );
}


// ---------------- REGISTER VOTER ----------------

async function registerVoter() {
    const voter_id = document.getElementById("voter_id").value;
    const name = document.getElementById("name").value;
    const email = document.getElementById("email").value;

    if (voter_id === "" || name === "" || email === "") {
        showMessage("registerMessage", "Please fill all fields", "red");

        playErrorBeep();

        showVotePopup(
            "error",
            "Missing Details",
            "Please fill Voter ID, Name, and Email."
        );

        return;
    }

    if (registrationFaceDescriptor === null) {
        showMessage("registerMessage", "Please capture voter face first", "red");

        playErrorBeep();

        showVotePopup(
            "error",
            "Face Not Captured",
            "Please capture voter face before registration."
        );

        return;
    }

    try {
        const response = await fetch(`${API_URL}/register_voter`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                voter_id: voter_id,
                name: name,
                email: email,
                face_descriptor: registrationFaceDescriptor
            })
        });

        const data = await response.json();

        showMessage(
            "registerMessage",
            data.message,
            data.success ? "green" : "red"
        );

        if (data.success === true) {
            playSuccessBeep();

            showVotePopup(
                "success",
                "Voter Registered Successfully",
                "Voter registration completed successfully."
            );
        } else {
            playErrorBeep();

            showVotePopup(
                "error",
                "Registration Failed",
                data.message
            );
        }

    } catch (error) {
        showMessage("registerMessage", "Backend connection failed", "red");

        playErrorBeep();

        showVotePopup(
            "error",
            "Backend Error",
            "Backend connection failed."
        );

        console.log(error);
    }
}


// ---------------- ADD CANDIDATE ----------------

async function addCandidate() {
    const candidate_name = document.getElementById("candidate_name").value;
    const party_name = document.getElementById("party_name").value;
    const symbol = document.getElementById("symbol").value;

    if (candidate_name === "" || party_name === "" || symbol === "") {
        showMessage("candidateMessage", "Please fill all fields", "red");

        playErrorBeep();

        showVotePopup(
            "error",
            "Missing Details",
            "Please fill candidate name, party name, and candidate photo file name."
        );

        return;
    }

    try {
        const response = await fetch(`${API_URL}/add_candidate`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                candidate_name: candidate_name,
                party_name: party_name,
                symbol: symbol
            })
        });

        const data = await response.json();

        showMessage(
            "candidateMessage",
            data.message,
            data.success ? "green" : "red"
        );

        if (data.success === true) {
            playSuccessBeep();

            showVotePopup(
                "success",
                "Candidate Added Successfully",
                "Candidate has been registered successfully."
            );

            document.getElementById("candidate_name").value = "";
            document.getElementById("party_name").value = "";
            document.getElementById("symbol").value = "";
        } else {
            playErrorBeep();

            showVotePopup(
                "error",
                "Candidate Add Failed",
                data.message
            );
        }

    } catch (error) {
        showMessage("candidateMessage", "Backend connection failed", "red");

        playErrorBeep();

        showVotePopup(
            "error",
            "Backend Error",
            "Backend connection failed."
        );

        console.log(error);
    }
}


// ---------------- LOAD CANDIDATES ON VOTING PAGE ----------------

async function loadCandidates() {
    const tableBody = document.getElementById("candidateTableBody");

    if (!tableBody) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/candidates`);
        const data = await response.json();

        tableBody.innerHTML = "";

        if (!data.candidates || data.candidates.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="4">No candidates registered yet.</td>
                </tr>
            `;
            return;
        }

        data.candidates.forEach((candidate) => {
            const row = document.createElement("tr");

            const candidateCode = `CAND-${String(candidate.id).padStart(3, "0")}`;

            row.innerHTML = `
                <td>
                    <div class="candidate-photo-circle">
                        <img 
                            src="images/${candidate.symbol}" 
                            alt="${candidate.candidate_name}"
                            onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';"
                        >

                        <span class="photo-fallback">
                            ${candidate.candidate_name.charAt(0).toUpperCase()}
                        </span>
                    </div>
                </td>

                <td>
                    <span class="candidate-code">
                        ${candidateCode}
                    </span>
                </td>

                <td>
                    <strong>${candidate.candidate_name}</strong>
                </td>

                <td>
                    <button 
                        type="button"
                        class="vote-btn" 
                        onclick="voteForCandidate(${candidate.id})"
                    >
                        Vote
                    </button>
                </td>
            `;

            tableBody.appendChild(row);
        });

    } catch (error) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="4">Unable to load candidates.</td>
            </tr>
        `;

        console.log(error);
    }
}


// ---------------- VOTE ----------------

async function voteForCandidate(candidate_id) {
    const voterInput = document.getElementById("vote_voter_id");
    const voter_id = voterInput ? voterInput.value : "";

    if (voter_id === "") {
        showMessage("voteMessage", "Please enter Voter ID", "red");

        playErrorBeep();

        showVotePopup(
            "error",
            "Missing Voter ID",
            "Please enter your voter ID before voting."
        );

        return;
    }

    if (votingFaceDescriptor === null) {
        showMessage("voteMessage", "Please scan your face before voting", "red");

        playErrorBeep();

        showVotePopup(
            "error",
            "Face Not Scanned",
            "Please scan your face before voting."
        );

        return;
    }

    try {
        const response = await fetch(`${API_URL}/vote`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                voter_id: voter_id,
                candidate_id: candidate_id,
                face_descriptor: votingFaceDescriptor
            })
        });

        const data = await response.json();

        console.log("Vote response:", data);

        if (data.success === true) {
            showMessage("voteMessage", data.message, "green");

            playSuccessBeep();

            showVotePopup(
                "success",
                "Congratulations!",
                "Your vote has been cast successfully and stored on blockchain."
            );

            return;
        }

        if (data.alert === true) {
            showMessage("voteMessage", data.message, "red");

            playFraudSiren();

            showVotePopup(
                "fraud",
                "Duplicate Vote Detected",
                data.message
            );

            return;
        }

        showMessage("voteMessage", data.message, "red");

        playErrorBeep();

        showVotePopup(
            "error",
            "Voting Failed",
            data.message
        );

    } catch (error) {
        showMessage("voteMessage", "Backend connection failed", "red");

        playErrorBeep();

        showVotePopup(
            "error",
            "Backend Error",
            "Backend connection failed."
        );

        console.log(error);
    }
}


// ---------------- SEND ADMIN OTP ----------------

async function sendAdminOTP() {
    const password = document.getElementById("admin_password").value;

    if (password === "") {
        showMessage("adminLoginMessage", "Enter admin password", "red");

        playErrorBeep();

        showVotePopup(
            "error",
            "Missing Password",
            "Please enter admin password."
        );

        return;
    }

    try {
        const response = await fetch(`${API_URL}/send_admin_otp`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                password: password
            })
        });

        const data = await response.json();

        showMessage(
            "adminLoginMessage",
            data.message,
            data.success ? "green" : "red"
        );

        if (data.success === true) {
            playSuccessBeep();

            showVotePopup(
                "success",
                "OTP Sent",
                data.message
            );
        } else {
            playErrorBeep();

            showVotePopup(
                "error",
                "Login Failed",
                data.message
            );
        }

    } catch (error) {
        showMessage("adminLoginMessage", "Backend connection failed", "red");

        playErrorBeep();

        showVotePopup(
            "error",
            "Backend Error",
            "Backend connection failed."
        );

        console.log(error);
    }
}


// ---------------- VERIFY ADMIN OTP ----------------

async function verifyAdminOTP() {
    const otp = document.getElementById("admin_otp").value;

    if (otp === "") {
        showMessage("adminLoginMessage", "Enter OTP", "red");

        playErrorBeep();

        showVotePopup(
            "error",
            "Missing OTP",
            "Please enter OTP."
        );

        return;
    }

    try {
        const response = await fetch(`${API_URL}/verify_admin_otp`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                otp: otp
            })
        });

        const data = await response.json();

        if (data.success === true) {
            playSuccessBeep();

            showVotePopup(
                "success",
                "Admin Login Successful",
                data.message
            );

            localStorage.setItem("adminLoggedIn", "true");

            setTimeout(() => {
                window.location.href = "admin-dashboard.html";
            }, 1200);

        } else {
            showMessage("adminLoginMessage", data.message, "red");

            playErrorBeep();

            showVotePopup(
                "error",
                "Invalid OTP",
                data.message
            );
        }

    } catch (error) {
        showMessage("adminLoginMessage", "Backend connection failed", "red");

        playErrorBeep();

        showVotePopup(
            "error",
            "Backend Error",
            "Backend connection failed."
        );

        console.log(error);
    }
}


// ---------------- ADMIN LOGIN CHECKS ----------------

function checkAdminLogin() {
    const loggedIn = localStorage.getItem("adminLoggedIn");

    if (loggedIn !== "true") {
        window.location.href = "admin-login.html";
        return;
    }

    loadResults();
}


function checkOnlyAdminLogin() {
    const loggedIn = localStorage.getItem("adminLoggedIn");

    if (loggedIn !== "true") {
        window.location.href = "admin-login.html";
        return false;
    }

    return true;
}


// ---------------- ADMIN LOGOUT ----------------

function adminLogout() {
    localStorage.removeItem("adminLoggedIn");
    window.location.href = "admin-login.html";
}


// ---------------- SEPARATE MANAGE PAGES ----------------

function loadManageVotersPage() {
    if (checkOnlyAdminLogin() === false) {
        return;
    }

    loadAdminVoters();
}


function loadManageCandidatesPage() {
    if (checkOnlyAdminLogin() === false) {
        return;
    }

    loadAdminCandidates();
}


function loadManageFraudPage() {
    if (checkOnlyAdminLogin() === false) {
        return;
    }

    loadFraudLogs();
}


// ---------------- MANAGE DROPDOWN ----------------

function toggleManageDropdown() {
    const menu = document.getElementById("manageDropdownMenu");

    if (!menu) {
        return;
    }

    if (menu.style.display === "block") {
        menu.style.display = "none";
    } else {
        menu.style.display = "block";
    }
}


// ---------------- LOAD RESULTS ----------------

async function loadResults() {
    const resultsBox = document.getElementById("resultsBox");

    if (!resultsBox) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/results`);
        const data = await response.json();

        resultsBox.innerHTML = "";

        const labels = [];
        const votes = [];

        if (!data.results || data.results.length === 0) {
            resultsBox.innerHTML = "<p>No results found.</p>";
            drawPieChart([], []);
            return;
        }

        data.results.forEach(result => {
            labels.push(result.candidate_name);
            votes.push(result.total_votes);

            const card = document.createElement("div");

            card.className = "result-card";

            const candidateCode = `CAND-${String(result.candidate_id).padStart(3, "0")}`;

            card.innerHTML = `
                <strong>Candidate Code:</strong> ${candidateCode}<br>
                <strong>Candidate:</strong> ${result.candidate_name}<br>
                <strong>Total Votes:</strong> ${result.total_votes}
            `;

            resultsBox.appendChild(card);
        });

        drawPieChart(labels, votes);

    } catch (error) {
        resultsBox.innerHTML = "<p>Unable to load results.</p>";
        console.log(error);
    }
}


// ---------------- PIE CHART ----------------

function drawPieChart(labels, votes) {
    const chartCanvas = document.getElementById("resultChart");

    if (!chartCanvas) {
        return;
    }

    if (chartObject !== null) {
        chartObject.destroy();
    }

    chartObject = new Chart(chartCanvas, {
        type: "pie",
        data: {
            labels: labels,
            datasets: [{
                label: "Votes",
                data: votes
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: "bottom"
                }
            }
        }
    });
}


// ---------------- LOAD FRAUD LOGS ----------------

async function loadFraudLogs() {
    const fraudBox = document.getElementById("fraudBox");

    if (!fraudBox) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/fraud_logs`);
        const data = await response.json();

        fraudBox.innerHTML = "";

        if (!data.fraud_logs || data.fraud_logs.length === 0) {
            fraudBox.innerHTML = "<p>No fraud attempts yet.</p>";
            return;
        }

        data.fraud_logs.forEach(log => {
            const card = document.createElement("div");

            card.className = "fraud-card";

            card.innerHTML = `
                <strong>Fraud ID:</strong> ${log.id}<br>
                <strong>Voter ID:</strong> ${log.voter_id}<br>
                <strong>Reason:</strong> ${log.reason}<br>
                <strong>Time:</strong> ${log.created_at}
            `;

            fraudBox.appendChild(card);
        });

    } catch (error) {
        fraudBox.innerHTML = "<p>Unable to load fraud logs.</p>";
        console.log(error);
    }
}


// ---------------- LOAD CANDIDATES IN ADMIN DASHBOARD ----------------

async function loadAdminCandidates() {
    const adminCandidateBox = document.getElementById("adminCandidateBox");

    if (!adminCandidateBox) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/candidates`);
        const data = await response.json();

        adminCandidateBox.innerHTML = "";

        if (!data.candidates || data.candidates.length === 0) {
            adminCandidateBox.innerHTML = "<p>No candidates found.</p>";
            return;
        }

        data.candidates.forEach((candidate) => {
            const card = document.createElement("div");

            card.className = "admin-candidate-card";

            const candidateCode = `CAND-${String(candidate.id).padStart(3, "0")}`;

            card.innerHTML = `
                <div>
                    <strong>${candidateCode}</strong><br>
                    Candidate: ${candidate.candidate_name}<br>
                    Photo File: ${candidate.symbol}
                </div>

                <button type="button" class="delete-btn" onclick="deleteCandidate(${candidate.id})">
                    Delete Candidate
                </button>
            `;

            adminCandidateBox.appendChild(card);
        });

    } catch (error) {
        adminCandidateBox.innerHTML = "<p>Unable to load candidates.</p>";
        console.log(error);
    }
}


// ---------------- DELETE CANDIDATE ----------------

async function deleteCandidate(candidate_id) {
    const confirmDelete = confirm(
        "Are you sure you want to delete this candidate?"
    );

    if (confirmDelete === false) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/delete_candidate/${candidate_id}`, {
            method: "DELETE"
        });

        const data = await response.json();

        if (data.success === true) {
            playSuccessBeep();

            showVotePopup(
                "success",
                "Candidate Deleted",
                data.message
            );

            loadAdminCandidates();
            loadResults();

        } else {
            playErrorBeep();

            showVotePopup(
                "error",
                "Delete Failed",
                data.message
            );
        }

    } catch (error) {
        playErrorBeep();

        showVotePopup(
            "error",
            "Backend Error",
            "Unable to delete candidate."
        );

        console.log(error);
    }
}


// ---------------- DELETE ALL CANDIDATES ----------------

async function deleteAllCandidates() {
    const confirmDelete = confirm(
        "Are you sure you want to delete ALL candidates? This will also clear local vote records."
    );

    if (confirmDelete === false) {
        return;
    }

    const secondConfirm = confirm(
        "Final confirmation: This action cannot be undone. Delete all candidates?"
    );

    if (secondConfirm === false) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/delete_all_candidates`, {
            method: "DELETE"
        });

        const data = await response.json();

        if (data.success === true) {
            playSuccessBeep();

            showVotePopup(
                "success",
                "All Candidates Deleted",
                data.message
            );

            loadAdminCandidates();
            loadResults();

        } else {
            playErrorBeep();

            showVotePopup(
                "error",
                "Delete Failed",
                data.message
            );
        }

    } catch (error) {
        playErrorBeep();

        showVotePopup(
            "error",
            "Backend Error",
            "Unable to delete all candidates."
        );

        console.log(error);
    }
}


// ---------------- LOAD VOTERS IN ADMIN DASHBOARD ----------------

async function loadAdminVoters() {
    const adminVoterBox = document.getElementById("adminVoterBox");

    if (!adminVoterBox) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/voters`);
        const data = await response.json();

        adminVoterBox.innerHTML = "";

        if (!data.voters || data.voters.length === 0) {
            adminVoterBox.innerHTML = "<p>No registered voters found.</p>";
            return;
        }

        data.voters.forEach((voter, index) => {
            const card = document.createElement("div");

            card.className = "admin-voter-card";

            const statusText = voter.has_voted === 1 ? "Voted" : "Not Voted";
            const statusClass = voter.has_voted === 1 ? "voted-badge" : "not-voted-badge";

            card.innerHTML = `
                <div>
                    <strong>${index + 1}. ${voter.name}</strong><br>
                    Voter ID: ${voter.voter_id}<br>
                    Email: ${voter.email}<br>
                    Status: <span class="${statusClass}">${statusText}</span>
                </div>

                <button type="button" class="delete-btn" onclick="deleteVoter('${voter.voter_id}')">
                    Delete Voter
                </button>
            `;

            adminVoterBox.appendChild(card);
        });

    } catch (error) {
        adminVoterBox.innerHTML = "<p>Unable to load voters.</p>";
        console.log(error);
    }
}


// ---------------- DELETE VOTER ----------------

async function deleteVoter(voter_id) {
    const confirmDelete = confirm(
        "Are you sure you want to delete this registered voter?"
    );

    if (confirmDelete === false) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/delete_voter/${voter_id}`, {
            method: "DELETE"
        });

        const data = await response.json();

        if (data.success === true) {
            playSuccessBeep();

            showVotePopup(
                "success",
                "Voter Deleted",
                data.message
            );

            loadAdminVoters();
            loadResults();
            loadFraudLogs();

        } else {
            playErrorBeep();

            showVotePopup(
                "error",
                "Delete Failed",
                data.message
            );
        }

    } catch (error) {
        playErrorBeep();

        showVotePopup(
            "error",
            "Backend Error",
            "Unable to delete voter."
        );

        console.log(error);
    }
}


// ---------------- DELETE ALL VOTERS ----------------

async function deleteAllVoters() {
    const confirmDelete = confirm(
        "Are you sure you want to delete ALL registered voters? This will also clear local votes and fraud logs."
    );

    if (confirmDelete === false) {
        return;
    }

    const secondConfirm = confirm(
        "Final confirmation: This action cannot be undone. Delete all voters?"
    );

    if (secondConfirm === false) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/delete_all_voters`, {
            method: "DELETE"
        });

        const data = await response.json();

        if (data.success === true) {
            playSuccessBeep();

            showVotePopup(
                "success",
                "All Voters Deleted",
                data.message
            );

            loadAdminVoters();
            loadResults();
            loadFraudLogs();

        } else {
            playErrorBeep();

            showVotePopup(
                "error",
                "Delete Failed",
                data.message
            );
        }

    } catch (error) {
        playErrorBeep();

        showVotePopup(
            "error",
            "Backend Error",
            "Unable to delete all voters."
        );

        console.log(error);
    }
}


// ---------------- DELETE ALL FRAUD LOGS ----------------

async function deleteAllFraudLogs() {
    const confirmDelete = confirm(
        "Are you sure you want to delete all fraud logs?"
    );

    if (confirmDelete === false) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/delete_all_fraud_logs`, {
            method: "DELETE"
        });

        const data = await response.json();

        if (data.success === true) {
            playSuccessBeep();

            showVotePopup(
                "success",
                "Fraud Logs Deleted",
                data.message
            );

            loadFraudLogs();

        } else {
            playErrorBeep();

            showVotePopup(
                "error",
                "Delete Failed",
                data.message
            );
        }

    } catch (error) {
        playErrorBeep();

        showVotePopup(
            "error",
            "Backend Error",
            "Unable to delete fraud logs."
        );

        console.log(error);
    }
}


// ---------------- SHOW MESSAGE ----------------

function showMessage(id, message, color) {
    const element = document.getElementById(id);

    if (element) {
        element.innerText = message;
        element.style.color = color;
    }
}


// ---------------- VOTE POPUP ----------------

function showVotePopup(type, title, message) {
    const oldPopup = document.getElementById("votePopupOverlay");

    if (oldPopup) {
        oldPopup.remove();
    }

    const overlay = document.createElement("div");
    overlay.id = "votePopupOverlay";
    overlay.className = "popup-overlay";

    let icon = "";
    let popupClass = "";
    let popupTime = 10000;

    if (type === "success") {
        icon = "✓";
        popupClass = "success-popup";
        popupTime = 10000;
    } else if (type === "fraud") {
        icon = "✕";
        popupClass = "fraud-popup";
        popupTime = 15000;
    } else {
        icon = "!";
        popupClass = "error-popup";
        popupTime = 10000;
    }

    overlay.innerHTML = `
        <div class="vote-popup ${popupClass}">
            <div class="popup-icon">
                ${icon}
            </div>

            <h2>${title}</h2>

            <p>${message}</p>

            <button type="button" onclick="closeVotePopup()">
                Close
            </button>
        </div>
    `;

    document.body.appendChild(overlay);

    setTimeout(() => {
        closeVotePopup();
    }, popupTime);
}


function closeVotePopup() {
    const popup = document.getElementById("votePopupOverlay");

    if (popup) {
        popup.remove();
    }
}


// ---------------- AUDIO CONTEXT ----------------

function createAudioContext() {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    const audioContext = new AudioContextClass();

    if (audioContext.state === "suspended") {
        audioContext.resume();
    }

    return audioContext;
}


// ---------------- SUCCESS BEEP SOUND ----------------

function playSuccessBeep() {
    try {
        const audioContext = createAudioContext();

        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        oscillator.type = "sine";
        oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
        gainNode.gain.setValueAtTime(0.45, audioContext.currentTime);

        oscillator.start();

        setTimeout(() => {
            oscillator.stop();
            audioContext.close();
        }, 500);

    } catch (error) {
        console.log("Success sound error:", error);
    }
}


// ---------------- ERROR BEEP SOUND ----------------

function playErrorBeep() {
    try {
        const audioContext = createAudioContext();

        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        oscillator.type = "square";
        oscillator.frequency.setValueAtTime(350, audioContext.currentTime);
        gainNode.gain.setValueAtTime(0.5, audioContext.currentTime);

        oscillator.start();

        setTimeout(() => {
            oscillator.stop();
            audioContext.close();
        }, 1200);

    } catch (error) {
        console.log("Error sound error:", error);
    }
}


// ---------------- FRAUD SIREN SOUND ----------------

function playFraudSiren() {
    try {
        const audioContext = createAudioContext();

        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        oscillator.type = "square";
        gainNode.gain.setValueAtTime(0.55, audioContext.currentTime);

        oscillator.start();

        let count = 0;

        const sirenInterval = setInterval(() => {
            if (count % 2 === 0) {
                oscillator.frequency.setValueAtTime(1000, audioContext.currentTime);
            } else {
                oscillator.frequency.setValueAtTime(450, audioContext.currentTime);
            }

            count++;

            if (count >= 24) {
                clearInterval(sirenInterval);
                oscillator.stop();
                audioContext.close();
            }

        }, 250);

    } catch (error) {
        console.log("Fraud siren error:", error);
    }
}
// ======================================================
// FINAL POPUP FIX - DO NOT DELETE
// This overrides older duplicate functions if present
// ======================================================


// ---------------- LOAD CANDIDATES ON VOTING PAGE - FIXED BUTTON ----------------

async function loadCandidates() {
    const tableBody = document.getElementById("candidateTableBody");

    if (!tableBody) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/candidates`);
        const data = await response.json();

        tableBody.innerHTML = "";

        if (!data.candidates || data.candidates.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="4">No candidates registered yet.</td>
                </tr>
            `;
            return;
        }

        data.candidates.forEach((candidate) => {
            const row = document.createElement("tr");

            const candidateCode = `CAND-${String(candidate.id).padStart(3, "0")}`;

            row.innerHTML = `
                <td>
                    <div class="candidate-photo-circle">
                        <img 
                            src="images/${candidate.symbol}" 
                            alt="${candidate.candidate_name}"
                            onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';"
                        >

                        <span class="photo-fallback">
                            ${candidate.candidate_name.charAt(0).toUpperCase()}
                        </span>
                    </div>
                </td>

                <td>
                    <span class="candidate-code">
                        ${candidateCode}
                    </span>
                </td>

                <td>
                    <strong>${candidate.candidate_name}</strong>
                </td>

                <td>
                    <button 
                        type="button"
                        class="vote-btn" 
                        onclick="voteForCandidate(${candidate.id}); return false;"
                    >
                        Vote
                    </button>
                </td>
            `;

            tableBody.appendChild(row);
        });

    } catch (error) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="4">Unable to load candidates.</td>
            </tr>
        `;

        console.log(error);
    }
}


// ---------------- VOTE FUNCTION - FINAL FIX ----------------

async function voteForCandidate(candidate_id) {
    const voterInput = document.getElementById("vote_voter_id");
    const voter_id = voterInput ? voterInput.value.trim() : "";

    if (voter_id === "") {
        showMessage("voteMessage", "Please enter Voter ID", "red");

        playErrorBeep();

        showVotePopup(
            "error",
            "Missing Voter ID",
            "Please enter your voter ID before voting.",
            10000
        );

        return false;
    }

    if (votingFaceDescriptor === null) {
        showMessage("voteMessage", "Please scan your face before voting", "red");

        playErrorBeep();

        showVotePopup(
            "error",
            "Face Not Scanned",
            "Please scan your face before voting.",
            10000
        );

        return false;
    }

    try {
        const response = await fetch(`${API_URL}/vote`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                voter_id: voter_id,
                candidate_id: candidate_id,
                face_descriptor: votingFaceDescriptor
            })
        });

        const data = await response.json();

        console.log("Vote response:", data);

        if (data.success === true) {
            showMessage("voteMessage", data.message, "green");

            playSuccessBeep();

            showVotePopup(
                "success",
                "Congratulations!",
                "Your vote has been cast successfully and stored on blockchain.",
                10000
            );

            return false;
        }

        if (data.alert === true) {
            showMessage("voteMessage", data.message, "red");

            playFraudSiren();

            showVotePopup(
                "fraud",
                "Duplicate Vote Detected",
                data.message,
                0
            );

            return false;
        }

        showMessage("voteMessage", data.message, "red");

        playErrorBeep();

        showVotePopup(
            "error",
            "Voting Failed",
            data.message,
            10000
        );

        return false;

    } catch (error) {
        showMessage("voteMessage", "Backend connection failed", "red");

        playErrorBeep();

        showVotePopup(
            "error",
            "Backend Error",
            "Backend connection failed.",
            10000
        );

        console.log(error);

        return false;
    }
}


// ---------------- POPUP FUNCTION - FINAL FIX ----------------

function showVotePopup(type, title, message, duration = 10000) {
    const oldPopup = document.getElementById("votePopupOverlay");

    if (oldPopup) {
        oldPopup.remove();
    }

    const overlay = document.createElement("div");
    overlay.id = "votePopupOverlay";
    overlay.className = "popup-overlay";

    overlay.style.position = "fixed";
    overlay.style.top = "0";
    overlay.style.left = "0";
    overlay.style.right = "0";
    overlay.style.bottom = "0";
    overlay.style.background = "rgba(15, 23, 42, 0.82)";
    overlay.style.display = "flex";
    overlay.style.justifyContent = "center";
    overlay.style.alignItems = "center";
    overlay.style.zIndex = "999999";

    let icon = "";
    let popupClass = "";

    if (type === "success") {
        icon = "✓";
        popupClass = "success-popup";
    } 
    
    else if (type === "fraud") {
        icon = "✕";
        popupClass = "fraud-popup";
    } 
    
    else {
        icon = "!";
        popupClass = "error-popup";
    }

    overlay.innerHTML = `
        <div class="vote-popup ${popupClass}" style="
            width: 440px;
            max-width: 90%;
            background: white;
            padding: 38px;
            border-radius: 24px;
            text-align: center;
            box-shadow: 0 25px 65px rgba(0, 0, 0, 0.45);
        ">
            <div class="popup-icon" style="
                width: 100px;
                height: 100px;
                margin: 0 auto 20px auto;
                border-radius: 50%;
                display: flex;
                justify-content: center;
                align-items: center;
                font-size: 58px;
                font-weight: 900;
                background: ${type === "fraud" ? "#fee2e2" : type === "success" ? "#dcfce7" : "#fef3c7"};
                color: ${type === "fraud" ? "#dc2626" : type === "success" ? "#16a34a" : "#d97706"};
                border: 5px solid ${type === "fraud" ? "#dc2626" : type === "success" ? "#16a34a" : "#d97706"};
            ">
                ${icon}
            </div>

            <h2 style="
                font-size: 30px;
                color: ${type === "fraud" ? "#dc2626" : type === "success" ? "#16a34a" : "#d97706"};
                margin-bottom: 12px;
            ">
                ${title}
            </h2>

            <p style="
                font-size: 18px;
                color: #374151;
                margin-bottom: 25px;
                font-weight: 600;
            ">
                ${message}
            </p>

            <button type="button" onclick="closeVotePopup()" style="
                background: #111827;
                color: white;
                padding: 12px 28px;
                border-radius: 12px;
                border: none;
                font-size: 16px;
                font-weight: 700;
                cursor: pointer;
            ">
                Close
            </button>
        </div>
    `;

    document.body.appendChild(overlay);

    if (duration > 0) {
        setTimeout(() => {
            closeVotePopup();
        }, duration);
    }
}


// ---------------- CLOSE POPUP ----------------

function closeVotePopup() {
    const popup = document.getElementById("votePopupOverlay");

    if (popup) {
        popup.remove();
    }
}


// ---------------- FRAUD SIREN FINAL FIX ----------------

function playFraudSiren() {
    try {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        const audioContext = new AudioContextClass();

        if (audioContext.state === "suspended") {
            audioContext.resume();
        }

        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        oscillator.type = "square";
        gainNode.gain.setValueAtTime(0.55, audioContext.currentTime);

        oscillator.start();

        let count = 0;

        const sirenInterval = setInterval(() => {
            if (count % 2 === 0) {
                oscillator.frequency.setValueAtTime(1000, audioContext.currentTime);
            } else {
                oscillator.frequency.setValueAtTime(450, audioContext.currentTime);
            }

            count++;

            if (count >= 24) {
                clearInterval(sirenInterval);
                oscillator.stop();
                audioContext.close();
            }

        }, 250);

    } catch (error) {
        console.log("Fraud siren error:", error);
    }
}
// ======================================================
// FINAL DUPLICATE VOTE POPUP FIX
// Paste this at the VERY BOTTOM of script.js
// ======================================================

console.log("FINAL DUPLICATE POPUP FIX LOADED");


// Show saved popup again if page refreshed
window.addEventListener("load", function () {
    const savedPopup = localStorage.getItem("pendingDuplicatePopup");

    if (savedPopup) {
        const popupData = JSON.parse(savedPopup);

        localStorage.removeItem("pendingDuplicatePopup");

        playFraudSiren();

        showPermanentDuplicatePopup(
            popupData.title,
            popupData.message
        );
    }
});


// Final vote function override
async function voteForCandidate(candidate_id) {
    const voterInput = document.getElementById("vote_voter_id");
    const voter_id = voterInput ? voterInput.value.trim() : "";

    if (voter_id === "") {
        showMessage("voteMessage", "Please enter Voter ID", "red");
        playErrorBeep();

        showPermanentErrorPopup(
            "Missing Voter ID",
            "Please enter your voter ID before voting."
        );

        return false;
    }

    if (votingFaceDescriptor === null) {
        showMessage("voteMessage", "Please scan your face before voting", "red");
        playErrorBeep();

        showPermanentErrorPopup(
            "Face Not Scanned",
            "Please scan your face before voting."
        );

        return false;
    }

    try {
        const response = await fetch(`${API_URL}/vote`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                voter_id: voter_id,
                candidate_id: candidate_id,
                face_descriptor: votingFaceDescriptor
            })
        });

        const data = await response.json();

        console.log("FINAL VOTE RESPONSE:", data);

        if (data.success === true) {
            showMessage("voteMessage", data.message, "green");
            playSuccessBeep();

            showPermanentSuccessPopup(
                "Congratulations!",
                "Your vote has been cast successfully and stored on blockchain."
            );

            return false;
        }

        if (data.alert === true || data.message.toLowerCase().includes("duplicate")) {
            const duplicateTitle = "Duplicate Vote Detected";
            const duplicateMessage = data.message || "This voter has already voted.";

            // Save popup so even if page refreshes, it appears again
            localStorage.setItem(
                "pendingDuplicatePopup",
                JSON.stringify({
                    title: duplicateTitle,
                    message: duplicateMessage
                })
            );

            showMessage("voteMessage", duplicateMessage, "red");
            playFraudSiren();

            showPermanentDuplicatePopup(
                duplicateTitle,
                duplicateMessage
            );

            return false;
        }

        showMessage("voteMessage", data.message, "red");
        playErrorBeep();

        showPermanentErrorPopup(
            "Voting Failed",
            data.message
        );

        return false;

    } catch (error) {
        showMessage("voteMessage", "Backend connection failed", "red");
        playErrorBeep();

        showPermanentErrorPopup(
            "Backend Error",
            "Backend connection failed."
        );

        console.log(error);

        return false;
    }
}


// Permanent duplicate popup
function showPermanentDuplicatePopup(title, message) {
    showFinalPermanentPopup(
        "fraud",
        title,
        message
    );
}


// Permanent success popup
function showPermanentSuccessPopup(title, message) {
    showFinalPermanentPopup(
        "success",
        title,
        message
    );
}


// Permanent error popup
function showPermanentErrorPopup(title, message) {
    showFinalPermanentPopup(
        "error",
        title,
        message
    );
}


// Final permanent popup maker
function showFinalPermanentPopup(type, title, message) {
    const oldPopup = document.getElementById("votePopupOverlay");

    if (oldPopup) {
        oldPopup.remove();
    }

    const overlay = document.createElement("div");
    overlay.id = "votePopupOverlay";

    overlay.style.position = "fixed";
    overlay.style.top = "0";
    overlay.style.left = "0";
    overlay.style.right = "0";
    overlay.style.bottom = "0";
    overlay.style.background = "rgba(15, 23, 42, 0.88)";
    overlay.style.display = "flex";
    overlay.style.justifyContent = "center";
    overlay.style.alignItems = "center";
    overlay.style.zIndex = "99999999";

    let icon = "!";
    let mainColor = "#d97706";
    let bgColor = "#fef3c7";

    if (type === "success") {
        icon = "✓";
        mainColor = "#16a34a";
        bgColor = "#dcfce7";
    }

    if (type === "fraud") {
        icon = "✕";
        mainColor = "#dc2626";
        bgColor = "#fee2e2";
    }

    overlay.innerHTML = `
        <div style="
            width: 460px;
            max-width: 92%;
            background: white;
            padding: 40px;
            border-radius: 26px;
            text-align: center;
            box-shadow: 0 30px 80px rgba(0, 0, 0, 0.55);
            border: 5px solid ${mainColor};
        ">
            <div style="
                width: 105px;
                height: 105px;
                margin: 0 auto 20px auto;
                border-radius: 50%;
                background: ${bgColor};
                color: ${mainColor};
                border: 5px solid ${mainColor};
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 60px;
                font-weight: 900;
            ">
                ${icon}
            </div>

            <h2 style="
                color: ${mainColor};
                font-size: 32px;
                margin-bottom: 15px;
            ">
                ${title}
            </h2>

            <p style="
                color: #111827;
                font-size: 19px;
                font-weight: 700;
                line-height: 1.5;
                margin-bottom: 28px;
            ">
                ${message}
            </p>

            <button type="button" onclick="closeVotePopup()" style="
                background: #111827;
                color: white;
                padding: 14px 32px;
                border-radius: 14px;
                border: none;
                font-size: 17px;
                font-weight: 800;
                cursor: pointer;
            ">
                Close
            </button>
        </div>
    `;

    document.body.appendChild(overlay);
}


// Close popup
function closeVotePopup() {
    const popup = document.getElementById("votePopupOverlay");

    if (popup) {
        popup.remove();
    }
}


// Fraud siren final
function playFraudSiren() {
    try {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        const audioContext = new AudioContextClass();

        if (audioContext.state === "suspended") {
            audioContext.resume();
        }

        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        oscillator.type = "square";
        gainNode.gain.setValueAtTime(0.6, audioContext.currentTime);

        oscillator.start();

        let count = 0;

        const sirenInterval = setInterval(() => {
            if (count % 2 === 0) {
                oscillator.frequency.setValueAtTime(1050, audioContext.currentTime);
            } else {
                oscillator.frequency.setValueAtTime(420, audioContext.currentTime);
            }

            count++;

            if (count >= 30) {
                clearInterval(sirenInterval);
                oscillator.stop();
                audioContext.close();
            }

        }, 250);

    } catch (error) {
        console.log("Fraud siren error:", error);
    }
}