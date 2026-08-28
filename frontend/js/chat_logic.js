/**
 * Nexus MCP Chat - Frontend Client Logic
 * Handles asynchronous API communication, state management,
 * Markdown parsing, MCP tool visualization, and DOM updates.
 */

// Configuration & State
const API_BASE = window.location.origin.includes('http') && !window.location.origin.includes('null') 
  ? window.location.origin 
  : 'http://127.0.0.1:8000';

let chatHistory = [];
let isProcessing = false;

// DOM Elements
const chatContainer = document.getElementById('chatContainer');
const messagesList = document.getElementById('messagesList');
const welcomeHero = document.getElementById('welcomeHero');
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');
const btnSend = document.getElementById('btnSend');
const btnClearChat = document.getElementById('btnClearChat');
const loadingIndicator = document.getElementById('loadingIndicator');
const loadingStageText = document.getElementById('loadingStageText');
const statusDot = document.getElementById('statusDot');
const statusPing = document.getElementById('statusPing');
const statusText = document.getElementById('statusText');
const btnToolsModal = document.getElementById('btnToolsModal');
const toolsModal = document.getElementById('toolsModal');
const btnCloseToolsModal = document.getElementById('btnCloseToolsModal');
const btnCloseToolsModalBottom = document.getElementById('btnCloseToolsModalBottom');
const toolsListContainer = document.getElementById('toolsListContainer');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  checkBackendHealth();
});

function setupEventListeners() {
  // Input Auto-Resize & State Check
  messageInput.addEventListener('input', () => {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 144) + 'px';
    btnSend.disabled = !messageInput.value.trim() || isProcessing;
  });

  // Keyboard Shortcuts (Enter to Send, Shift+Enter for Newline)
  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!btnSend.disabled) {
        chatForm.dispatchEvent(new Event('submit'));
      }
    }
  });

  // Form Submit
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = messageInput.value.trim();
    if (!text || isProcessing) return;
    await sendMessage(text);
  });

  // Suggestion Chips
  document.querySelectorAll('.suggestion-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (prompt) {
        messageInput.value = prompt;
        messageInput.dispatchEvent(new Event('input'));
        sendMessage(prompt);
      }
    });
  });

  // Clear Chat History
  btnClearChat.addEventListener('click', () => {
    if (confirm('Clear entire conversation history?')) {
      chatHistory = [];
      messagesList.innerHTML = '';
      welcomeHero.classList.remove('hidden');
      scrollToBottom();
    }
  });

  // Tools Modal Open/Close
  btnToolsModal.addEventListener('click', openToolsModal);
  btnCloseToolsModal.addEventListener('click', () => toolsModal.classList.add('hidden'));
  btnCloseToolsModalBottom.addEventListener('click', () => toolsModal.classList.add('hidden'));
  toolsModal.addEventListener('click', (e) => {
    if (e.target === toolsModal) toolsModal.classList.add('hidden');
  });
}

/**
 * Health check & diagnostic status polling
 */
async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (res.ok) {
      const data = await res.json();
      statusDot.className = 'relative inline-flex rounded-full h-2 w-2 bg-emerald-500';
      statusPing.className = 'animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75';
      statusText.textContent = data.mcp_server === 'connected' ? 'MCP Online' : 'MCP Fallback';
      statusText.title = `Model: ${data.llm_model} | Tools: ${data.available_tools_count}`;
    } else {
      setOfflineStatus();
    }
  } catch (err) {
    setOfflineStatus();
  }
}

function setOfflineStatus() {
  statusDot.className = 'relative inline-flex rounded-full h-2 w-2 bg-rose-500';
  statusPing.className = 'hidden';
  statusText.textContent = 'Server Offline';
}

/**
 * Send user message to FastAPI backend
 */
async function sendMessage(text) {
  if (isProcessing) return;
  isProcessing = true;
  btnSend.disabled = true;

  // Hide welcome hero on first message
  if (!welcomeHero.classList.contains('hidden')) {
    welcomeHero.classList.add('hidden');
  }

  // Clear input
  messageInput.value = '';
  messageInput.style.height = 'auto';

  // Append user message to UI
  appendUserMessage(text);
  scrollToBottom();

  // Show loading indicator
  loadingIndicator.classList.remove('hidden');
  loadingStageText.textContent = 'Querying LLM & executing MCP tools...';
  scrollToBottom();

  try {
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        history: chatHistory
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    // Update history
    chatHistory.push({ role: 'user', content: text });
    chatHistory.push({ role: 'assistant', content: data.response });

    // Render assistant message
    appendAssistantMessage(data);

  } catch (error) {
    console.error('Chat error:', error);
    appendAssistantMessage({
      response: `**Error communicating with backend:** ${error.message}\n\nPlease verify that the FastAPI backend is running on \`${API_BASE}\`.`,
      tool_calls: [],
      status: 'error'
    });
  } finally {
    loadingIndicator.classList.add('hidden');
    isProcessing = false;
    messageInput.focus();
    scrollToBottom();
  }
}

/**
 * Append user message bubble to DOM
 */
function appendUserMessage(text) {
  const msgEl = document.createElement('div');
  msgEl.className = 'flex justify-end items-start gap-3 animate-fade-in';
  
  const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  msgEl.innerHTML = `
    <div class="flex flex-col items-end max-w-[85%] sm:max-w-[75%] space-y-1">
      <div class="user-bubble text-white px-4 py-3 rounded-2xl rounded-tr-sm text-sm sm:text-base leading-relaxed break-words shadow-md">
        ${escapeHtml(text)}
      </div>
      <span class="text-[10px] text-slate-500 pr-1">${timeStr}</span>
    </div>
    <div class="h-8 w-8 rounded-xl bg-gradient-to-tr from-slate-700 to-slate-600 flex items-center justify-center text-slate-200 text-xs font-bold flex-shrink-0 shadow">
      You
    </div>
  `;

  messagesList.appendChild(msgEl);
}

