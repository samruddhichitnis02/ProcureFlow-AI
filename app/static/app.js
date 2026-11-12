document.addEventListener("DOMContentLoaded", () => {
  lucide.createIcons();
  loadMetricsSummary();
  loadOrders(false, false);
  loadPendingApprovals();
  loadAuditLogs();
});

function setQueryPreset(type) {
  const input = document.getElementById("agent-query-input");
  if (type === "delayed") {
    input.value = "Investigate delayed fulfillment and transit bottleneck for order ord_000001";
  } else if (type === "payment") {
    input.value = "Review payment anomaly and reconcile invoice for order ord_000003";
  } else if (type === "seller") {
    input.value = "Audit supplier fulfillment SLA rating and delayed order ratio for seller_0001";
  }
}

async function loadMetricsSummary() {
  try {
    const res = await fetch("/api/metrics/summary");
    if (!res.ok) return;
    const data = await res.json();
    document.getElementById("kpi-total-orders").textContent = data.total_orders.toLocaleString();
    document.getElementById("kpi-delay-rate").textContent = `${data.delayed_rate_percent}%`;
    document.getElementById("kpi-delay-count").textContent = `${data.delayed_orders} delayed`;
    document.getElementById("kpi-pending-approvals").textContent = data.pending_human_approvals;
    document.getElementById("queue-badge-count").textContent = `${data.pending_human_approvals} Pending`;
  } catch (err) {
    console.error("Failed to load metrics summary:", err);
  }
}

