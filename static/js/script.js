   
    function formattaRicettaHTML(rawText) {
  // 1. Rimuove <p> iniziale e finale, se presenti
  const cleanText = rawText.replace(/^<p>/, '').replace(/<\/p>$/, '').trim();

  // 2. Divide in righe
  const righe = cleanText.split('\\n');

  let html = '';
  let dentroLista = false;

  righe.forEach((riga) => {
    const trimmed = riga.trim();

    if (trimmed === '') {
      if (dentroLista) {
        html += '</ul>';
        dentroLista = false;
      }
      html += '<br>';
    } else if (/^\d+\.\s*/.test(trimmed)) {
      // Esempio: "1. Titolo"
      if (dentroLista) {
        html += '</ul>';
        dentroLista = false;
      }
      html += `<h3>${trimmed}</h3>`;
    } else if (trimmed.startsWith('- ')) {
      if (!dentroLista) {
        html += '<ul>';
        dentroLista = true;
      }
      html += `<li>${trimmed.substring(2)}</li>`;
    } else {
      html += `<p>${trimmed}</p>`;
    }
  });

  if (dentroLista) html += '</ul>';
  return html;
}
    
    const sendBtn = document.getElementById("send-btn");
    const userInput = document.getElementById("user-input");
    const chatContainer = document.getElementById("chat-container");

    sendBtn.addEventListener("click", () => {
      const message = userInput.value.trim();
      if (!message) return;

      const ragEnabled = document.getElementById("rag-toggle").checked;
      const guardrailsEnabled = document.getElementById("guardrails-toggle").checked;

      // Mostra messaggio utente
      const userDiv = document.createElement("div");
      userDiv.className = "message user";
      userDiv.textContent = message;
      chatContainer.appendChild(userDiv);
      chatContainer.scrollTop = chatContainer.scrollHeight;

      // Svuota input
      userInput.value = "";
      //console.log("RAG attivo:", document.getElementById("rag-toggle").checked);

      // Chiamata al backend
      fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          message: message,
          rag: ragEnabled,
          guardrails: guardrailsEnabled
        })
      })  
      .then(res => res.json())
      .then(data => {
        const botDiv = document.createElement("div");
        botDiv.className = "message bot";
        botDiv.innerHTML = formattaRicettaHTML(data.reply);

        // Cambia grafica in base ai guardrails
        if (guardrailsEnabled) {
          botDiv.style.border = "2px solid red";
        }

        chatContainer.appendChild(botDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
      });
    });

    document.addEventListener("DOMContentLoaded", () => {
      document.getElementById("user-input").addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          event.preventDefault(); // evita eventuale invio form
          document.getElementById("send-btn").click(); // simula click sul bottone
        }
      });

      const uploadForm = document.getElementById("upload-form");
      const uploadInput = document.getElementById("upload-input");

      uploadForm.addEventListener("submit", async (e) => {
        e.preventDefault(); // ✅ BLOCCA IL SUBMIT TRADIZIONALE

        const file = uploadInput.files[0];
        if (!file) return alert("Seleziona un file .txt");

        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch("/upload", {
          method: "POST",
          body: formData
        });

        const data = await response.json();
        if (data.error) {
          alert(data.error);
          return;
        }

        console.log("File salvato, contenuto:", data.content);

        // Visualizza messaggio nella chat
        const botDiv = document.createElement("div");
        botDiv.className = "message bot";
        botDiv.textContent = "File caricato correttamente!";
        chatContainer.appendChild(botDiv);
      });
    });

