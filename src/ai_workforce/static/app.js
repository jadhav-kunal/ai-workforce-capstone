const state = {
  selected: new URLSearchParams(window.location.search).get('run'),
  poll: null,
  detailTab: 'summary',
  submitting: false,
};
const $ = (selector) => document.querySelector(selector);
const ARITHMETIC_RE = /^[\d\s+\-*/().]+$/;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

function toast(message) {
  const node = $('#toast');
  node.textContent = message;
  node.classList.add('show');
  window.setTimeout(() => node.classList.remove('show'), 2600);
}

function esc(value) {
  return String(value ?? '').replace(/[&<>'"]/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;',
  }[c]));
}

function setFieldError(id, message) {
  const field = document.getElementById(id)?.closest('.field');
  const error = document.getElementById(`${id}-error`);
  if (!field || !error) return;
  if (message) {
    field.classList.add('invalid');
    error.hidden = false;
    error.textContent = message;
    document.getElementById(id)?.setAttribute('aria-invalid', 'true');
  } else {
    field.classList.remove('invalid');
    error.hidden = true;
    error.textContent = '';
    document.getElementById(id)?.removeAttribute('aria-invalid');
  }
}

function parseSources(value) {
  const lines = value.split('\n').map(line => line.trim()).filter(Boolean);
  const sources = [];
  const errors = [];

  lines.forEach((line, index) => {
    const separator = line.indexOf('|');
    if (separator < 0) {
      errors.push(`Line ${index + 1}: use "title | passage".`);
      return;
    }
    const title = line.slice(0, separator).trim();
    const content = line.slice(separator + 1).trim();
    if (!title || !content) {
      errors.push(`Line ${index + 1}: title and passage are both required.`);
      return;
    }
    sources.push({ title, content });
  });

  return { sources, errors };
}

function validateExpression(value) {
  const expression = value.trim();
  if (!expression) return '';
  if (!ARITHMETIC_RE.test(expression)) {
    return 'Use only numbers and + - * / ( ).';
  }
  try {
    // eslint-disable-next-line no-new-func
    const result = Function(`"use strict"; return (${expression});`)();
    if (typeof result !== 'number' || !Number.isFinite(result)) {
      return 'Expression must evaluate to a finite number.';
    }
  } catch {
    return 'Expression is not valid arithmetic.';
  }
  return '';
}

function validateForm() {
  let firstInvalid = null;

  const objective = $('#objective').value.trim();
  const objectiveError = objective.length < 3 ? 'Enter an objective with at least 3 characters.' : '';
  setFieldError('objective', objectiveError);
  if (objectiveError && !firstInvalid) firstInvalid = $('#objective');

  const { sources, errors: sourceErrors } = parseSources($('#sources').value);
  const sourcesError = sourceErrors[0] || (sources.length ? '' : 'Add at least one source line as "title | passage".');
  setFieldError('sources', sourcesError);
  if (sourcesError && !firstInvalid) firstInvalid = $('#sources');

  const expressionError = validateExpression($('#expression').value);
  setFieldError('expression', expressionError);
  if (expressionError && !firstInvalid) firstInvalid = $('#expression');

  const recipient = $('#recipient').value.trim();
  let recipientError = '';
  if ($('#send-message').checked) {
    if (!recipient) recipientError = 'Recipient email is required when sending an update.';
    else if (!EMAIL_RE.test(recipient)) recipientError = 'Enter a valid email address.';
  } else if (recipient && !EMAIL_RE.test(recipient)) {
    recipientError = 'Enter a valid email address.';
  }
  setFieldError('recipient', recipientError);
  if (recipientError && !firstInvalid) firstInvalid = $('#recipient');

  return { ok: !firstInvalid, firstInvalid, sources };
}

function setSubmitting(isSubmitting) {
  state.submitting = isSubmitting;
  const button = $('#submit-run');
  const status = $('#form-status');
  button.disabled = isSubmitting;
  button.querySelector('span').textContent = isSubmitting ? 'Deploying…' : 'Deploy workforce';
  if (isSubmitting) {
    status.hidden = false;
    status.textContent = 'Request in progress. Form values are preserved if the API call fails.';
  } else {
    status.hidden = true;
    status.textContent = '';
  }
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
  if (!runs.length) {
    container.innerHTML = '<p class="empty">No runs yet. Delegate an outcome above.</p>';
    return;
  }
  container.innerHTML = runs.map(run => `
    <article class="run-card ${run.id === state.selected ? 'active' : ''}" data-id="${esc(run.id)}" tabindex="0" role="button" aria-label="Open run ${esc(run.objective)}">
      <time>${new Date(run.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time>
      <strong>${esc(run.objective)}</strong>
      <span class="badge ${esc(run.status)}">${esc(run.status.replace('_', ' '))}</span>
    </article>`).join('');
  container.querySelectorAll('.run-card').forEach(card => {
    card.addEventListener('click', () => selectRun(card.dataset.id));
    card.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        selectRun(card.dataset.id);
      }
    });
  });
}

