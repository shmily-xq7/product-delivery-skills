import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const localModules = new URL('./node_modules/', import.meta.url);
let modules = localModules;
if (!existsSync(new URL('mermaid/package.json', localModules))) {
  const configured = process.env.PRODUCT_DIAGRAM_NODE_MODULES;
  if (!configured) throw new Error('缺少图表运行依赖，请通过安装器重新安装 product-diagram');
  modules = pathToFileURL(resolve(configured) + '/');
}
const { JSDOM } = await import(new URL('jsdom/lib/api.js', modules));

const dom = new JSDOM('<!doctype html><html><body><div id="diagram-root"></div></body></html>', {
  pretendToBeVisual: true,
});
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.Element = dom.window.Element;
globalThis.HTMLElement = dom.window.HTMLElement;
globalThis.SVGElement = dom.window.SVGElement;

// The server-side DOM has no layout engine, so use stable text estimates.
// Readability is verified separately by opening the generated artifact.
dom.window.SVGElement.prototype.getBBox = function () {
  const size = Number.parseFloat(this.getAttribute?.('font-size') || '14') || 14;
  const text = (this.textContent || '').trim();
  return { x: 0, y: 0, width: Math.max(size, Array.from(text).length * size * 0.62), height: size * 1.25 };
};
dom.window.SVGElement.prototype.getComputedTextLength = function () {
  return this.getBBox().width;
};

const { default: mermaid } = await import(new URL('mermaid/dist/mermaid.esm.mjs', modules));
mermaid.initialize({
  startOnLoad: false,
  securityLevel: 'strict',
  theme: 'base',
  themeVariables: {
    background: '#ffffff',
    primaryColor: '#eef2ff',
    primaryTextColor: '#172033',
    primaryBorderColor: '#5670b8',
    lineColor: '#526078',
    secondaryColor: '#f5f7fa',
    tertiaryColor: '#ffffff',
    fontFamily: 'Arial, "PingFang SC", "Microsoft YaHei", sans-serif',
  },
});

let input = '';
for await (const chunk of process.stdin) input += chunk;

function xmlText(value) {
  return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
}

async function renderDiagram(request) {
  const id = String(request.id || 'diagram').replace(/[^A-Za-z0-9_-]/g, '_');
  const title = xmlText(request.title || id);
  const description = xmlText(request.description || `Diagram: ${request.title || id}`);
  const host = document.getElementById('diagram-root');
  host.innerHTML = '';
  const result = await mermaid.render(id, String(request.text || ''), host);
  const openEnd = result.svg.indexOf('>');
  if (openEnd < 0) throw new Error('渲染结果缺少 SVG 根元素');
  let opening = result.svg.slice(0, openEnd);
  opening = opening.replace(/\srole="[^"]*"/g, '').replace(/\saria-labelledby="[^"]*"/g, '');
  const labelled = `${opening} role="img" aria-labelledby="${id}-title ${id}-desc">`;
  const body = result.svg.slice(openEnd + 1);
  return `${labelled}<title id="${id}-title">${title}</title><desc id="${id}-desc">${description}</desc>${body}`;
}

try {
  const request = JSON.parse(input);
  if (!request || request.action !== 'render') throw new Error('输入必须是 render 请求');
  const svg = await renderDiagram(request);
  process.stdout.write(JSON.stringify({ ok: true, svg }));
} catch (error) {
  process.stdout.write(JSON.stringify({ ok: false, error: String(error.message).slice(0, 1200) }));
  process.exitCode = 1;
}
