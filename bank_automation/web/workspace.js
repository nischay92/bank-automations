'use strict';

const root = document.getElementById('content');
const members = {
  '12345': {name: 'Alex Example', balance: '2400.00'},
  '23456': {name: 'Jordan Sample', balance: '1875.50'},
  '34567': {name: 'Casey Demo', balance: '925.00'},
};
const scenario = new URL(parent.location.href).searchParams.get('scenario') || 'normal';
const scenarioNames = {
  slow: 'Slow recovery',
  stuck: 'Loading timeout',
  expired: 'Session handoff',
  denied: 'Permission denied',
  ambiguous: 'Ambiguous target',
  disabled: 'Disabled target',
  drift: 'UI label drift',
  blocked: 'Blocked request',
  dialog: 'Unexpected dialog',
  review_mismatch: 'Review mismatch',
};

let memberId = '';
let nickname = '';
let expired = false;

const escapeHtml = value => String(value).replace(
  /[&<>"']/g,
  character => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[character]),
);

function show(html) {
  const banner = scenarioNames[scenario]
    ? `<div class="scenario-banner" role="status">Synthetic scenario: ${scenarioNames[scenario]}</div>`
    : '';
  root.innerHTML = banner + html;
}

function button(name, onClick, className = '') {
  const control = document.createElement('button');
  control.textContent = name;
  control.className = className;
  control.onclick = onClick;
  root.appendChild(control);
  return control;
}

function search() {
  show('<h1>Member search</h1><p class="muted">Find a member to begin servicing.</p><label for="member">Member ID</label><input id="member" autocomplete="off" inputmode="numeric">');
  const runSearch = async () => {
    memberId = document.getElementById('member').value;
    if (!/^\d{5}$/.test(memberId)) {
      show('<h1>Validation rejected</h1><p role="alert">Member ID must contain five digits.</p>');
      return;
    }
    if (scenario === 'dialog' && !window.confirm('Continue member search?')) return;
    if (scenario === 'blocked') {
      fetch('/admin').catch(() => {});
      return;
    }
    if (scenario === 'slow' || scenario === 'stuck') {
      show('<h1>Loading</h1><p role="status">Loading member record…</p>');
      if (scenario === 'stuck') return;
      await new Promise(resolve => setTimeout(resolve, 1600));
    }
    if (memberId === '99999' || !members[memberId]) {
      show('<h1>Member not found</h1><p role="alert">No matching member.</p>');
      return;
    }
    if (scenario === 'denied') {
      show('<h1>Permission denied</h1><p role="alert">Your role cannot access this record.</p>');
      return;
    }
    details();
  };
  const searchButton = button(scenario === 'drift' ? 'Find member' : 'Search', runSearch);
  if (scenario === 'ambiguous') button('Search', runSearch);
  if (scenario === 'disabled') searchButton.disabled = true;
}

function details() {
  show(`<h1>Member details</h1><p>${escapeHtml(members[memberId].name)}</p><dl><dt>Member ID</dt><dd>${escapeHtml(memberId)}</dd></dl><table><thead><tr><th>Account</th><th>Status</th></tr></thead><tbody><tr><td>Primary savings</td><td>Active</td></tr></tbody></table>`);
  button('View savings', account);
}

function account() {
  show(`<h1>Savings account</h1><dl><dt>Account type</dt><dd>Savings</dd><dt>Current balance</dt><dd>$${members[memberId].balance}</dd></dl>`);
  button('New sub-account', () => {
    if (scenario === 'expired' && !expired) {
      expired = true;
      login();
    } else {
      form();
    }
  });
}

function login() {
  show('<h1>Session expired</h1><p class="notice">Restore your training session to continue.</p><label for="operator">Operator name</label><input id="operator" autocomplete="off"><label for="password">Training password</label><input type="password" id="password" autocomplete="off">');
  button('Restore session', () => {
    if (document.getElementById('operator').value && document.getElementById('password').value) form();
  });
}

function form() {
  show('<h1>New sub-account</h1><label for="kind">Account type</label><select id="kind"><option value="savings">Savings</option></select><label for="nickname">Nickname</label><input id="nickname" maxlength="30" autocomplete="off">');
  button('Review', () => {
    nickname = document.getElementById('nickname').value.trim();
    if (!nickname || nickname.toLowerCase() === 'reserved') {
      show('<h1>Validation rejected</h1><p role="alert">Nickname is unavailable.</p>');
      return;
    }
    review();
  });
}

function review() {
  const displayedNickname = scenario === 'review_mismatch' ? `${nickname} changed` : nickname;
  show(`<h1>Review sub-account</h1><p class="notice">Review the details before creating the account. Nothing has been submitted.</p><dl><dt>Member ID</dt><dd>${escapeHtml(memberId)}</dd><dt>Account type</dt><dd>Savings</dd><dt>Nickname</dt><dd>${escapeHtml(displayedNickname)}</dd></dl>`);
  button('Create account', () => show('<h1>Account created</h1>'), 'danger');
}

search();