async function selectRun(id) {
  state.selected = id;
  window.history.replaceState(null, '', `?run=${encodeURIComponent(id)}`);
  await loadRuns();
  const run = await api(`/api/runs/${id}`);
  renderDetail(run);
  const transient = ['queued', 'running'].includes(run.status);
  if (transient) schedulePoll();
  else clearTimeout(state.poll);
}

function renderSummary(run) {
  const waiting = run.plan.find(step => step.status === 'waiting_approval');
  const plan = run.plan.map((step, index) => `
    <div class="step ${esc(step.status)}">
      <span class="step-dot">${step.status === 'completed' ? '✓' : index + 1}</span>
      <div>
        <h4>${esc(step.title)}</h4>
        <p>${esc(step.agent)} · ${esc(step.tool)} · ${esc(step.risk)} risk${Object.keys(step.arguments || {}).length ? ` · ${esc(JSON.stringify(step.arguments))}` : ''}</p>
      </div>
    </div>`).join('');
  const approval = waiting
    ? `<div class="approval"><p><strong>Human decision required.</strong><br>This step creates an external-facing artifact in the simulated outbox.</p><button type="button" data-approve="true">Approve & continue</button><button type="button" class="reject" data-approve="false">Reject</button></div>`
    : '';
  const calculation = run.result?.artifacts?.find(item => Object.hasOwn(item, 'value'));
  const research = run.result?.artifacts?.find(item => item.findings);
  const message = run.result?.artifacts?.find(item => item.message);
  const evidence = research?.findings?.map((item, index) => `<li><b>${esc(item.id || `S${index + 1}`)}</b> ${esc(item.title)}</li>`).join('') || '';
  const execution = run.result?.execution;
  const result = run.result
    ? `<div class="result">
        <div class="result-head"><h4>Verified run result</h4><strong>${Math.round(run.result.review.quality_score * 100)}% grounding score</strong></div>
        <div class="result-grid">
          <div><small>EVIDENCE</small><b>${research?.source_count || 0} supplied passages</b>${evidence ? `<ul>${evidence}</ul>` : ''}</div>
          <div><small>CALCULATION</small><b>${calculation ? `${esc(calculation.expression)} = ${esc(calculation.value)}` : 'Not requested'}</b></div>
          <div><small>POLICY OUTCOME</small><b>${message ? `Approved · ${esc(message.message.delivery)} only` : 'No outbound artifact'}</b></div>
        </div>
        ${execution ? `<p><b>Execution:</b> ${esc(execution.planner)} planner · ${esc(execution.step_attempts)} attempts · ${esc(execution.replans)} replans · ${esc(execution.draft_revisions)} revisions</p>` : ''}
        <p>${esc(run.result.review.reflection)}</p>
      </div>`
    : (run.error ? `<div class="result"><h4>Run error</h4><p>${esc(run.error)}</p></div>` : '');

  return `${approval}<div class="timeline">${plan || '<p class="empty">Planning…</p>'}</div>${result}`;
}

function renderArtifacts(run) {
  if (!run.result?.artifacts) {
    return `<div class="artifact-panel"><h4>Artifacts</h4><p class="empty">${run.error ? esc(run.error) : 'No artifacts yet for this run.'}</p></div>`;
  }
  return `<div class="artifact-panel"><h4>Exact artifact JSON</h4><pre>${esc(JSON.stringify(run.result.artifacts, null, 2))}</pre></div>`;
}

function renderAudit(run) {
  if (!run.events?.length) {
    return `<div class="events"><h4>Audit history</h4><p class="empty">No audit events recorded yet.</p></div>`;
  }
  return `<div class="events"><h4>Audit history · ${run.events.length} events</h4><ol>${run.events.map(event => `
    <li>
      <time>${esc(new Date(event.created_at).toLocaleTimeString())}</time>
      <b>${esc(event.type)}</b>
      <span>${esc(event.actor)}</span>
    </li>`).join('')}</ol></div>`;
}

