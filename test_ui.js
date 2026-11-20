// Optional UI state regression check: node test_ui.js (no npm packages).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const nodes = new Map();
const context2d = new Proxy({}, { get: (_, key) => key === 'createLinearGradient'
  ? () => ({ addColorStop() {} }) : () => {} });
function element() {
  return { innerHTML: '', textContent: '', value: '', dataset: {}, disabled: false,
    clientWidth: 700, clientHeight: 450, style: { setProperty() {} },
    classList: { add() {}, remove() {}, toggle() {} },
    setAttribute() {}, addEventListener() {}, appendChild() {}, replaceChildren(...children) { this.children = children; },
    querySelectorAll: () => [], getContext: () => context2d, parentElement: {} };
}
const document = { getElementById(id) { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); },
  createElement: element, querySelectorAll: () => [] };
let ticks = null;
const calls = [];
const cp = { kind: 'closest_pair', name: 'points.txt', size: 20, preview: '0 0\n3 4', input: { points: [[0, 0], [3, 4]] } };
const integer = { kind: 'integer_multiplication', name: 'numbers.txt', size: 5, preview: '12\n34', input: { a: '12', b: '34' } };
const answer = { kind: 'answer', title: 'Final answer', depth: 0, boxes: [], splits: [], lines: ['Complete'] };
const middle = { kind: 'multiply', title: 'Multiply', depth: 0, boxes: [], splits: [], lines: ['12 × 34 = 408'] };
const sandbox = { document, window: { addEventListener() {}, devicePixelRatio: 1 },
  ResizeObserver: class { observe() {} }, console, setTimeout: () => 1, clearTimeout() {},
  setInterval(fn) { ticks = fn; return 1; }, clearInterval() { ticks = null; },
  fetch: async (url, options) => {
    calls.push(url);
    let body;
    if (url === '/api/files') body = { files: [] };
    else if (url === '/api/prepare') body = { ok: true, ...cp };
    else body = { ok: true, kind: 'integer_multiplication', result: {
      product: '408', product_digits: 3, a_digits: 2, b_digits: 2, ms: 1,
      schoolbook_ms: 1, match: true, omitted: 0, steps: [structuredClone(middle), structuredClone(answer)] } };
    return { ok: true, json: async () => body };
  } };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(__dirname + '/q4_ui.js', 'utf8'), sandbox);
(async () => {
  await new Promise(resolve => setImmediate(resolve));
  await vm.runInContext('selectFile("points.txt")', sandbox);
  assert.equal(calls.includes('/api/run'), false, 'Selecting input must not run the algorithm');
  assert.equal(vm.runInContext('state.result', sandbox), null);
  assert.equal(nodes.get('run').disabled, false);
  sandbox.inputFixture = integer;
  vm.runInContext('showInput(inputFixture, "12\\n34")', sandbox);
  await vm.runInContext('run(state.loaded.name)', sandbox);
  assert.equal(nodes.get('product').textContent, '', 'Product stays hidden at the start');
  assert.equal(vm.runInContext('state.index', sandbox), 0);
  assert.ok(ticks, 'Run starts playback');
  ticks();
  assert.equal(nodes.get('product').textContent, '', 'Final product stays hidden at intermediate step');
  ticks();
  assert.equal(nodes.get('product').textContent, '408');
  assert.equal(nodes.get('copy').disabled, false);
  assert.equal(ticks, null, 'Playback stops at the answer');
  vm.runInContext('goto(1)', sandbox);
  assert.equal(nodes.get('product').textContent, '', 'Stepping back hides the final answer again');
  assert.equal(nodes.get('copy').disabled, true);
  await vm.runInContext('selectFile("points.txt")', sandbox);
  assert.equal(nodes.get('product').textContent, '', 'Changing inputs clears results');
  assert.equal(vm.runInContext('state.steps.length', sandbox), 0);
  console.log('UI checks passed: input-only loading, playback, final reveal, stepping back, and reset.');
})().catch(error => { console.error(error); process.exitCode = 1; });
