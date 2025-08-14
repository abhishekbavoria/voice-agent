let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let botActive = true;
let sessionId = getOrCreateSessionId();

const recordBtn = document.getElementById("record-btn");
const stopAgentBtn = document.getElementById("stop-agent-btn");
const statusEl = document.getElementById("status");
const echoAudio = document.getElementById("echo-audio");

function getOrCreateSessionId() {
    const urlParams = new URLSearchParams(window.location.search);
    let id = urlParams.get("session_id");

    if (!id) {
        id = Math.random().toString(36).substring(2, 12);
        urlParams.set("session_id", id);
        window.history.replaceState({}, "", `${location.pathname}?${urlParams}`);
    }
    return id;
}

// Toggle recording
recordBtn.addEventListener("click", async () => {
    if (isRecording) {
        stopRecording();
        recordBtn.innerHTML = '<i class="fa-solid fa-microphone"></i> Start Recording';
    } else {
        startRecording();
        recordBtn.innerHTML = '<i class="fa-solid fa-stop"></i> Stop Recording';
        botActive = true;
        stopAgentBtn.style.display = "inline-block"; // Show stop agent button
    }
});

// Stop Agent button
stopAgentBtn.addEventListener("click", () => {
    botActive = false; // Prevent auto-restarts
    isRecording = false;
    stopAgentBtn.style.display = "none";
    recordBtn.classList.remove("recording");
    recordBtn.innerHTML = '<i class="fa-solid fa-microphone"></i> Start Recording';
    statusEl.textContent = "Stopped";
});

async function startRecording() {
    botActive = true;
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            const formData = new FormData();
            formData.append("file", audioBlob, "user_input.webm");

            statusEl.textContent = "Thinking...";

            try {
                const response = await fetch(`/agent/chat/${sessionId}`, {
                    method: "POST",
                    body: formData
                });

                const result = await response.json();

                if (response.ok && !result.error) {
                    statusEl.textContent = "Speaking...";
                    echoAudio.src = result.audio_url;
                    echoAudio.play();

                    echoAudio.onended = () => {
                        statusEl.textContent = "Idle";
                        if (botActive) {
                            startRecording(); // Continue conversation loop
                            recordBtn.innerHTML = '<i class="fa-solid fa-stop"></i> Stop Recording';
                            recordBtn.classList.add("recording");
                        }
                    };                    
                } else {
                    statusEl.textContent = "Error";
                    echoAudio.src = "/static/fallback.mp3";
                    echoAudio.play();
                    botActive = false;
                    stopAgentBtn.style.display = "none";
                }
            } catch (err) {
                console.error("LLM pipeline error:", err);
                statusEl.textContent = "Network/Processing error.";
                echoAudio.src = "/static/fallback.mp3";
                echoAudio.play();
                botActive = false;
                stopAgentBtn.style.display = "none";
            }
        };

        mediaRecorder.start();
        isRecording = true;
        recordBtn.classList.add("recording");
        statusEl.textContent = "Recording...";
    } catch (err) {
        console.error("Microphone access error:", err);
        alert("Please allow microphone access to use the voice agent.");
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
        isRecording = false;
        recordBtn.classList.remove("recording");
        statusEl.textContent = "Processing...";
    }
}