/**
 * Append assistant message card to DOM with MCP tool call badges
 */
function appendAssistantMessage(data) {
  const msgEl = document.createElement('div');
  msgEl.className = 'flex items-start gap-3 animate-fade-in';
  
  const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const modelName = data.model || 'Nexus Assistant';
  const hasTools = data.tool_calls && data.tool_calls.length > 0;

  // Build Tool Calls UI Block if present
  let toolsHtml = '';
  if (hasTools) {
    toolsHtml = `
      <div class="space-y-2 mb-3">
        <div class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
          <svg class="w-3.5 h-3.5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Model Context Protocol Tools Invoked (${data.tool_calls.length})
        </div>
        <div class="space-y-2">
          ${data.tool_calls.map(tool => `
            <div class="tool-card rounded-xl p-3 text-xs">
              <div class="flex items-center justify-between font-mono font-medium text-indigo-300 mb-1">
                <span class="flex items-center gap-1.5">
                  <span class="w-1.5 h-1.5 rounded-full ${tool.status === 'success' ? 'bg-emerald-400' : 'bg-amber-400'}"></span>
                  tool::${tool.name}()
                </span>
                <span class="text-[10px] px-1.5 py-0.5 rounded ${tool.status === 'success' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'}">
                  ${tool.status.toUpperCase()}
                </span>
              </div>
              ${tool.arguments && Object.keys(tool.arguments).length > 0 ? `
                <div class="text-[11px] text-slate-400 font-mono mt-1 bg-slate-950/60 p-2 rounded border border-slate-800/80">
                  <span class="text-slate-500">args:</span> ${escapeHtml(JSON.stringify(tool.arguments))}
                </div>
              ` : ''}
              ${tool.output ? `
                <div class="text-[11px] text-slate-300 mt-1.5 bg-slate-950/80 p-2 rounded border border-slate-800 font-mono">
                  <span class="text-slate-500">result:</span> ${escapeHtml(tool.output)}
                </div>
              ` : ''}
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // Parse Markdown for response body
  const parsedMarkdown = typeof marked !== 'undefined' 
    ? marked.parse(data.response || '') 
    : `<p>${escapeHtml(data.response || '')}</p>`;

  msgEl.innerHTML = `
    <div class="h-8 w-8 rounded-xl bg-gradient-to-tr from-indigo-600 via-violet-600 to-cyan-400 p-0.5 flex-shrink-0 shadow-md shadow-indigo-500/20">
      <div class="h-full w-full bg-slate-950 rounded-[10px] flex items-center justify-center text-indigo-400">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      </div>
    </div>
    <div class="flex flex-col items-start max-w-[90%] sm:max-w-[85%] space-y-1">
      <div class="assistant-bubble text-slate-100 px-4 py-3.5 rounded-2xl rounded-tl-sm text-sm sm:text-base leading-relaxed shadow-lg w-full">
        <div class="flex items-center justify-between text-xs text-slate-400 mb-2 border-b border-slate-800/80 pb-1.5">
          <span class="font-medium text-slate-300">${modelName}</span>
          ${data.latency_seconds ? `<span class="font-mono text-[10px] text-slate-500">${data.latency_seconds}s</span>` : ''}
        </div>
        ${toolsHtml}
        <div class="prose-custom">
          ${parsedMarkdown}
        </div>
      </div>
      <span class="text-[10px] text-slate-500 pl-1">${timeStr}</span>
    </div>
  `;

  messagesList.appendChild(msgEl);
}

/**
 * Open Tools Modal & Populate registered tools
 */
async function openToolsModal() {
  toolsModal.classList.remove('hidden');
  toolsListContainer.innerHTML = '<div class="text-xs text-slate-400 p-4 text-center">Loading registered MCP tools...</div>';
  
  try {
    const res = await fetch(`${API_BASE}/api/tools`);
    if (res.ok) {
      const data = await res.json();
      if (data.tools && data.tools.length > 0) {
        toolsListContainer.innerHTML = data.tools.map(tool => `
          <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-3">
            <div class="flex items-center justify-between mb-1">
              <span class="font-mono font-semibold text-indigo-300 text-xs">${tool.name}</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono">MCP Tool</span>
            </div>
            <p class="text-slate-400 text-xs">${tool.description || 'No description provided.'}</p>
            ${tool.parameters && tool.parameters.properties && Object.keys(tool.parameters.properties).length > 0 ? `
              <div class="mt-2 text-[10px] text-slate-500 font-mono bg-slate-900/90 p-1.5 rounded">
                Params: ${Object.keys(tool.parameters.properties).join(', ')}
              </div>
            ` : ''}
          </div>
        `).join('');
      } else {
        toolsListContainer.innerHTML = '<div class="text-xs text-slate-400 p-4 text-center">No tools registered.</div>';
      }
    }
  } catch (e) {
    toolsListContainer.innerHTML = `<div class="text-xs text-rose-400 p-4 text-center">Failed to query tools: ${e.message}</div>`;
  }
}

function scrollToBottom() {
  setTimeout(() => {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }, 50);
}

function escapeHtml(str) {
  if (typeof str !== 'string') return String(str);
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
