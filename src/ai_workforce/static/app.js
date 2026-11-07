const state = { selected: new URLSearchParams(window.location.search).get('run'), poll: null };
const $ = (selector) => document.querySelector(selector);

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || `Request failed (${response.status})`); }
  return response.json();
}

function toast(message) {
  const node = $('#toast'); node.textContent = message; node.classList.add('show');
  window.setTimeout(() => node.classList.remove('show'), 2600);
}

function esc(value) {
  return String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function parseSources(value) {
  return value.split('\n').map(line => line.trim()).filter(Boolean).map((line, index) => {
    const separator = line.indexOf('|');
    if (separator < 0) return { title: `Source ${index + 1}`, content: line };
    return { title: line.slice(0, separator).trim(), content: line.slice(separator + 1).trim() };
  });
}

async function loadMetrics() {
  const metric = await api('/api/metrics');
  $('#metric-runs').textContent = metric.total_runs;
  $('#metric-success').textContent = `${Math.round(metric.success_rate * 100)}%`;
  $('#metric-lessons').textContent = metric.lessons_learned;
}

async function loadRuns() {
  const runs = await api('/api/runs');
  const container = $('#runs');
  if (!runs.length) { container.innerHTML = '<p class="empty">No runs yet. Delegate an outcome above.</p>'; return; }
  container.innerHTML = runs.map(run => `
    <article class="run-card ${run.id === state.selected ? 'active' : ''}" data-id="${esc(run.id)}">
      <time>${new Date(run.created_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</time>
      <strong>${esc(run.objective)}</strong>
      <span class="badge ${esc(run.status)}">${esc(run.status.replace('_',' '))}</span>
    </article>`).join('');
  container.querySelectorAll('.run-card').forEach(card => card.addEventListener('click', () => selectRun(card.dataset.id)));
}

async function selectRun(id) {
  state.selected = id;
  window.history.replaceState(null, '', `?run=${encodeURIComponent(id)}`);
  await loadRuns();
  const run = await api(`/api/runs/${id}`);
  renderDetail(run);
  const transient = ['queued','running'].includes(run.status);
  if (transient) schedulePoll(); else clearTimeout(state.poll);
}

function renderDetail(run) {
  const waiting = run.plan.find(step => step.status === 'waiting_approval');
  const plan = run.plan.map((step, index) => `
    <div class="step ${esc(step.status)}">
      <span class="step-dot">${step.status === 'completed' ? '✓' : index + 1}</span>
      <div><h4>${esc(step.title)}</h4><p>${esc(step.agent)} · ${esc(step.tool)} · ${esc(step.risk)} risk${Object.keys(step.arguments || {}).length ? ` · ${esc(JSON.stringify(step.arguments))}` : ''}</p></div>
    </div>`).join('');
  const approval = waiting ? `<div class="approval"><p><strong>Human decision required.</strong><br>This step creates an external-facing artifact in the simulated outbox.</p><button data-approve="true">Approve & continue</button><button class="reject" data-approve="false">Reject</button></div>` : '';
  const calculation = run.result?.artifacts?.find(item => Object.hasOwn(item, 'value'));
  const research = run.result?.artifacts?.find(item => item.findings);
  const message = run.result?.artifacts?.find(item => item.message);
  const evidence = research?.findings?.map((item, index) => `<li><b>${esc(item.id || `S${index + 1}`)}</b> ${esc(item.title)}</li>`).join('') || '';
  const execution = run.result?.execution;
  const result = run.result ? `<div class="result">
    <div class="result-head"><h4>Verified run result</h4><strong>${Math.round(run.result.review.quality_score * 100)}% grounding score</strong></div>
    <div class="result-grid">
      <div><small>EVIDENCE</small><b>${research?.source_count || 0} supplied passages</b>${evidence ? `<ul>${evidence}</ul>` : ''}</div>
      <div><small>CALCULATION</small><b>${calculation ? `${esc(calculation.expression)} = ${esc(calculation.value)}` : 'Not requested'}</b></div>
      <div><small>POLICY OUTCOME</small><b>${message ? `Approved · ${esc(message.message.delivery)} only` : 'No outbound artifact'}</b></div>
    </div>
    ${execution ? `<p><b>Execution:</b> ${esc(execution.planner)} planner · ${esc(execution.step_attempts)} attempts · ${esc(execution.replans)} replans · ${esc(execution.draft_revisions)} revisions</p>` : ''}
    <p>${esc(run.result.review.reflection)}</p>
    <details><summary>Exact artifact JSON</summary><pre>${esc(JSON.stringify(run.result.artifacts, null, 2))}</pre></details>
  </div>` : (run.error ? `<div class="result"><h4>Run error</h4><p>${esc(run.error)}</p></div>` : '');
  const events = run.events?.length ? `<details class="events"><summary>Audit event history · ${run.events.length} events</summary><ol>${run.events.map(event => `<li><time>${esc(new Date(event.created_at).toLocaleTimeString())}</time><b>${esc(event.type)}</b><span>${esc(event.actor)}</span></li>`).join('')}</ol></details>` : '';
  $('#detail').innerHTML = `
    <div class="detail-top"><div><span class="run-id">${esc(run.id)}</span><h3>${esc(run.objective)}</h3></div><span class="badge ${esc(run.status)}">${esc(run.status.replace('_',' '))}</span></div>
    <div class="timeline">${plan || '<p class="empty">Planning…</p>'}</div>${approval}${result}${events}`;
  document.querySelectorAll('[data-approve]').forEach(button => button.addEventListener('click', () => resolveApproval(run.id, waiting.id, button.dataset.approve === 'true')));
}

async function resolveApproval(runId, stepId, approved) {
  try {
    await api(`/api/runs/${runId}/approval`, { method:'POST', body:JSON.stringify({ step_id:stepId, approved }) });
    await Promise.all([loadRuns(), loadMetrics()]); await selectRun(runId); toast(approved ? 'Action approved and completed' : 'Action rejected');
  } catch (error) { toast(error.message); }
}

function schedulePoll() { clearTimeout(state.poll); state.poll = setTimeout(() => selectRun(state.selected), 800); }

// ---- Delegation form validation (client-side mirror of the server's rules) ----
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Returns an error message for the first malformed source line, or ''.
function validateSources(value) {
  const lines = value.split('\n');
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i].trim();
    if (!line) continue;
    const sep = line.indexOf('|');
    if (sep < 0) return `Line ${i + 1} is missing "|". Use: title | passage`;
    if (!line.slice(0, sep).trim()) return `Line ${i + 1} has no title before "|".`;
    if (!line.slice(sep + 1).trim()) return `Line ${i + 1} has no passage after "|".`;
  }
  return '';
}

