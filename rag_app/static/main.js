const messages = document.getElementById('messages');
const input = document.getElementById('input');
const send = document.getElementById('send');
const fileinput = document.getElementById('fileinput');
const upload = document.getElementById('upload');

function addMessage(who, text) {
  const d = document.createElement('div');
  d.className = 'msg ' + (who === 'user' ? 'user' : 'bot');
  d.textContent = (who === 'user' ? 'You: ' : 'Assistant: ') + text;
  messages.appendChild(d);
  messages.scrollTop = messages.scrollHeight;
}

send.addEventListener('click', async () => {
  const txt = input.value.trim();
  if (!txt) return;
  addMessage('user', txt);
  input.value = '';

  try {
    const resp = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: txt, top_k: 5 })
    });
    const data = await resp.json();
    if (data.answer) addMessage('bot', data.answer);
    else if (data.context) addMessage('bot', 'Retrieved context:\n' + data.context.slice(0, 200));
    else addMessage('bot', JSON.stringify(data));
    if (data.retrieved) {
      data.retrieved.forEach(r => {
        const el = document.createElement('div');
        el.style.fontSize = '0.9em';
        el.style.color = '#555';
        el.textContent = `Source: ${r.metadata.source || r.id} - score: ${r.score.toFixed(3)}`;
        messages.appendChild(el);
      });
    }
  } catch (e) {
    addMessage('bot', 'Error: ' + e.message);
  }
});

upload.addEventListener('click', async () => {
  const files = fileinput.files;
  if (!files || files.length === 0) return;
  addMessage('user', `Uploading ${files.length} file(s)...`);
  const fd = new FormData();
  for (let i = 0; i < files.length; i++) fd.append('files', files[i]);

  try {
    const resp = await fetch('/upload', { method: 'POST', body: fd });
    const data = await resp.json();
    if (resp.ok) {
      addMessage('bot', `Uploaded ${data.count} files: ${data.stored.join(', ')}`);
    } else {
      addMessage('bot', `Upload failed: ${data.detail || JSON.stringify(data)}`);
    }
  } catch (e) {
    addMessage('bot', 'Upload error: ' + e.message);
  }
});
