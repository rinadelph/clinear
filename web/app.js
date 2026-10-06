const state = { token: localStorage.getItem("hoja_token"), issues: [], states: [] };
const $ = (id) => document.getElementById(id);

async function graphql(query, variables = {}) {
  const response = await fetch("/graphql", {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${state.token}` },
    body: JSON.stringify({ query, variables }),
  });
  const body = await response.json();
  if (!response.ok || body.errors) throw new Error(body.errors?.[0]?.message || "Request failed");
  return body.data;
}

function showWorkspace() { $("login").hidden = true; $("workspace").hidden = false; }
function showLogin(message = "") { $("login").hidden = false; $("workspace").hidden = true; $("login-error").textContent = message; }

async function load() {
  try {
    const data = await graphql(`query Workspace { viewer { name email } teams { nodes { id name key states { nodes { id name type color } } } } issues(first: 100, orderBy: createdAt) { nodes { id identifier title description priority priorityLabel state { id name type color } team { key name } assignee { name } } } }`);
    $("viewer").textContent = data.viewer?.name || data.viewer?.email || "Workspace member";
    const teams = data.teams.nodes;
    $("workspace-name").textContent = teams[0]?.name || "Workspace";
    $("teams").innerHTML = teams.map((team) => `<button class="team"><span class="team-dot" style="background:${team.states.nodes[0]?.color || '#7c6ff2'}"></span>${team.name}<span>${team.key}</span></button>`).join("");
    state.issues = data.issues.nodes;
    state.states = teams.flatMap((team) => team.states.nodes);
    $("issue-team").innerHTML = teams.map((team) => `<option value="${team.id}">${escapeHtml(team.name)} (${team.key})</option>`).join("");
    $("state-filter").innerHTML = `<option value="">All states</option>` + state.states.map((s) => `<option>${s.name}</option>`).join("");
    renderIssues();
  } catch (error) { localStorage.removeItem("hoja_token"); state.token = null; showLogin(error.message); }
}

function renderIssues() {
  const term = $("search").value.toLowerCase(); const filter = $("state-filter").value;
  const issues = state.issues.filter((issue) => (!filter || issue.state?.name === filter) && (!term || `${issue.identifier} ${issue.title}`.toLowerCase().includes(term)));
  $("issues").innerHTML = issues.length ? issues.map((issue) => `<article class="issue"><span class="priority p${issue.priority || 0}"></span><div class="issue-main"><strong>${escapeHtml(issue.title)}</strong><span class="issue-meta">${issue.identifier} · ${escapeHtml(issue.team?.name || "")} · ${escapeHtml(issue.state?.name || "No state")}</span></div><span class="assignee">${escapeHtml(issue.assignee?.name || "Unassigned")}</span></article>`).join("") : '<p class="muted">No issues match your filters.</p>';
}
function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c])); }

$("login-form").addEventListener("submit", async (event) => { event.preventDefault(); state.token = $("token").value.trim(); try { await load(); if (state.token) { localStorage.setItem("hoja_token", state.token); showWorkspace(); } } catch (_) {} });
$("logout").addEventListener("click", () => { localStorage.removeItem("hoja_token"); state.token = null; showLogin(); });
$("refresh").addEventListener("click", load); $("search").addEventListener("input", renderIssues); $("state-filter").addEventListener("change", renderIssues);
$("new-issue").addEventListener("click", () => { $("issue-error").textContent = ""; $("issue-form").reset(); $("issue-dialog").showModal(); });
$("close-dialog").addEventListener("click", () => $("issue-dialog").close());
$("issue-form").addEventListener("submit", async (event) => {
  event.preventDefault(); $("issue-error").textContent = ""; $("create-issue").disabled = true;
  try {
    const input = { title: $("issue-title").value.trim(), teamId: $("issue-team").value, description: $("issue-description").value.trim() || null, priority: Number($("issue-priority").value) };
    const result = await graphql(`mutation CreateIssue($input: IssueCreateInput!) { issueCreate(input: $input) { success issue { id } } }`, { input });
    if (!result.issueCreate.success) throw new Error("Could not create issue");
    $("issue-dialog").close(); await load();
  } catch (error) { $("issue-error").textContent = error.message; } finally { $("create-issue").disabled = false; }
});
if (state.token) { showWorkspace(); load(); }
