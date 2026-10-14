const API = "/transactions";
const feedback = document.querySelector("#feedback");
const money = (value) => Number(value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const apiKeyInput = document.querySelector("#api-key");
const getApiKey = () => localStorage.getItem("api_key") || "";
apiKeyInput.value = getApiKey();
document.querySelector("#save-api-key").addEventListener("click", () => {
  const key = apiKeyInput.value.trim();
  if (key) {
    localStorage.setItem("ledgerApiKey", key);
    localStorage.setItem("api_key", key);
    notify("Chave da API salva neste navegador.");
  } else {
    localStorage.removeItem("ledgerApiKey");
    localStorage.removeItem("api_key");
    notify("Informe uma chave da API.", "error");
  }
});

function notify(message, type = "success") {
  feedback.textContent = message;
  feedback.className = `feedback ${type}`;
  if ("speechSynthesis" in window && type === "success") window.speechSynthesis.speak(new SpeechSynthesisUtterance(message));
}

async function request(url, options = {}) {
  const apiKey = getApiKey();
  const response = await fetch(url, { headers: { "Content-Type": "application/json", ...(apiKey ? { "x-api-key": apiKey } : {}), ...(options.headers || {}) }, ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Não foi possível concluir a operação.");
  return data;
}

document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => {
  document.querySelectorAll(".tab,.tab-content").forEach((element) => element.classList.remove("is-active"));
  tab.classList.add("is-active");
  document.querySelector(`[data-panel="${tab.dataset.tab}"]`).classList.add("is-active");
  if (tab.dataset.tab === "totals") loadTotals();
}));

document.querySelector("#manual-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formElement = event.currentTarget;
  const form = new FormData(formElement);
  const data = {
    title: form.get("title"),
    amount: Number(form.get("amount")),
    category: form.get("category"),
  };
  try {
    const apiKey = localStorage.getItem("api_key");
    const response = await fetch(API, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(apiKey ? { "x-api-key": apiKey } : {}),
      },
      body: JSON.stringify(data),
    });
    const transaction = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(transaction.detail || "Não foi possível salvar o gasto.");
    formElement.reset();
    notify(`Gasto de ${money(transaction.amount)} salvo em ${transaction.category}.`);
  } catch (error) { notify(error.message, "error"); }
});

async function loadTotals() {
  try {
    const data = await request(`${API}/totals`);
    document.querySelector("#grand-total").textContent = money(data.total);
    document.querySelector("#category-totals").innerHTML = data.by_category.length
      ? data.by_category.map((item) => `<div class="category-row"><span>${item.category}</span><strong>${money(item.total)}</strong></div>`).join("")
      : '<p class="muted">Nenhum gasto cadastrado.</p>';
  } catch (error) { notify(error.message, "error"); }
}
document.querySelector("#refresh-totals").addEventListener("click", loadTotals);
document.querySelector("#speak-total").addEventListener("click", () => {
  const total = document.querySelector("#grand-total").textContent;
  if ("speechSynthesis" in window) window.speechSynthesis.speak(new SpeechSynthesisUtterance(`Seu total gasto é ${total}.`));
});

const recordButton = document.querySelector("#record-button");
let recorder; let chunks = [];
recordButton.addEventListener("click", async () => {
  if (recorder?.state === "recording") return recorder.stop();
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const type = ["audio/webm", "audio/mp4", "audio/wav"].find((item) => MediaRecorder.isTypeSupported(item));
    recorder = new MediaRecorder(stream, type ? { mimeType: type } : undefined); chunks = [];
    recorder.ondataavailable = (event) => event.data.size && chunks.push(event.data);
    recorder.onstart = () => { recordButton.classList.add("is-recording"); document.querySelector("#hint").textContent = "Clique novamente para finalizar"; };
    recorder.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop()); recordButton.classList.remove("is-recording");
      document.querySelector("#hint").textContent = "Processando sua voz...";
      try {
        const mimeType = recorder.mimeType || "audio/webm";
        const extension = mimeType.includes("mp4") ? "mp4" : mimeType.includes("wav") ? "wav" : "webm";
        const audioBlob = new Blob(chunks, { type: mimeType });
        const formData = new FormData();
        formData.append("file", audioBlob, `audio.${extension}`);
        const apiKey = localStorage.getItem("api_key");
        const response = await fetch("/api/voice-transaction", {
          method: "POST",
          headers: apiKey ? { "x-api-key": apiKey } : {},
          body: formData,
        });
        const data = await response.json(); if (!response.ok) throw new Error(data.detail || "Não foi possível salvar.");
        notify(`Gasto de ${money(data.amount)} salvo em ${data.category}.`);
      } catch (error) { notify(error.message, "error"); }
      document.querySelector("#hint").textContent = "Clique para começar a gravar";
    };
    recorder.start();
  } catch { notify("É necessário permitir o acesso ao microfone.", "error"); }
});
