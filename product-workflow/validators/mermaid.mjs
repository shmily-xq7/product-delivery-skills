import { JSDOM } from 'jsdom';
const dom = new JSDOM('');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
const { default: mermaid } = await import('mermaid');
mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' });
let input = '';
for await (const chunk of process.stdin) input += chunk;
try {
  const blocks = JSON.parse(input);
  const results = [];
  for (const text of blocks) {
    try { await mermaid.parse(text); results.push({ ok: true }); }
    catch (error) { results.push({ ok: false, error: String(error.message).slice(0, 800) }); }
  }
  process.stdout.write(JSON.stringify(results));
} catch (error) {
  process.stderr.write(String(error)); process.exitCode = 2;
}