async function loadOrders(delayedOnly = false, paymentOnly = false) {
  const tbody = document.getElementById("orders-table-body");
  tbody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-slate-500">Loading orders...</td></tr>`;

  try {
    let url = `/api/orders?limit=25`;
    if (delayedOnly) url += `&delayed_only=true`;
    if (paymentOnly) url += `&payment_issues_only=true`;

    const res = await fetch(url);
    const data = await res.json();

    if (!data.orders || data.orders.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-slate-500">No matching orders found.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.orders.map(o => `
      <tr class="hover:bg-slate-800/40 transition">
        <td class="p-2.5 font-mono text-cyan-400 font-medium">${o.order_id}</td>
        <td class="p-2.5">
          <span class="px-2 py-0.5 rounded text-[10px] ${o.order_status === 'delivered' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-slate-800 text-slate-300'}">
            ${o.order_status}
          </span>
        </td>
        <td class="p-2.5 ${o.is_delayed ? 'text-amber-400 font-semibold' : 'text-slate-400'}">
          ${o.is_delayed ? `+${o.delay_days} days` : 'On-time'}
        </td>
        <td class="p-2.5">
          ${o.has_payment_issue ? '<span class="text-rose-400 font-semibold font-mono">[!] Discrepancy</span>' : '<span class="text-emerald-400 font-mono">[OK] Settled</span>'}
        </td>
        <td class="p-2.5 text-right">
          <button onclick="investigateTargetOrder('${o.order_id}')" class="px-2.5 py-1 text-[11px] rounded bg-cyan-900/40 hover:bg-cyan-800/60 border border-cyan-700/60 text-cyan-300 transition">
            Investigate
          </button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-rose-400">Failed to load orders: ${err}</td></tr>`;
  }
}

function investigateTargetOrder(orderId) {
  document.getElementById("agent-query-input").value = `Investigate order ${orderId} fulfillment status and payment details`;
  runInvestigation();
  window.scrollTo({ top: 180, behavior: "smooth" });
}

async function runInvestigation() {
  const query = document.getElementById("agent-query-input").value.trim();
  if (!query) return;

  const btn = document.getElementById("run-agent-btn");
  const stepper = document.getElementById("agent-stepper");
  const resContainer = document.getElementById("agent-result-container");
  
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Analyzing...</span>`;
  lucide.createIcons();

  stepper.classList.remove("hidden");
  resetStepper();

  // Animate stepper stages for visual feedback
  setStepState("step-triage", "step-active");
  setTimeout(() => setStepState("step-evidence", "step-active"), 200);
  setTimeout(() => setStepState("step-diagnose", "step-active"), 400);
  setTimeout(() => setStepState("step-action", "step-active"), 600);

  try {
    const res = await fetch("/api/agent/investigate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Agent workflow encountered an error.");

    // Complete stepper
    ["step-triage", "step-evidence", "step-diagnose", "step-action"].forEach(s => setStepState(s, "step-done"));

    // Render results
    resContainer.classList.remove("hidden");
    document.getElementById("res-intent").textContent = data.intent || "PROCUREMENT_INQUIRY";
    
    const statusBadge = document.getElementById("res-status-badge");
    statusBadge.textContent = data.approval_status;
    if (data.approval_status === "PENDING_APPROVAL") {
      statusBadge.className = "text-xs px-2.5 py-1 rounded-md font-mono bg-rose-950 text-rose-300 border border-rose-800";
    } else {
      statusBadge.className = "text-xs px-2.5 py-1 rounded-md font-mono bg-emerald-950 text-emerald-300 border border-emerald-800";
    }

    document.getElementById("res-accuracy").textContent = `Evidence Accuracy: ${data.evidence_accuracy_score}%`;
    document.getElementById("res-latency").textContent = `${data.latency_ms} ms`;

    // Render markdown report (simple formatting)
    document.getElementById("res-markdown").innerHTML = formatMarkdown(data.final_response);

    // Render evidence citations
    const evBox = document.getElementById("res-evidence-details");
    const diag = data.diagnosis || {};
    evBox.innerHTML = `
      <div class="space-y-1">
        <div><strong>Root Cause:</strong> ${diag.root_cause || 'N/A'}</div>
        <div><strong>Attribution:</strong> ${diag.delay_attribution || 'N/A'}</div>
        <div><strong>Delay Days:</strong> ${diag.delay_days !== undefined ? diag.delay_days : 'N/A'}</div>
        <div><strong>Payment Discrepancy:</strong> $${diag.payment_discrepancy || 0.0}</div>
        <div><strong>Relational Order Record:</strong> ${data.retrieved_evidence.order_found ? '✓ Verified in PostgreSQL/SQLite' : 'Not Found'}</div>
        <div><strong>Semantic Chunks Retrieved:</strong> ${data.retrieved_evidence.semantic_review_matches} matching review citations</div>
      </div>
    `;

    // Refresh pending queue & metrics
    loadPendingApprovals();
    loadMetricsSummary();
    loadAuditLogs();
  } catch (err) {
    alert("Investigation failed: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="play" class="w-4 h-4"></i><span>Investigate</span>`;
    lucide.createIcons();
  }
}

function resetStepper() {
  ["step-triage", "step-evidence", "step-diagnose", "step-action"].forEach(id => {
    const el = document.getElementById(id);
    el.className = "p-2.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-400 flex items-center space-x-2";
  });
}

function setStepState(id, cls) {
  const el = document.getElementById(id);
  if (el) el.classList.add(cls);
}

