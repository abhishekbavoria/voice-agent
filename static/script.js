// Text to Speech: Static Input
async function generateAudio() {
    const text = document.getElementById("text-input").value;

    const response = await fetch("/generate-audio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
    });

    if (!response.ok) {
        alert("Something went wrong while generating audio.");
        return;
    }

    const data = await response.json();
    const audioPlayer = document.getElementById("audio-player");
    audioPlayer.src = data.audio_url;
    audioPlayer.style.display = "block";
    audioPlayer.play();
}

let mediaRecorder;
let audioChunks = [];

const startBtn = document.getElementById("start-record-btn");
const stopBtn = document.getElementById("stop-record-btn");
const stopBotBtn = document.getElementById("stop-bot-btn");
const echoAudio = document.getElementById("echo-audio");

let sessionId = getOrCreateSessionId();
let botActive = true;

function getOrCreateSessionId() {
    const urlParams = new URLSearchParams(window.location.search);
    let id = urlParams.get("session_id");

    if (!id) {
        id = Math.random().toString(36).substring(2, 12); // generate a random session id
        urlParams.set("session_id", id);
        window.history.replaceState({}, "", `${location.pathname}?${urlParams}`);
    }

    return id;
}

startBtn.addEventListener("click", async () => {
    botActive = true;
    stopBotBtn.style.display = "inline-block";

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            const formData = new FormData();
            formData.append("file", audioBlob, "user_input.webm");
        
            const status = document.getElementById("upload-status");
            const transcriptBox = document.getElementById("transcription");
        
            status.textContent = "Thinking...";
            transcriptBox.textContent = "";
        
            try {
                const response = await fetch(`/agent/chat/${sessionId}`, {
                    method: "POST",
                    body: formData
                });
        
                const result = await response.json();
        
                if (response.ok && !result.error) {
                    status.textContent = "Done!";
                    transcriptBox.textContent = `You said: ${result.transcript}\nAI replied: ${result.llm_response}`;
        
                    echoAudio.src = result.audio_url;
                    echoAudio.style.display = "block";
                    echoAudio.play();
        
                    echoAudio.onended = () => {
                        if (botActive) {
                            startBtn.click(); // restart recording
                        }
                    };
                } else {
                    // On error, fallback
                    status.textContent = "Error from server. Playing fallback response.";
                    transcriptBox.textContent = result.detail || result.error || "Unknown error";
        
                    echoAudio.src = "/static/fallback.mp3";
                    echoAudio.style.display = "block";
                    echoAudio.play();
        
                    botActive = false;
                    stopBotBtn.style.display = "none";
                }
            } catch (err) {
                console.error("LLM pipeline error:", err);
                status.textContent = "Failed to get response. Playing fallback response.";
                transcriptBox.textContent = "Network or processing error.";
        
                echoAudio.src = "/static/fallback.mp3";
                echoAudio.style.display = "block";
                echoAudio.play();
        
                botActive = false;
                stopBotBtn.style.display = "none";
            }
        };        

        mediaRecorder.start();
        startBtn.disabled = true;
        stopBtn.disabled = false;
    } catch (err) {
        console.error("Microphone access error:", err);
        alert("Please allow microphone access to use the Echo Bot.");
    }
});

stopBtn.addEventListener("click", () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
        startBtn.disabled = false;
        stopBtn.disabled = true;
    }
});

stopBotBtn.addEventListener("click", () => {
    botActive = false;
    stopBotBtn.style.display = "none";
    startBtn.disabled = false;
    stopBtn.disabled = true;
});
