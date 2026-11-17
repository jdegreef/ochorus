/**
 * Draw a share card for every prerendered READING PLAN page, in every language.
 *
 * Runs as `postbuild`, after the quote cards:
 *
 *     npm run build                                  # vite build, then every card
 *     node scripts/build-plan-cards.mjs [buildDir]   # by hand; default ./build
 *
 * WHAT IT IS
 * Every plan used to share the one generic `/og/plans.png`. Its card is now the
 * plan's own: its title, where day 1 begins, a gold badge with its length and
 * minutes a day, and its books standing on the ledge the home card uses — so a
 * shared plan reads as "this many days, these books, start here".
 *
 * Plans are per-language rows, so the card is drawn in the page's language,
 * right-to-left for Arabic, from strings the plan pages already use ("Day",
 * "days", "min/day", and the plans tagline as its footer). A page whose plan
 * fell back to another language names that language's card instead of one
 * mixing two languages, so it is not drawn here. Drawn with Pango through `card-kit.mjs`, from the plan
 * response each page inlines; covers are each edition's `shareImage`.
 */
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { shareImage } from '../src/lib/coverArt.ts';
import { minutesPerDay, planCardUrl, planData } from '../src/lib/planCard.ts';
import {
	BADGE,
	INK,
	JPEG,
	MUTED,
	SANS,
	SERIF,
	W,
	drawAll,
	esc,
	paper,
	runAsScript,
	sharp,
	text,
	wordmark,
	UPRIGHT,
	badge,
	ledge,
	shelf
} from './card-kit.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const LOCALES = JSON.parse(
	readFileSync(resolve(HERE, '../project.inlang/settings.json'), 'utf8')
).locales;

const RTL = new Set(['ar']);
/** Scripts with no italic of their own — see build-author-cards. */

const TITLE_W = 820;

// ── Pieces ──────────────────────────────────────────────────────────────────

/** The largest size at which the title fits two lines. */
async function titleBlock(title, rtl) {
	let block;
	for (const size of [54, 48, 42, 38]) {
		block = await text(
			`<span font_desc="${SERIF} Semi-Bold ${size}" foreground="${INK}">${esc(title)}</span>`,
			{ width: TITLE_W, rtl }
		);
		if (block.height <= size * 2.6) return block;
	}
	return block;
}

// ── One card ────────────────────────────────────────────────────────────────

async function draw(locale, plan, msg, build) {
	const rtl = RTL.has(locale);
	const upright = UPRIGHT.has(locale);
	const mark = await wordmark(400);
	const title = await titleBlock(plan.title, rtl);
	const parts = [
		{ input: mark.data, left: rtl ? W - 72 - mark.width : 72, top: 58 },
		{ input: title.data, left: rtl ? W - 72 - title.width : 72, top: 100 }
	];

	const first = plan.day_one?.chapter_title;
	if (first) {
		const chapter = first.length > 70 ? `${first.slice(0, first.lastIndexOf(' ', 70))}…` : first;
		const day = await text(
			`<span font_desc="${SANS} Medium 21" foreground="#4a4035">${esc(msg.plans_day)} 1 · </span>` +
				`<span font_desc="${SERIF} ${upright ? '' : 'Italic'} 21" foreground="#4a4035">${esc(chapter)}</span>`,
			{ width: TITLE_W, rtl }
		);
		parts.push({
			input: day.data,
			left: rtl ? W - 72 - day.width : 72,
			top: 100 + title.height + 10
		});
	}

	const perDay = minutesPerDay(plan);
	parts.push({
		input: await badge(locale, plan.day_count, msg.plans_days, perDay ? `~${perDay} ${msg.plans_min_per_day}` : ''),
		left: rtl ? 72 : W - 72 - BADGE.d,
		top: BADGE.top
	});

	const files = (plan.covers ?? [])
		.map(
			(c) => shareImage({ slug: c.slug, language: c.language, cover_url: c.cover_url || '' })?.url
		)
		.filter((url) => url && /\.(jpe?g|png)$/.test(url))
		.map((url) => join(build, url))
		.filter(existsSync);
	parts.push(...(await shelf(files)), await ledge());

	const foot = await text(
		`<span font_desc="${SANS} Medium 19" foreground="${MUTED}">${esc(msg.plans_tagline)} · ochorus.com</span>`,
		{ width: W - 144, rtl }
	);
	parts.push({ input: foot.data, left: rtl ? W - 72 - foot.width : 72, top: 582 });

	// The kit's paper; its footer rule sits under the ledge.
	return sharp(paper()).composite(parts).jpeg(JPEG).toBuffer();
}

// ── Reading the build ───────────────────────────────────────────────────────

/** Every prerendered plan page, with the locale its path names. */
function planPages(build) {
	const found = [];
	for (const locale of LOCALES) {
		const root = locale === 'en' ? join(build, 'plans') : join(build, locale, 'plans');
		if (!existsSync(root)) continue;
		for (const slug of readdirSync(root)) {
			const file = join(root, slug, 'index.html');
			if (existsSync(file)) found.push({ locale, slug, file });
		}
	}
	return found;
}

async function main(build) {
	const messages = Object.fromEntries(
		LOCALES.map((l) => [
			l,
			JSON.parse(readFileSync(resolve(HERE, `../messages/${l}.json`), 'utf8'))
		])
	);
	// A page whose plan fell back to another language names THAT language's
	// card (see the plan page), so it needs none of its own.
	const jobs = planPages(build)
		.map((p) => ({ ...p, data: planData(readFileSync(p.file, 'utf8')) }))
		.filter((p) => !p.data || p.data.language === p.locale)
		.map((p) => ({ ...p, dest: planCardUrl(p.slug, p.locale), label: `${p.locale}/${p.slug}` }));
	await drawAll('build-plan-cards', build, jobs, async ({ locale, data }) => {
		if (!data) throw new Error('no plan data inlined in the page');
		return draw(locale, data.plan, messages[locale], build);
	});
}

await runAsScript(import.meta.url, 'build-plan-cards', main);
