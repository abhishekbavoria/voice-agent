let mediaRecorder;
let ws;
let isRecording = false;

const recordBtn = document.getElementById("record-btn");
const stopAgentBtn = document.getElementById("stop-agent-btn");
const statusEl = document.getElementById("status");

// Toggle recording
recordBtn.addEventListener("click", async () => {
    if (isRecording) {
        stopRecording();
        recordBtn.innerHTML = '<i class="fa-solid fa-microphone"></i> Start Recording';
    } else {
        startWebSocketAndRecording();
        recordBtn.innerHTML = '<i class="fa-solid fa-stop"></i> Stop Recording';
        stopAgentBtn.style.display = "inline-block";
    }
});

// Stop Agent button
stopAgentBtn.addEventListener("click", () => {
    stopRecording();
    stopAgentBtn.style.display = "none";
    recordBtn.classList.remove("recording");
    recordBtn.innerHTML = '<i class="fa-solid fa-microphone"></i> Start Recording';
    statusEl.textContent = "Stopped";
});

function startWebSocketAndRecording() {
    ws = new WebSocket("ws://localhost:8000/ws/audio");

    ws.binaryType = "arraybuffer";

    ws.onopen = async () => {
        statusEl.textContent = "Recording...";
        startRecording();
    };

    ws.onclose = () => {
        statusEl.textContent = "Stopped";
        isRecording = false;
    };

    ws.onerror = (err) => {
        statusEl.textContent = "WebSocket Error";
        console.error("WebSocket error:", err);
        stopRecording();
    };
}

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = event => {
            if (event.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
                event.data.arrayBuffer().then(buffer => {
                    ws.send(buffer); // Send chunk to server
                });
            }
        };

        mediaRecorder.onstop = () => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.close();
            }
            statusEl.textContent = "Stopped";
        };

        mediaRecorder.start(300); // Emit dataavailable every 300ms
        isRecording = true;
        recordBtn.classList.add("recording");
        statusEl.textContent = "Recording...";
    }).catch(err => {
        console.error("Microphone access error:", err);
        alert("Please allow microphone access to use the voice agent.");
        statusEl.textContent = "Mic Error";
    });
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
        isRecording = false;
        recordBtn.classList.remove("recording");
        statusEl.textContent = "Processing...";
    }
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
    }
}
