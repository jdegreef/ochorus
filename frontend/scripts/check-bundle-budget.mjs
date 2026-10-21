#!/usr/bin/env node
/**
 * Fail the build when the JavaScript / CSS every page pays for grows past its
 * budget (bundle-budget.json). The history, briefly: a 1.4 MB all-locales i18n
 * chunk rode along on every page and Search Console marked all 578 URLs "poor"
 * on mobile INP (244 ms) — nothing caught it because nothing measured it.
 *
 *   node scripts/check-bundle-budget.mjs                         # build/_app/immutable
 *   node scripts/check-bundle-budget.mjs build-app/_app/immutable
 *   node scripts/check-bundle-budget.mjs <dir> --suggest         # measured + 15%, as JSON
 *
 * What it measures (raw and gzip bytes):
 *   entryClosure      the STATIC-import closure of entry/app + entry/start + the
 *                     root layout node (nodes/0) — what every page downloads,
 *                     parses and runs before it can answer a tap. Dynamic
 *                     import() is lazy and deliberately not followed.
 *   largestChunk      the biggest single .js file anywhere in the output.
 *   largestCatalogue  the biggest per-locale UI catalogue (the lazy
 *                     `/messages/<locale>.json` modules in the i18n loader's
 *                     import map), plus anything it pulls in that the entry
 *                     closure doesn't already hold.
 *   globalCss         the CSS the layout node preloads (every page), minus
 *                     the on-demand font sheets ($lib/fonts-<locale>.css,
 *                     fonts-reader.css), which load only where they are drawn.
 *
 * Raising a budget is allowed — deliberately: edit bundle-budget.json and say
 * in the PR why the bytes are worth it.
 */

