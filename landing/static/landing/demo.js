(function () {
    "use strict";

    var MAX_RECORD_MS = 20000; // ~20 soniyadan keyin avtomatik to'xtaydi

    function getCookie(name) {
        var match = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
        return match ? decodeURIComponent(match.pop()) : "";
    }

    function initDemo() {
        var micBtn = document.querySelector("[data-demo-mic]");
        var statusEl = document.querySelector("[data-demo-status]");
        var chatPanel = document.querySelector("[data-demo-chat]");
        var chatMessages = document.querySelector("[data-demo-messages]");
        var chatForm = document.querySelector("[data-demo-form]");
        var chatInput = document.querySelector("[data-demo-input]");
        if (!micBtn) return;

        var history = [];
        var mediaRecorder = null;
        var chunks = [];
        var isRecording = false;
        var autoStopTimer = null;
        var csrftoken = getCookie("csrftoken");

        function setStatus(text) {
            if (statusEl) statusEl.textContent = text;
        }

        function addMessage(role, text) {
            var bubble = document.createElement("div");
            bubble.className = "demo-msg demo-msg-" + role;
            bubble.textContent = text;
            chatMessages.appendChild(bubble);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            return bubble;
        }

        function showTyping() {
            var bubble = document.createElement("div");
            bubble.className = "demo-msg demo-msg-assistant demo-typing";
            bubble.setAttribute("data-demo-typing", "");
            bubble.innerHTML = "<span></span><span></span><span></span>";
            chatMessages.appendChild(bubble);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function hideTyping() {
            var bubble = chatMessages.querySelector("[data-demo-typing]");
            if (bubble) bubble.remove();
        }

        function openChat() {
            if (chatPanel) chatPanel.style.display = "flex";
        }

        async function sendAudio(blob) {
            setStatus("AI yozmoqda...");
            openChat();
            showTyping();
            var formData = new FormData();
            formData.append("audio", blob, "demo.webm");
            try {
                var resp = await fetch("/demo/voice/", {
                    method: "POST",
                    headers: { "X-CSRFToken": csrftoken },
                    body: formData,
                });
                var data = await resp.json();
                hideTyping();
                if (!resp.ok) {
                    setStatus(data.error || "Xatolik yuz berdi.");
                    return;
                }
                addMessage("user", data.question);
                addMessage("assistant", data.answer);
                history.push({ role: "user", content: data.question });
                history.push({ role: "assistant", content: data.answer });
                setStatus("Yozib gapiring yoki pastda yozing.");
            } catch (e) {
                hideTyping();
                setStatus("Tarmoq xatoligi. Qaytadan urinib ko'ring.");
            }
        }

        async function sendChatMessage(text) {
            var sendBtn = document.querySelector("[data-demo-send]");
            addMessage("user", text);
            history.push({ role: "user", content: text });
            if (sendBtn) sendBtn.disabled = true;
            if (chatInput) chatInput.disabled = true;
            showTyping();
            try {
                var resp = await fetch("/demo/chat/", {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                    body: JSON.stringify({ message: text, history: history }),
                });
                var data = await resp.json();
                hideTyping();
                if (!resp.ok) {
                    addMessage("assistant", data.error || "Xatolik yuz berdi.");
                    return;
                }
                addMessage("assistant", data.answer);
                history.push({ role: "assistant", content: data.answer });
            } catch (e) {
                hideTyping();
                addMessage("assistant", "Tarmoq xatoligi. Qaytadan urinib ko'ring.");
            } finally {
                if (sendBtn) sendBtn.disabled = false;
                if (chatInput) { chatInput.disabled = false; chatInput.focus(); }
            }
        }

        function stopRecording() {
            if (mediaRecorder && isRecording) {
                mediaRecorder.stop();
            }
            if (autoStopTimer) {
                clearTimeout(autoStopTimer);
                autoStopTimer = null;
            }
        }

        async function startRecording() {
            if (!navigator.mediaDevices || !window.MediaRecorder) {
                setStatus("Brauzeringiz ovoz yozishni qo'llab-quvvatlamaydi.");
                return;
            }
            try {
                var stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                chunks = [];
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = function (e) {
                    if (e.data.size > 0) chunks.push(e.data);
                };
                mediaRecorder.onstop = function () {
                    isRecording = false;
                    micBtn.classList.remove("recording");
                    stream.getTracks().forEach(function (t) { t.stop(); });
                    var blob = new Blob(chunks, { type: "audio/webm" });
                    sendAudio(blob);
                };
                mediaRecorder.start();
                isRecording = true;
                micBtn.classList.add("recording");
                setStatus("Tinglayapman... (yana bosing to'xtatish uchun)");
                autoStopTimer = setTimeout(stopRecording, MAX_RECORD_MS);
            } catch (e) {
                setStatus("Mikrofonga ruxsat berilmadi.");
            }
        }

        micBtn.addEventListener("click", function () {
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        });

        if (chatForm) {
            chatForm.addEventListener("submit", function (e) {
                e.preventDefault();
                var text = (chatInput.value || "").trim();
                if (!text) return;
                chatInput.value = "";
                sendChatMessage(text);
            });
        }
    }

    document.addEventListener("DOMContentLoaded", initDemo);
})();