function formatMarkdown(text) {
  if (!text) return "";
  return text
    .replace(/^### (.*$)/gim, '<h3 class="text-sm font-bold text-cyan-400 mb-2">$1</h3>')
    .replace(/^## (.*$)/gim, '<h2 class="text-base font-bold text-white mb-2">$1</h2>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong class="text-slate-100">$1</strong>')
    .replace(/`([^`]+)`/gim, '<code class="bg-slate-800 text-cyan-300 px-1 py-0.5 rounded font-mono text-xs">$1</code>')
    .replace(/^\- (.*$)/gim, '<li class="ml-4 list-disc text-slate-300">$1</li>')
    .replace(/\n\n/gim, '<br/><br/>');
}

async function loadPendingApprovals() {
  const container = document.getElementById("pending-approvals-list");
  try {
    const res = await fetch("/api/agent/pending-approvals");
    const actions = await res.json();

    document.getElementById("queue-badge-count").textContent = `${actions.length} Pending`;

    if (actions.length === 0) {
      container.innerHTML = `<div class="text-xs text-slate-500 p-4 text-center">No actions currently pending approval.</div>`;
      return;
    }

    container.innerHTML = actions.map(a => `
      <div class="bg-slate-900 border border-rose-900/60 rounded-xl p-3.5 space-y-2.5">
        <div class="flex items-center justify-between">
          <span class="text-xs font-mono font-bold text-rose-300">${a.action_type}</span>
          <span class="text-xs px-2 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-800 font-mono">$${a.amount.toFixed(2)}</span>
        </div>
        <div class="text-xs text-slate-300">
          <div><span class="text-slate-500">Order:</span> <span class="font-mono text-cyan-400">${a.order_id}</span></div>
          <div class="mt-1"><span class="text-slate-500">Reason:</span> ${a.reason}</div>
        </div>
        <div class="flex items-center space-x-2 pt-2 border-t border-slate-800">
          <button onclick="resolveApproval('${a.action_id}', 'APPROVED')" 
            class="flex-1 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition">
            ✓ Approve
          </button>
          <button onclick="resolveApproval('${a.action_id}', 'REJECTED')" 
            class="flex-1 py-1.5 rounded-lg bg-rose-600/80 hover:bg-rose-500 text-white font-semibold text-xs transition">
            ✕ Reject
          </button>
        </div>
      </div>
    `).join("");
  } catch (err) {
    container.innerHTML = `<div class="text-xs text-rose-400 p-3">Failed to load approvals: ${err}</div>`;
  }
}

async function resolveApproval(actionId, decision) {
  try {
    const res = await fetch(`/api/agent/approve/${actionId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision,
        reviewed_by: "Lead_Procurement_Officer",
        notes: `Action marked as ${decision} via enterprise Agentforce dashboard.`,
      }),
    });

    if (!res.ok) throw new Error("Approval submission failed.");
    loadPendingApprovals();
    loadMetricsSummary();
    loadAuditLogs();
  } catch (err) {
    alert("Error: " + err.message);
  }
}

async function runLatencyBenchmark() {
  const btn = document.getElementById("bench-btn");
  const statusEl = document.getElementById("bench-status");
  btn.disabled = true;
  statusEl.textContent = "Running 100 concurrent non-generation retrieval operations...";

  try {
    const res = await fetch("/api/metrics/p95-benchmark?samples=100");
    const data = await res.json();

    document.getElementById("bench-p50").textContent = `${data.p50_latency_ms} ms`;
    document.getElementById("bench-p90").textContent = `${data.p90_latency_ms} ms`;
    document.getElementById("bench-p95").textContent = `${data.p95_latency_ms} ms`;

    statusEl.innerHTML = `<span class="text-emerald-400 font-semibold">✓ ${data.status} (SLA &lt; ${data.sla_target_ms} ms)</span>`;
  } catch (err) {
    statusEl.innerHTML = `<span class="text-rose-400">Benchmark error: ${err}</span>`;
  } finally {
    btn.disabled = false;
  }
}

async function loadAuditLogs() {
  const list = document.getElementById("audit-logs-list");
  try {
    const res = await fetch("/api/audit-logs?limit=8");
    const data = await res.json();

    if (!data.logs || data.logs.length === 0) {
      list.innerHTML = `<div class="text-slate-500 p-3 text-center">No audit logs recorded yet.</div>`;
      return;
    }

    list.innerHTML = data.logs.map(l => `
      <div class="bg-slate-900/80 p-2 rounded border border-slate-800 space-y-1">
        <div class="flex items-center justify-between text-[11px]">
          <span class="text-cyan-400 font-semibold">${l.event_type}</span>
          <span class="text-slate-500">${l.timestamp ? l.timestamp.split("T")[1].slice(0, 8) : ''}</span>
        </div>
        <div class="text-[11px] text-slate-300 truncate">${l.details}</div>
        <div class="text-[10px] text-slate-500">Actor: ${l.actor}</div>
      </div>
    `).join("");
  } catch (err) {
    list.innerHTML = `<div class="text-rose-400 p-2">Error loading audit logs.</div>`;
  }
}

