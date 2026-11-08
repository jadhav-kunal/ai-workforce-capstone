const state = { selected: new URLSearchParams(window.location.search).get('run'), poll: null, lastStatus: {} };
const $ = (selector) => document.querySelector(selector);

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || `Request failed (${response.status})`); }
  return response.json();
}

// Visible toast + live region. Errors use role="alert" (assertive); everything else is a polite status.
let toastTimer = null;
function toast(message, isError = false) {
  const node = $(isError ? '#toast-error' : '#toast');
  $(isError ? '#toast' : '#toast-error').classList.remove('show');
  node.textContent = '';
  // Re-set text on the next tick so repeated identical messages are announced again.
  window.setTimeout(() => { node.textContent = message; node.classList.add('show'); }, 30);
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => node.classList.remove('show'), isError ? 6000 : 4000);
}

// Screen-reader-only announcements (loading, run status changes) that need no visual toast.
function announce(message) {
  const node = $('#sr-status'); node.textContent = '';
  window.setTimeout(() => { node.textContent = message; }, 30);
}

const label = (value) => String(value ?? '').replace(/_/g, ' ');

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
  const container = $('#runs');
  container.setAttribute('aria-busy', 'true');
  try {
    const runs = await api('/api/runs');
    if (!runs.length) { container.innerHTML = '<p class="empty">No runs yet. Delegate an outcome above.</p>'; return; }
    // Keep keyboard focus on the same run if the list is re-rendered (refresh, polling).
    const focusedId = document.activeElement?.closest?.('.run-card')?.dataset.id;
    container.innerHTML = `<ul class="run-items">${runs.map(run => `
      <li><button type="button" class="btn run-card ${run.id === state.selected ? 'active' : ''}" data-id="${esc(run.id)}" ${run.id === state.selected ? 'aria-current="true"' : ''}>
        <time datetime="${esc(run.created_at)}">${new Date(run.created_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</time>
        <strong><span class="sr-only">Run: </span>${esc(run.objective)}</strong>
        <span class="badge ${esc(run.status)}"><span class="sr-only">Status: </span>${esc(label(run.status))}</span>
      </button></li>`).join('')}</ul>`;
    container.querySelectorAll('.run-card').forEach(card => card.addEventListener('click', () => selectRun(card.dataset.id, { focus: true })));
    if (focusedId) container.querySelector(`.run-card[data-id="${CSS.escape(focusedId)}"]`)?.focus();
  } finally { container.setAttribute('aria-busy', 'false'); }
}

async function selectRun(id, { focus = false } = {}) {
  state.selected = id;
  window.history.replaceState(null, '', `?run=${encodeURIComponent(id)}`);
  const detail = $('#detail');
  detail.setAttribute('aria-busy', 'true');
  if (focus) announce('Loading run details…');
  await loadRuns();
  const run = await api(`/api/runs/${id}`);
  renderDetail(run);
  detail.setAttribute('aria-busy', 'false');
  if (focus) $('#detail-title')?.focus();
  if (state.lastStatus[id] !== run.status) {
    if (state.lastStatus[id] !== undefined || focus) announce(`Run status: ${label(run.status)}${run.status === 'waiting_approval' ? '. Human approval is required.' : ''}`);
    state.lastStatus[id] = run.status;
  }
  const transient = ['queued','running'].includes(run.status);
  if (transient) schedulePoll(); else clearTimeout(state.poll);
}

function renderDetail(run) {
  const waiting = run.plan.find(step => step.status === 'waiting_approval');
  const plan = run.plan.map((step, index) => `
    <div class="step ${esc(step.status)}" role="listitem">
      <span class="step-dot" aria-hidden="true">${step.status === 'completed' ? '✓' : step.status === 'waiting_approval' ? '!' : index + 1}</span>
      <div><h4>${esc(step.title)} <span class="step-status">${esc(label(step.status))}</span></h4><p>${esc(step.agent)} · ${esc(step.tool)} · ${esc(step.risk)} risk${Object.keys(step.arguments || {}).length ? ` · ${esc(JSON.stringify(step.arguments))}` : ''}</p></div>
    </div>`).join('');
  const approval = waiting ? `<div class="panel approval" role="group" aria-labelledby="approval-title"><p><strong id="approval-title">Human decision required.</strong><br>This step creates an external-facing artifact in the simulated outbox.</p><button class="btn btn-solid" type="button" data-approve="true">Approve &amp; continue</button><button class="btn btn-danger" type="button" data-approve="false">Reject</button></div>` : '';
  const calculation = run.result?.artifacts?.find(item => Object.hasOwn(item, 'value'));
  const research = run.result?.artifacts?.find(item => item.findings);
  const message = run.result?.artifacts?.find(item => item.message);
  const evidence = research?.findings?.map((item, index) => `<li><b>${esc(item.id || `S${index + 1}`)}</b> ${esc(item.title)}</li>`).join('') || '';
  const execution = run.result?.execution;
  const result = run.result ? `<div class="panel result">
    <div class="result-head"><h4>Verified run result</h4><strong>${Math.round(run.result.review.quality_score * 100)}% grounding score</strong></div>
    <div class="result-grid">
      <div><small>EVIDENCE</small><b>${research?.source_count || 0} supplied passages</b>${evidence ? `<ul>${evidence}</ul>` : ''}</div>
      <div><small>CALCULATION</small><b>${calculation ? `${esc(calculation.expression)} = ${esc(calculation.value)}` : 'Not requested'}</b></div>
      <div><small>POLICY OUTCOME</small><b>${message ? `Approved · ${esc(message.message.delivery)} only` : 'No outbound artifact'}</b></div>
    </div>
    ${execution ? `<p><b>Execution:</b> ${esc(execution.planner)} planner · ${esc(execution.step_attempts)} attempts · ${esc(execution.replans)} replans · ${esc(execution.draft_revisions)} revisions</p>` : ''}
    <p>${esc(run.result.review.reflection)}</p>
    <details><summary>Exact artifact JSON</summary><pre>${esc(JSON.stringify(run.result.artifacts, null, 2))}</pre></details>
  </div>` : (run.error ? `<div class="panel result"><h4>Run error</h4><p>${esc(run.error)}</p></div>` : '');
  const events = run.events?.length ? `<details class="panel events"><summary>Audit event history · ${run.events.length} events</summary><ol>${run.events.map(event => `<li><time datetime="${esc(event.created_at)}">${esc(new Date(event.created_at).toLocaleTimeString())}</time><b>${esc(event.type)}</b><span>${esc(event.actor)}</span></li>`).join('')}</ol></details>` : '';
  $('#detail').innerHTML = `
    <div class="detail-top"><div><span class="run-id">${esc(run.id)}</span><h3 id="detail-title" tabindex="-1">${esc(run.objective)}</h3></div><span class="badge ${esc(run.status)}"><span class="sr-only">Status: </span>${esc(label(run.status))}</span></div>
    <div class="timeline" role="list" aria-label="Plan steps">${plan || '<p class="empty">Planning…</p>'}</div>${approval}${result}${events}`;
  document.querySelectorAll('[data-approve]').forEach(button => button.addEventListener('click', () => resolveApproval(run.id, waiting.id, button.dataset.approve === 'true')));
}

async function resolveApproval(runId, stepId, approved) {
  try {
    await api(`/api/runs/${runId}/approval`, { method:'POST', body:JSON.stringify({ step_id:stepId, approved }) });
    await Promise.all([loadRuns(), loadMetrics()]); await selectRun(runId, { focus: true }); toast(approved ? 'Action approved and completed' : 'Action rejected');
  } catch (error) { toast(error.message, true); }
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
    announce(`${invalid.length} field${invalid.length > 1 ? 's need' : ' needs'} attention.`);
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
  const button = event.currentTarget.querySelector('button[type="submit"]');
  button.disabled = true; button.setAttribute('aria-busy', 'true');
  button.firstElementChild.textContent = 'Deploying…';
  announce('Deploying workforce…');
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
    toast('Workforce deployed'); await loadMetrics(); await selectRun(run.id, { focus: true });
  } catch (error) {
    // Entered values are left untouched so the user can correct and retry.
    formError.textContent = `Could not deploy: ${error.message}. Your entries were kept; try again.`;
    formError.hidden = false;
    toast(error.message, true);
  } finally {
    submitting = false; button.disabled = false; button.removeAttribute('aria-busy');
    button.firstElementChild.textContent = 'Deploy workforce';
  }
});
$('#refresh').addEventListener('click', () => {
  announce('Refreshing run log…');
  Promise.all([loadRuns(), loadMetrics()]).then(() => announce('Run log refreshed')).catch(error => toast(error.message, true));
});
Promise.all([loadRuns(), loadMetrics()])
  .then(() => state.selected && selectRun(state.selected))
  .catch(error => toast(error.message, true));