// Recursive-descent check of: numbers, + - * / % **, unary minus, parentheses. No eval.
function validateExpression(value) {
  const text = value.trim();
  if (!text) return '';
  const tokens = text.match(/\d+\.?\d*|\.\d+|\*\*|[-+*/%()]|\S/g);
  let pos = 0;
  const peek = () => tokens[pos];
  const fail = (m) => { throw new Error(m); };
  function atom() {
    const t = peek();
    if (t === undefined) fail('Expression ends unexpectedly.');
    if (t === '(') { pos += 1; sum(); if (peek() !== ')') fail('Missing closing parenthesis.'); pos += 1; return; }
    if (t === '-' || t === '+') { pos += 1; atom(); return; }
    if (/^(\d|\.\d)/.test(t)) { pos += 1; return; }
    fail(`Unexpected "${t}". Use numbers, + - * / % ** and parentheses only.`);
  }
  function power() { atom(); if (peek() === '**') { pos += 1; power(); } }
  function product() { power(); while (['*', '/', '%'].includes(peek())) { pos += 1; power(); } }
  function sum() { product(); while (['+', '-'].includes(peek())) { pos += 1; product(); } }
  try { sum(); if (pos < tokens.length) fail(`Unexpected "${peek()}".`); } catch (error) { return error.message; }
  return '';
}

const FIELD_RULES = {
  objective: (v) => (v.trim().length < 3 ? 'Describe the outcome in at least 3 characters.' : ''),
  sources: validateSources,
  expression: validateExpression,
  recipient: (v) => (v.trim() && !EMAIL_RE.test(v.trim()) ? 'Enter a valid email address, e.g. name@example.com.' : ''),
};

function setFieldError(name, message) {
  const input = $(`#${name}`); const node = $(`#${name}-error`);
  node.textContent = message; node.hidden = !message;
  if (message) input.setAttribute('aria-invalid', 'true'); else input.removeAttribute('aria-invalid');
  return !message;
}

function validateField(name) { return setFieldError(name, FIELD_RULES[name]($(`#${name}`).value)); }

// Validates every field, focuses the first invalid one, and reports whether the form is valid.
function validateForm() {
  const invalid = Object.keys(FIELD_RULES).filter((name) => !validateField(name));
  if (invalid.length) {
    $('#sources').closest('details').open = true;
    $(`#${invalid[0]}`).focus();
  }
  return !invalid.length;
}

Object.keys(FIELD_RULES).forEach((name) => {
  const input = $(`#${name}`);
  input.addEventListener('blur', () => validateField(name));
  // Clear a shown error as soon as the user fixes it.
  input.addEventListener('input', () => { if (input.getAttribute('aria-invalid') === 'true') validateField(name); });
});

let submitting = false;
$('#run-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (submitting) return;
  const formError = $('#form-error'); formError.hidden = true; formError.textContent = '';
  if (!validateForm()) return;
  submitting = true;
  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true; button.setAttribute('aria-busy', 'true');
  button.firstElementChild.textContent = 'Deploying…';
  try {
    const expression = $('#expression').value.trim();
    const context = {
      send_message: $('#send-message').checked,
      sources: parseSources($('#sources').value),
      recipient: $('#recipient').value.trim() || 'project-sponsor@example.com',
      channel: 'email'
    };
    if (expression) context.expression = expression;
    const run = await api('/api/runs', { method:'POST', body:JSON.stringify({ objective:$('#objective').value, context }) });
    toast('Workforce deployed'); await loadMetrics(); await selectRun(run.id);
  } catch (error) {
    // Entered values are left untouched so the user can correct and retry.
    formError.textContent = `Could not deploy: ${error.message}. Your entries were kept; try again.`;
    formError.hidden = false;
    toast(error.message);
  } finally {
    submitting = false; button.disabled = false; button.removeAttribute('aria-busy');
    button.firstElementChild.textContent = 'Deploy workforce';
  }
});
$('#refresh').addEventListener('click', () => Promise.all([loadRuns(), loadMetrics()]));
Promise.all([loadRuns(), loadMetrics()])
  .then(() => state.selected && selectRun(state.selected))
  .catch(error => toast(error.message));
