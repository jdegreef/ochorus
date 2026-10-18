import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
	catalogueImports,
	checkBudgets,
	closure,
	layoutCss,
	measure,
	staticImports,
	suggest
} from '../../scripts/check-bundle-budget.mjs';

describe('staticImports', () => {
	it('finds static imports, side-effect imports and re-exports', () => {
		const src =
			'import{a as b}from"../chunks/A.js";import * as n from "./B.js";import"./C.js";' +
			'export{x as y}from"./D.js";export * from \'./E.js\';';
		expect(staticImports(src)).toEqual([
			'../chunks/A.js',
			'./B.js',
			'./C.js',
			'./D.js',
			'./E.js'
		]);
	});

	it('ignores dynamic import(), import.meta and bare specifiers', () => {
		const src =
			'const l=()=>import(`./Lazy.js`);const m=()=>import("./Lazy2.js");' +
			'new URL("./x.js",import.meta.url);import{s}from"svelte";reimport"./no.js"';
		expect(staticImports(src)).toEqual([]);
	});
});

describe('closure + measure on a tiny build', () => {
	let root = '';
	const put = (file: string, src: string) => {
		mkdirSync(join(root, file, '..'), { recursive: true });
		writeFileSync(join(root, file), src);
	};

	beforeAll(() => {
		root = mkdtempSync(join(tmpdir(), 'budget-'));
		put(
			'entry/app.X1.js',
			'const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["/_app/immutable/nodes/0.L.js","/_app/immutable/assets/0.G.css","/_app/immutable/assets/fonts-ko.K.css","/_app/immutable/assets/Other.O.css"])))=>i.map(i=>d[i]);' +
				'import{t}from"../chunks/shared.js";' +
				'var W=[()=>T(()=>import(`../nodes/0.L.js`),__vite__mapDeps([0,1,2]),import.meta.url)];'
		);
		put('entry/start.S1.js', 'export{a as start}from"../chunks/kit.js";');
		put('nodes/0.L.js', 'import{x}from"../chunks/i18n.js";import"../chunks/shared.js";');
		put('nodes/1.P.js', 'import"../chunks/page-only.js";');
		put('chunks/shared.js', 'export const t=1;');
		put('chunks/kit.js', 'import"./shared.js";export const a=2;');
		put(
			'chunks/i18n.js',
			'export const x=Object.assign({"/messages/en.json":()=>e(()=>import(`./en.js`).then(e=>e.default),[],import.meta.url),' +
				'"/messages/es.json":()=>e(()=>import(`./es.js`).then(e=>e.default),[],import.meta.url)});'
		);
		put('chunks/en.js', 'var e={a:`hello`};export{e as default};');
		put('chunks/es.js', `import"./shared.js";var e={a:\`${'hola '.repeat(400)}\`};export{e as default};`);
		put('chunks/page-only.js', 'x'.repeat(5000));
		put('assets/0.G.css', 'body{color:red}');
		put('assets/fonts-ko.K.css', '@font-face{}'.repeat(100));
		put('assets/Other.O.css', '.never{}');
	});
	afterAll(() => rmSync(root, { recursive: true, force: true }));

	it('walks static imports only, from the entry and the layout node', () => {
		const files = closure(
			['entry/app.X1.js', 'entry/start.S1.js', 'nodes/0.L.js'],
			(f: string) => readFileSync(join(root, f), 'utf8')
		);
		expect([...files].sort()).toEqual([
			'chunks/i18n.js',
			'chunks/kit.js',
			'chunks/shared.js',
			'entry/app.X1.js',
			'entry/start.S1.js',
			'nodes/0.L.js'
		]);
	});

	it('measures each metric', () => {
		const m = measure(root);
		expect(m.entryClosure.files.map((f) => f.file)).not.toContain('chunks/en.js');
		expect(m.entryClosure.files.map((f) => f.file)).not.toContain('nodes/1.P.js');
		expect(m.largestChunk.label).toBe('chunks/page-only.js');
		expect(m.largestChunk.raw).toBe(5000);
		// es is biggest; its shared.js import is already in the entry closure, so not counted.
		expect(m.largestCatalogue.label).toBe('es');
		expect(m.largestCatalogue.files[0].file).toBe('es: chunks/es.js');
		// fonts-ko and CSS not in the layout's deps are excluded.
		expect(m.globalCss.files.map((f) => f.file)).toEqual(['assets/0.G.css']);
		expect(m.globalCss.raw).toBe('body{color:red}'.length);
	});

	it('passes within budget and names the metric and culprits when over', () => {
		const m = measure(root);
		expect(checkBudgets(m, suggest(m))).toEqual([]);
		const tight = { ...suggest(m), largestChunk: { raw: 100, gzip: 1_000_000 } };
		const failures = checkBudgets(m, tight);
		expect(failures).toHaveLength(1);
		expect(failures[0]).toMatch(/^largestChunk \(raw\) \[chunks\/page-only\.js\]: 4\.9 KB > budget 0\.1 KB/);
		expect(failures[0]).toContain('chunks/page-only.js');
		expect(checkBudgets(m, {})[0]).toMatch(/no budget/);
	});
});

describe('catalogueImports / layoutCss', () => {
	it('reads the locale → module map', () => {
		const src =
			'{"/messages/am.json":()=>e(()=>import(`./A.js`).then(e=>e.default),[],import.meta.url),"/messages/pt-BR.json":()=>e(()=>import("./B.js"))}';
		expect(catalogueImports(src)).toEqual({ am: './A.js', 'pt-BR': './B.js' });
	});

	it('returns null when the preload map is missing', () => {
		expect(layoutCss('import"./x.js"')).toBeNull();
	});
});

describe('suggest', () => {
	it('adds 15% and rounds up to the KB', () => {
		expect(suggest({ a: { raw: 1024 * 100, gzip: 1000, files: [] } })).toEqual({
			a: { raw: 1024 * 115, gzip: 2048 }
		});
	});
});
