async function postForm(url, data){
  const fd=new FormData(); for(const [k,v] of Object.entries(data)) fd.append(k,v);
  const r=await fetch(url,{method:"POST",body:fd}); return r.json();
}
function log(t){ const el=document.getElementById("log"); const d=document.createElement("div"); d.textContent=t; el.appendChild(d); el.scrollTop=el.scrollHeight; }
async function refresh(){
  const st = await fetch("/api/state").then(r=>r.json());
  document.getElementById("loc").textContent = st.loc;
  document.getElementById("money").textContent = "€"+st.money;
  document.getElementById("turn").textContent = "T"+st.turn;
  const inv = document.getElementById("inv"); inv.innerHTML="";
  (st.inventory||[]).forEach(id=>{ const li=document.createElement("li"); li.textContent=id; inv.appendChild(li); });
}

document.getElementById("cmdform").addEventListener("submit", async (e)=>{
  e.preventDefault();
  const cmd = document.getElementById("cmd").value.trim(); if(!cmd) return;
  const res = await postForm("/api/command",{cmd});
  log("> "+cmd); log(res.output);
  if(res.tts_base64 && res.tts_base64.length > 0){ 
    log("🔊 Carregando áudio TTS...");
    const a=document.getElementById("player"); 
    a.onloadeddata = () => {
      log("▶️ Reproduzindo áudio...");
      a.play().catch(e => log("⚠️ Erro ao reproduzir áudio: "+e.message));
    };
    a.onerror = (e) => {
      log("❌ Erro ao carregar áudio TTS. Tentando formato alternativo...");
      // Tentar formato alternativo
      a.src="data:audio/mpeg;base64,"+res.tts_base64;
      a.load();
    };
    a.oncanplay = () => {
      log("✅ Áudio pronto para reprodução");
    };
    a.src="data:audio/mp3;base64,"+res.tts_base64; 
    a.load();
  } else {
    log("⚠️ Nenhum áudio TTS recebido");
  }
  document.getElementById("cmd").value=""; refresh();
});

document.getElementById("btn-state").addEventListener("click", refresh);

// Voice
let rec; let chunks=[];
document.getElementById("rec").addEventListener("click", async ()=>{
  if(!rec||rec.state==="inactive"){
    try {
      const s = await navigator.mediaDevices.getUserMedia({audio:true});
      // Tentar usar codec opus se disponível, senão usar o padrão
      const options = {mimeType: 'audio/webm;codecs=opus'};
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options.mimeType = 'audio/webm';
      }
      rec = new MediaRecorder(s, options);
      chunks=[];
      rec.ondataavailable=e=>{
        if(e.data && e.data.size > 0) {
          chunks.push(e.data);
        }
      };
      rec.onstop=async ()=>{
      const blob=new Blob(chunks,{type:"audio/webm"});
      const sizeKB = (blob.size / 1024).toFixed(2);
      log(`📤 Enviando áudio (${sizeKB} KB)...`);
      if(blob.size < 1000) {
        log("⚠️ Áudio muito pequeno. Certifique-se de que está falando e que o microfone está funcionando.");
        return;
      }
      const fd=new FormData(); fd.append("file",blob,"rec.webm");
      log("⏳ Processando transcrição (pode demorar alguns segundos na primeira vez)...");
      try {
        const response = await fetch("/api/stt",{method:"POST",body:fd});
        if(!response.ok) {
          log(`❌ Erro HTTP ${response.status}: ${response.statusText}`);
          return;
        }
        const r = await response.json();
        if(r.error) {
          log("❌ Erro STT: "+r.error);
        } else if(r.text && r.text.trim()) {
          log("🎧 "+r.text);
          document.getElementById("cmd").value=r.text;
        } else {
          log("⚠️ Nenhum texto transcrito. Tente falar mais alto ou verifique o microfone.");
        }
      } catch(e) {
        if(e.message.includes("Failed to fetch") || e.message.includes("ERR_CONNECTION_REFUSED")) {
          log("❌ Servidor não está rodando. Por favor, inicie o servidor com: python -m app.main");
        } else {
          log("❌ Erro ao enviar áudio: "+e.message);
        }
      }
      };
      rec.start(); document.getElementById("rec").textContent="🛑 Parar";
    } catch(e) {
      log("❌ Erro ao iniciar gravação: "+e.message);
    }
  }else{ 
    rec.stop(); 
    document.getElementById("rec").textContent="🎙️ Falar"; 
  }
});

// LLM
document.getElementById("llmform").addEventListener("submit", async (e)=>{
  e.preventDefault();
  const prompt = document.getElementById("prompt").value.trim(); if(!prompt) return;
  const provider = document.getElementById("prov").value;
  const res = await postForm("/api/llm",{prompt,provider});
  log("🤖 "+res.text);
  if(res.tts_base64 && res.tts_base64.length > 0){ 
    log("🔊 Carregando áudio TTS...");
    const a=document.getElementById("player"); 
    a.onloadeddata = () => {
      log("▶️ Reproduzindo áudio...");
      a.play().catch(e => log("⚠️ Erro ao reproduzir áudio: "+e.message));
    };
    a.onerror = (e) => {
      log("❌ Erro ao carregar áudio TTS. Tentando formato alternativo...");
      a.src="data:audio/mpeg;base64,"+res.tts_base64;
      a.load();
    };
    a.oncanplay = () => {
      log("✅ Áudio pronto para reprodução");
    };
    a.src="data:audio/mp3;base64,"+res.tts_base64; 
    a.load();
  } else {
    log("⚠️ Nenhum áudio TTS recebido");
  }
});

// Boot
refresh();
log("Demo pronta. Tenta: 'examinar praia' → 'este' → 'falar' → 'sul' 'examinar' → 'norte' 'norte' 'examinar' → 'oeste' 'usar corda' 'usar lanterna' → 'oeste' 'abrir baú'.");
