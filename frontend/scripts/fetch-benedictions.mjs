#!/usr/bin/env node
/**
 * Regenerates src/lib/benediction.generated.ts: the footer's closing blessings,
 * one per season of the Church year, VERBATIM from each locale's own Bible on
 * Take Root (the `bible` code backend/library/language_seed.py names). English
 * is the exception: it quotes the Open Word Bible (Balanced, CC0) the reader's
 * Scripture popover uses, read from the copy the backend bundles
 * (backend/library/data/bible/owb-en-b.json.gz, scripts/build_owb_bible.py).
 *
 * Scripture is never ours to write, so this is the only way the text gets in.
 * Run it by hand when a Bible or a locale changes, review the diff, commit:
 *
 *   node scripts/fetch-benedictions.mjs
 *   node scripts/fetch-benedictions.mjs --only en   # one locale; the rest kept as they are
 *
 * The only edits made to the API's text: the speech marks some editions wrap
 * round a quoted verse are trimmed (each blessing stands alone here), the
 * French mirror's stray spaces around apostrophes are closed up, and the
 * Vietnamese mirror's capital Đ (sent as Ð, U+00D0) is repaired — the same
 * repair backend/library/translation.fetch_chapter makes.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { gunzipSync } from 'node:zlib';

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, '..', 'src', 'lib', 'benediction.generated.ts');
const OWB = join(HERE, '..', '..', 'backend', 'library', 'data', 'bible', 'owb-en-b.json.gz');
const API = 'https://api.takeroot.bible/api/bible';

/** locale → Take Root code (mirrors language_seed.py). */
const BIBLES = {
	en: 'owb-en-b',
	es: 'rv1858',
	sw: 'swhonen',
	lg: 'lug',
	pt: 'porbrbsl',
	ar: 'arb-vd',
	hi: 'irvhin',
	uk: 'ukr-kul',
	fr: 'fralsg',
	am: 'am-ulb',
	vi: 'vietnamese',
	ko: 'korean'
};

/**
 * The blessings. `verses` names KJV numbering; `last` takes the chapter's
 * final N verses instead, for a passage whose numbering differs between
 * Bibles (2 Corinthians 13's grace is v14 in the KJV, v13 in many others).
 */
const PASSAGES = {
	aaronic: { usfm: 'NUM', chapter: 6, verses: [24, 25, 26] },
	hope: { usfm: 'ROM', chapter: 15, verses: [13] },
	keep: { usfm: 'JUD', chapter: 1, last: 2 },
	shepherd: { usfm: 'HEB', chapter: 13, verses: [20, 21] },
	grace: { usfm: '2CO', chapter: 13, last: 1 }
};

const QUOTES = /^[\s“”‘’"]+|[\s“”‘’"]+$/g;
// OWB English quotes with straight marks: Numbers 6:26 closes on ."' (the
// Lord's speech, then Moses').
const STRAIGHT = /^[\s“”‘’"']+|[\s“”‘’"']+$/g;

function clean(text, locale) {
	let s = text.replace(locale === 'en' ? STRAIGHT : QUOTES, '');
	if (locale === 'fr') s = s.replace(/’ /g, '’').replace(/ ’/g, '’');
	if (locale === 'vi') s = s.replace(/Ð/g, 'Đ');
	return s.replace(/\s{2,}/g, ' ');
}

/** The bundled Open Word Bible, as Take Root shapes a chapter. */
const OWB_BOOKS = { NUM: [4, 'Numbers'], ROM: [45, 'Romans'], JUD: [65, 'Jude'], HEB: [58, 'Hebrews'], '2CO': [47, '2 Corinthians'] };
let owb;
function owbChapter(usfm, ch) {
	owb ??= JSON.parse(gunzipSync(readFileSync(OWB)).toString('utf-8')).verses;
	const [number, name] = OWB_BOOKS[usfm];
	const base = number * 1_000_000 + ch * 1000;
	// Every verse of the chapter, past any OWB lacks; a verse it prints joined
	// to the one before (Psalm 13:5-6) is that one's entry, as Take Root gives it.
	const verses = Object.keys(owb)
		.map(Number)
		.filter((id) => Math.floor(id / 1000) === base / 1000)
		.sort((a, b) => a - b)
		.map((id) => ({ number: id % 1000, text: owb[id] }));
	return { book_name: name, verses };
}

async function chapter(bible, usfm, ch) {
	if (bible === 'owb-en-b') return owbChapter(usfm, ch);
	const res = await fetch(`${API}/${bible}/${usfm}/${ch}/`, { signal: AbortSignal.timeout(20_000) });
	if (!res.ok) throw new Error(`${bible} ${usfm} ${ch}: HTTP ${res.status}`);
	return res.json();
}

function span(numbers) {
	return numbers.length === 1 ? `${numbers[0]}` : `${numbers[0]}–${numbers[numbers.length - 1]}`;
}

// `--only <locale>` refetches one locale and keeps every other as generated:
// Take Root is unreachable from some sessions, and the English text is local.
const only = process.argv.includes('--only') ? process.argv[process.argv.indexOf('--only') + 1] : null;
const out = only
	? JSON.parse(readFileSync(OUT, 'utf-8').replace(/^[\s\S]*?= /, '').replace(/ as const;\s*$/, ''))
	: {};
for (const [locale, bible] of Object.entries(BIBLES)) {
	if (only && locale !== only) continue;
	out[locale] = { bible };
	for (const [key, p] of Object.entries(PASSAGES)) {
		const data = await chapter(bible, p.usfm, p.chapter);
		const all = data.verses.map((v) => ({ n: Number(v.number), text: String(v.text).trim() }));
		const picked = p.last ? all.slice(-p.last) : all.filter((v) => p.verses.includes(v.n));
		// Some editions merge verses (am-ulb prints Hebrews 13:20–21 as one
		// entry numbered 20): a requested verse may be absent only when the
		// verse before it was printed, i.e. it was folded into that one.
		const ok = p.last
			? picked.length === p.last
			: picked[0]?.n === p.verses[0] &&
				p.verses.every((n, i) => all.some((v) => v.n === n) || (i > 0 && all.some((v) => v.n === p.verses[i - 1])));
		if (!ok || picked.some((v) => !v.text)) {
			throw new Error(`${locale} ${key}: verses missing (got ${picked.map((v) => v.n).join(', ')})`);
		}
		out[locale][key] = {
			book: String(data.book_name).trim(),
			// Jude is one chapter: cited by verse alone, as Bibles print it.
			passage: (() => {
				const nums = p.last ? picked.map((v) => v.n) : p.verses;
				return p.usfm === 'JUD' ? span(nums) : `${p.chapter}:${span(nums)}`;
			})(),
			text: picked.map((v) => clean(v.text, locale)).join(' ')
		};
	}
	console.log(`✓ ${locale} (${bible})`);
}

writeFileSync(
	OUT,
	`// GENERATED by scripts/fetch-benedictions.mjs — do not edit by hand.\n` +
		`// Verbatim from each locale's own Bible (Take Root; English: Open Word Bible); see that script.\n` +
		`export const BLESSINGS = ${JSON.stringify(out, null, '\t')} as const;\n`,
	'utf-8'
);
console.log(`wrote ${OUT}`);