import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { dirname, join, normalize, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { gzipSync } from 'node:zlib';

/** @typedef {{ raw: number, gzip: number }} Size */
/** @typedef {{ file: string, raw: number, gzip: number }} FileSize */
/** @typedef {Size & { files: FileSize[], label?: string }} Metric */
/** @typedef {Record<string, Metric>} Metrics */

/**
 * Relative specifiers of a module's STATIC imports and re-exports:
 * `import {a} from "./x.js"`, `import * as n from "./x.js"`, `import "./x.js"`,
 * `export {a} from "./x.js"`, `export * from "./x.js"`. Static specifiers are
 * always "…" or '…'; the bundler writes dynamic `import(`./x.js`)` with a
 * paren (and usually backticks), which the pattern never matches.
 * @param {string} src
 * @returns {string[]}
 */
export function staticImports(src) {
	const re =
		/(?<![\w$.])(?:import|export)\s*(?:[\w$*{},\s]*?\s*from\s*)?["'](\.{1,2}\/[^"'\n]+?\.js)["']/g;
	return [...src.matchAll(re)].map((m) => m[1]);
}

/**
 * Every file reachable from `starts` by static imports (paths relative to the
 * output root, forward slashes).
 * @param {string[]} starts
 * @param {(file: string) => string} read
 * @returns {Set<string>}
 */
export function closure(starts, read) {
	/** @type {Set<string>} */
	const seen = new Set();
	const walk = (/** @type {string} */ file) => {
		if (seen.has(file)) return;
		seen.add(file);
		for (const spec of staticImports(read(file))) {
			walk(normalize(join(dirname(file), spec)).replaceAll('\\', '/'));
		}
	};
	starts.forEach(walk);
	return seen;
}

/**
 * The lazy per-locale catalogue modules from the i18n loader's import map:
 * `"/messages/es.json": () => e(() => import(`./Ab12.js`)…)` → { es: './Ab12.js' }.
 * @param {string} src
 * @returns {Record<string, string>}
 */
export function catalogueImports(src) {
	const re =
		/["'`]\/messages\/([\w-]+)\.json["'`]\s*:\s*\(\)\s*=>[^,]{0,200}?import\(\s*["'`](\.{1,2}\/[^"'`]+\.js)["'`]/g;
	/** @type {Record<string, string>} */
	const out = {};
	for (const m of src.matchAll(re)) out[m[1]] = m[2];
	return out;
}

/**
 * CSS the app entry preloads alongside the root layout node — rolldown/vite
 * write `import(`../nodes/0.X.js`),__vite__mapDeps([6,1,…])` against a shared
 * `m.f=[…]` path list. Returns paths relative to the output root.
 * @param {string} appSrc
 * @returns {string[] | null} null when the pattern isn't there (caller falls back)
 */
export function layoutCss(appSrc) {
	const call = appSrc.match(
		/import\(\s*["'`]\.\.\/nodes\/0\.[^"'`]+\.js["'`]\s*\)\s*,\s*__vite__mapDeps\(\s*\[([\d,\s]*)\]/
	);
	const list = appSrc.match(/m\.f\s*=\s*\[([^\]]*)\]/);
	if (!call || !list) return null;
	const paths = [...list[1].matchAll(/["'`]([^"'`]+)["'`]/g)].map((m) => m[1]);
	return call[1]
		.split(',')
		.filter((s) => s.trim() !== '')
		.map((i) => paths[Number(i)])
		.filter((p) => p && p.endsWith('.css'))
		.map((p) => p.replace(/^.*?immutable\//, ''));
}

/** @param {Buffer} buf @returns {Size} */
const sizeOf = (buf) => ({ raw: buf.length, gzip: gzipSync(buf, { level: 9 }).length });

/**
 * @param {string} root
 * @param {Iterable<string>} files
 * @param {string} [label]
 * @returns {Metric}
 */
function sumFiles(root, files, label) {
	const list = [...files].map((file) => ({ file, ...sizeOf(readFileSync(join(root, file))) }));
	list.sort((a, b) => b.raw - a.raw);
	return {
		raw: list.reduce((n, f) => n + f.raw, 0),
		gzip: list.reduce((n, f) => n + f.gzip, 0),
		files: list,
		...(label ? { label } : {})
	};
}

/** @param {string} dir @returns {string[]} */
const ls = (dir) => (existsSync(dir) ? readdirSync(dir) : []);

/**
 * Measure an `_app/immutable` directory.
 * @param {string} root
 * @returns {Metrics}
 */
export function measure(root) {
	const read = (/** @type {string} */ f) => readFileSync(join(root, f), 'utf8');
	const entry = ls(join(root, 'entry'));
	const app = entry.find((f) => /^app\..*\.js$/.test(f));
	const layout = ls(join(root, 'nodes')).find((f) => /^0\..*\.js$/.test(f));
	if (!app || !layout) {
		throw new Error(
			`${root} has no entry/app.*.js or nodes/0.*.js — is this a SvelteKit _app/immutable dir?`
		);
	}
	const starts = [
		`entry/${app}`,
		...entry.filter((f) => /^start\..*\.js$/.test(f)).map((f) => `entry/${f}`),
		`nodes/${layout}`
	];
	const entryFiles = closure(starts, read);
	const entryClosure = sumFiles(root, entryFiles);

	const allJs = ['entry', 'nodes', 'chunks'].flatMap((d) =>
		ls(join(root, d))
			.filter((f) => f.endsWith('.js'))
			.map((f) => `${d}/${f}`)
	);
	const chunks = sumFiles(root, allJs);
	const top = chunks.files[0];
	const largestChunk = {
		raw: top?.raw ?? 0,
		gzip: top?.gzip ?? 0,
		files: chunks.files.slice(0, 5),
		label: top?.file
	};

	const loader = allJs.find((f) => read(f).includes('"/messages/en.json"'));
	if (!loader) throw new Error('no chunk holds "/messages/en.json" — did the i18n loader move?');
	const catalogues = Object.entries(catalogueImports(read(loader))).map(([locale, spec]) => {
		const file = normalize(join(dirname(loader), spec)).replaceAll('\\', '/');
		const own = [...closure([file], read)].filter((f) => !entryFiles.has(f));
		return sumFiles(root, own, locale);
	});
	if (catalogues.length === 0) throw new Error(`${loader}: no /messages/<locale>.json imports found`);
	catalogues.sort((a, b) => b.raw - a.raw);
	const biggest = catalogues[0];
	const largestCatalogue = {
		raw: biggest.raw,
		gzip: biggest.gzip,
		label: biggest.label,
		files: catalogues.slice(0, 5).map((c) => ({ file: `${c.label}: ${c.files[0]?.file}`, raw: c.raw, gzip: c.gzip }))
	};

	const css =
		layoutCss(read(`entry/${app}`)) ??
		ls(join(root, 'assets'))
			.filter((f) => /^0\..*\.css$/.test(f))
			.map((f) => `assets/${f}`);
	const globalCss = sumFiles(
		root,
		css.filter((f) => !/\/fonts-[a-z]+\./.test(f) && existsSync(join(root, f)))
	);

	return { entryClosure, largestChunk, largestCatalogue, globalCss };
}

/** @param {number} n */
const kb = (n) => `${(n / 1024).toFixed(1)} KB`;

/**
 * Compare metrics with budgets. Returns one message per breach (empty = pass).
 * @param {Metrics} metrics
 * @param {Record<string, unknown>} budgets
 * @returns {string[]}
 */
export function checkBudgets(metrics, budgets) {
	/** @type {string[]} */
	const failures = [];
	for (const [name, metric] of Object.entries(metrics)) {
		const budget = /** @type {Partial<Size> | undefined} */ (budgets[name]);
		if (!budget) {
			failures.push(`${name}: no budget in bundle-budget.json — add one (see --suggest).`);
			continue;
		}
		for (const kind of /** @type {const} */ (['raw', 'gzip'])) {
			const limit = budget[kind];
			if (typeof limit !== 'number' || metric[kind] <= limit) continue;
			const culprits = metric.files
				.slice(0, 5)
				.map((f) => `      ${kb(f.raw).padStart(9)} raw  ${kb(f.gzip).padStart(9)} gz  ${f.file}`)
				.join('\n');
			failures.push(
				`${name} (${kind})${metric.label ? ` [${metric.label}]` : ''}: ${kb(metric[kind])} > budget ${kb(limit)} (+${kb(metric[kind] - limit)})\n` +
					`    biggest files:\n${culprits}`
			);
		}
	}
	return failures;
}

/**
 * Budgets with headroom over what was measured — for setting or deliberately
 * raising bundle-budget.json.
 * @param {Metrics} metrics
 * @param {number} [headroom]
 */
export function suggest(metrics, headroom = 0.15) {
	/** @type {Record<string, Size>} */
	const out = {};
	for (const [name, m] of Object.entries(metrics)) {
		out[name] = {
			raw: Math.ceil((m.raw * (1 + headroom)) / 1024) * 1024,
			gzip: Math.ceil((m.gzip * (1 + headroom)) / 1024) * 1024
		};
	}
	return out;
}

function main() {
	const args = process.argv.slice(2);
	const here = dirname(fileURLToPath(import.meta.url));
	const dir = resolve(args.find((a) => !a.startsWith('--')) ?? join(here, '..', 'build/_app/immutable'));
	const metrics = measure(dir);

	if (args.includes('--suggest')) {
		console.log(JSON.stringify(suggest(metrics), null, '\t'));
		return;
	}

	const budgetFile = join(here, '..', 'bundle-budget.json');
	const budgets = JSON.parse(readFileSync(budgetFile, 'utf8'));
	console.log(`Bundle budget — ${relative(process.cwd(), dir) || dir}`);
	for (const [name, m] of Object.entries(metrics)) {
		const b = budgets[name] ?? {};
		console.log(
			`  ${name.padEnd(17)} ${kb(m.raw).padStart(10)} raw (budget ${b.raw ? kb(b.raw) : '—'})  ` +
				`${kb(m.gzip).padStart(9)} gz (budget ${b.gzip ? kb(b.gzip) : '—'})` +
				(m.label ? `  ${m.label}` : '')
		);
	}

	const failures = checkBudgets(metrics, budgets);
	if (failures.length === 0) {
		console.log('✓ within budget');
		return;
	}
	console.error(`\n✗ bundle over budget:\n\n${failures.map((f) => `  ${f}`).join('\n\n')}\n`);
	console.error(
		'Every page downloads, parses and runs these bytes before it can answer a tap — this is\n' +
			'how mobile INP regressed before (see _why in bundle-budget.json). Usually the fix is a\n' +
			'dynamic import() or moving code out of the root layout. If the growth is worth it, raise\n' +
			'the budget deliberately: edit frontend/bundle-budget.json (`--suggest` prints measured +15%)\n' +
			'and say why in the PR description.\n'
	);
	process.exitCode = 1;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) main();