function renderDetail(run) {
  const waiting = run.plan.find(step => step.status === 'waiting_approval');
  const activeTab = ['summary', 'artifacts', 'audit'].includes(state.detailTab) ? state.detailTab : 'summary';
  state.detailTab = activeTab;

  $('#detail').innerHTML = `
    <div class="detail-top">
      <div>
        <span class="run-id">${esc(run.id)}</span>
        <h3>${esc(run.objective)}</h3>
      </div>
      <span class="badge ${esc(run.status)}">${esc(run.status.replace('_', ' '))}</span>
    </div>
    <div class="detail-tabs" role="tablist" aria-label="Run detail sections">
      <button type="button" class="tab" role="tab" id="tab-summary" aria-controls="panel-summary" aria-selected="${activeTab === 'summary'}" tabindex="${activeTab === 'summary' ? '0' : '-1'}" data-tab="summary">Summary</button>
      <button type="button" class="tab" role="tab" id="tab-artifacts" aria-controls="panel-artifacts" aria-selected="${activeTab === 'artifacts'}" tabindex="${activeTab === 'artifacts' ? '0' : '-1'}" data-tab="artifacts">Artifacts</button>
      <button type="button" class="tab" role="tab" id="tab-audit" aria-controls="panel-audit" aria-selected="${activeTab === 'audit'}" tabindex="${activeTab === 'audit' ? '0' : '-1'}" data-tab="audit">Audit History</button>
    </div>
    <div class="tab-panel" role="tabpanel" id="panel-summary" aria-labelledby="tab-summary" ${activeTab === 'summary' ? '' : 'hidden'}>
      ${activeTab === 'summary' ? renderSummary(run) : ''}
    </div>
    <div class="tab-panel" role="tabpanel" id="panel-artifacts" aria-labelledby="tab-artifacts" ${activeTab === 'artifacts' ? '' : 'hidden'}>
      ${activeTab === 'artifacts' ? renderArtifacts(run) : ''}
    </div>
    <div class="tab-panel" role="tabpanel" id="panel-audit" aria-labelledby="tab-audit" ${activeTab === 'audit' ? '' : 'hidden'}>
      ${activeTab === 'audit' ? renderAudit(run) : ''}
    </div>`;

  const tabs = [...document.querySelectorAll('.detail-tabs .tab')];
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => {
      state.detailTab = tab.dataset.tab;
      renderDetail(run);
      document.getElementById(`tab-${state.detailTab}`)?.focus();
    });
    tab.addEventListener('keydown', event => {
      const current = index;
      let next = current;
      if (event.key === 'ArrowRight') next = (current + 1) % tabs.length;
      else if (event.key === 'ArrowLeft') next = (current - 1 + tabs.length) % tabs.length;
      else if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = tabs.length - 1;
      else return;
      event.preventDefault();
      state.detailTab = tabs[next].dataset.tab;
      renderDetail(run);
      document.getElementById(`tab-${state.detailTab}`)?.focus();
    });
  });

  document.querySelectorAll('[data-approve]').forEach(button => {
    button.addEventListener('click', () => resolveApproval(run.id, waiting.id, button.dataset.approve === 'true'));
  });
}

async function resolveApproval(runId, stepId, approved) {
  try {
    await api(`/api/runs/${runId}/approval`, {
      method: 'POST',
      body: JSON.stringify({ step_id: stepId, approved }),
    });
    await Promise.all([loadRuns(), loadMetrics()]);
    await selectRun(runId);
    toast(approved ? 'Action approved and completed' : 'Action rejected');
  } catch (error) {
    toast(error.message);
  }
}

function schedulePoll() {
  clearTimeout(state.poll);
  state.poll = setTimeout(() => selectRun(state.selected), 800);
}

['objective', 'sources', 'expression', 'recipient'].forEach(id => {
  const node = document.getElementById(id);
  node?.addEventListener('input', () => {
    if (document.getElementById(`${id}-error`) && !document.getElementById(`${id}-error`).hidden) {
      validateForm();
    }
  });
});
$('#send-message')?.addEventListener('change', () => {
  if (!document.getElementById('recipient-error').hidden) validateForm();
});

$('#run-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (state.submitting) return;

  const { ok, firstInvalid, sources } = validateForm();
  if (!ok) {
    firstInvalid?.focus();
    toast('Fix the highlighted fields before deploying.');
    return;
  }

  setSubmitting(true);
  try {
    const expression = $('#expression').value.trim();
    const context = {
      send_message: $('#send-message').checked,
      sources,
      recipient: $('#recipient').value.trim() || 'project-sponsor@example.com',
      channel: 'email',
    };
    if (expression) context.expression = expression;
    const run = await api('/api/runs', {
      method: 'POST',
      body: JSON.stringify({ objective: $('#objective').value.trim(), context }),
    });
    toast('Workforce deployed');
    await loadMetrics();
    await selectRun(run.id);
  } catch (error) {
    toast(error.message);
  } finally {
    setSubmitting(false);
  }
});

$('#refresh').addEventListener('click', () => Promise.all([loadRuns(), loadMetrics()]));
Promise.all([loadRuns(), loadMetrics()])
  .then(() => state.selected && selectRun(state.selected))
  .catch(error => toast(error.message));
