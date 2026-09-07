const state = { selected: null, poll: null };
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
      <div><h4>${esc(step.title)}</h4><p>${esc(step.agent)} · ${esc(step.tool)} · ${esc(step.risk)} risk</p></div>
    </div>`).join('');
  const approval = waiting ? `<div class="approval"><p><strong>Human decision required.</strong><br>This step creates an external-facing artifact in the simulated outbox.</p><button data-approve="true">Approve & continue</button><button class="reject" data-approve="false">Reject</button></div>` : '';
  const result = run.result ? `<div class="result"><h4>Quality review · ${Math.round(run.result.review.quality_score * 100)}%</h4><p>${esc(run.result.review.reflection)}</p><pre>${esc(JSON.stringify(run.result.artifacts, null, 2))}</pre></div>` : (run.error ? `<div class="result"><h4>Run error</h4><p>${esc(run.error)}</p></div>` : '');
  $('#detail').innerHTML = `
    <div class="detail-top"><div><span class="run-id">${esc(run.id)}</span><h3>${esc(run.objective)}</h3></div><span class="badge ${esc(run.status)}">${esc(run.status.replace('_',' '))}</span></div>
    <div class="timeline">${plan || '<p class="empty">Planning…</p>'}</div>${approval}${result}`;
  document.querySelectorAll('[data-approve]').forEach(button => button.addEventListener('click', () => resolveApproval(run.id, waiting.id, button.dataset.approve === 'true')));
}

async function resolveApproval(runId, stepId, approved) {
  try {
    const run = await api(`/api/runs/${runId}/approval`, { method:'POST', body:JSON.stringify({ step_id:stepId, approved }) });
    renderDetail(run); await Promise.all([loadRuns(), loadMetrics()]); toast(approved ? 'Action approved and completed' : 'Action rejected');
  } catch (error) { toast(error.message); }
}

function schedulePoll() { clearTimeout(state.poll); state.poll = setTimeout(() => selectRun(state.selected), 800); }

$('#run-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = event.currentTarget.querySelector('button'); button.disabled = true;
  try {
    const run = await api('/api/runs', { method:'POST', body:JSON.stringify({ objective:$('#objective').value, context:{ send_message:$('#send-message').checked } }) });
    toast('Workforce deployed'); await loadMetrics(); await selectRun(run.id);
  } catch (error) { toast(error.message); } finally { button.disabled = false; }
});
$('#refresh').addEventListener('click', () => Promise.all([loadRuns(), loadMetrics()]));
Promise.all([loadRuns(), loadMetrics()]).catch(error => toast(error.message));
