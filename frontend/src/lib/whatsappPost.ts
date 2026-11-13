import type { TodayPicks } from '$lib/todayPicks';

/**
 * The day's post for an Ochorus WhatsApp channel, composed in the admin
 * (/admin/whatsapp) so running a channel is a copy and a paste each morning:
 * the date, the verse, the chapter of the day, today's devotional reading and
 * the sermon of the day
 * (the home Today card's picks, $lib/todayPicks), each with a plain link.
 *
 * WhatsApp's own markup: *bold*, _italic_, and URLs bare on their own line so
 * the app links them (and previews the first). There is no escaping in that
 * markup, so the marker characters are taken out of the text set inside them.
 * A pick the language doesn't have leaves its block out.
 */
export interface WhatsAppPostInput {
	/** The day as a reader of that language writes it ("Wednesday, 11 November"). */
	date: string;
	picks: TodayPicks;
	/** The section labels in the post's language. */
	labels: { reading: string; sermon: string; chapter: string };
	/** An absolute ochorus.com URL for a site path, in the post's language. */
	href: (path: string) => string;
}

/** Text that sits inside a `*…*` or `_…_` span: its own markers would end it. */
const plain = (s: string) => s.replace(/[*_~`]/g, '').replace(/\s+/g, ' ').trim();

export function whatsappPost({ date, picks, labels, href }: WhatsAppPostInput): string {
	const blocks: string[] = [`*${plain(date)}*`];
	if (picks.verse) blocks.push(`_${plain(picks.verse.text)}_\n${picks.verse.ref}`);
	if (picks.chapter) {
		const c = picks.chapter;
		blocks.push(`*${plain(labels.chapter)}:* ${c.title}\n${href(`${c.href}/`)}`);
	}
	if (picks.reading) {
		const r = picks.reading;
		const title = r.heading ? `${r.heading} (${r.book.title})` : r.book.title;
		blocks.push(`*${plain(labels.reading)}:* ${title} — ${r.book.author.name}\n${href(`/today/${r.book.slug}/`)}`);
	}
	if (picks.sermon) {
		const s = picks.sermon;
		blocks.push(`*${plain(labels.sermon)}:* ${s.title} — ${s.author.name}\n${href(`/sermons/${s.slug}/`)}`);
	}
	return blocks.join('\n\n');
}
