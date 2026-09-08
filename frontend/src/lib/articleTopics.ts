// SEO copy for a topic-filtered article shelf (`/articles/<topic>/`).
//
// The bare /articles index keeps the plain "Articles" heading; each topic view
// gets its own keyword-led H1 so the filtered page reads as a page about that
// subject rather than a duplicate of the index. The <title> is built from the
// H1 (`<h1> — Ochorus`, the site convention).
//
// Two pieces of prose, deliberately separate, because they serve two readers:
//   - `blurb` — one tight sentence, the META DESCRIPTION (and the JSON-LD
//     description). Kept ~150 chars so a crawler shows it whole, not truncated.
//   - `intro` — the visible STANDFIRST under the H1, 80–130 words, written for
//     the human who just landed. It is rendered in <ArticleTopicShelf> and
//     never feeds the crawl. Do not collapse the two: a 100-word meta
//     description is truncated in search, and a one-line standfirst wastes the
//     shelf's opening.
//
// The ten shelves are a curated set; a topic added later (the vocabulary is
// DB-owned) simply falls back to a template built from its chip title, so a new
// shelf is never wrong — only less tuned.
//
// DEBT: this is an English-only home for per-topic prose that the backend
// `Topic` model already owns a translatable form of (`Topic.description` +
// `TopicTranslation`). It is an acceptable first cut while articles are
// English-only, but when articles gain translations this copy must move to a
// translatable backend field (e.g. `Topic.article_h1` / `article_intro`) served
// through the API — this map cannot localize.

import type { ArticleSummary } from './library-public';
import { SITE_URL } from './config';
import { jsonLd } from './seo';

/** True when an article carries the given topic. `?? []` guards a lagging API
 *  that predates the `topics` field (version skew). Shared by the shelf filter,
 *  the topic page, and the legacy `?topic=` redirect so the predicate can't
 *  drift between them. */
export const articleHasTopic = (a: ArticleSummary, slug: string): boolean =>
	(a.topics ?? []).some((tc) => tc.slug === slug);

/** The `CollectionPage → hasPart → Article` JSON-LD both the index and each
 *  topic shelf emit, so the set reads as one entity to a crawler. One builder,
 *  not a copy per page (the shape intentionally differs from seo.ts's
 *  `collectionPage()` ItemList — an article collection lists Articles). */
export const articleCollectionLd = (
	name: string,
	description: string,
	url: string,
	articles: ArticleSummary[]
) =>
	jsonLd({
		'@context': 'https://schema.org',
		'@type': 'CollectionPage',
		name,
		description,
		url,
		hasPart: articles.map((a) => ({
			'@type': 'Article',
			headline: a.h1,
			url: `${SITE_URL}/articles/${a.slug}/`
		}))
	});

export interface ArticleTopicSeo {
	/** The visible <h1> for the shelf, and the stem of its <title>. */
	h1: string;
	/** One-sentence meta description (and JSON-LD description). Kept short so a
	 *  crawler shows it whole; NOT rendered on the page. */
	blurb: string;
	/** The visible standfirst under the H1 — 80–130 words, for the reader who
	 *  just arrived. Rendered as the shelf's standfirst; never fed to the crawl. */
	intro: string;
}

const CURATED: Record<string, ArticleTopicSeo> = {
	prayer: {
		h1: 'Articles on Prayer',
		blurb:
			'Short readings on prayer — how to pray, how to keep praying, and how to pray ' +
			'for others — each one sending you on to a classic on the life of prayer.',
		intro:
			'Prayer is the plainest thing in the Christian life and the hardest to keep ' +
			"up. These readings are for anyone who wants to pray and finds it difficult — " +
			"the beginner who doesn't know where to start, and the believer whose praying " +
			'has gone cold. You will find help on how to pray so God answers, how to keep ' +
			'going when heaven seems silent, and how to carry others to God. Each one is ' +
			'short, meant to be read in a few minutes, and each sends you on to a classic ' +
			'on prayer — Bounds, Murray, Ryle and others — worth reading slowly, in full, ' +
			'and free.'
	},
	'holy-spirit': {
		h1: 'Articles on the Holy Spirit',
		blurb:
			'Plain-spoken readings on the person and work of the Holy Spirit — his ' +
			'indwelling, his power, and the Spirit-filled Christian life.',
		intro:
			'The Holy Spirit is God himself at work in the believer, and the most ' +
			'misunderstood person of the Trinity. These plain-spoken readings return to ' +
			'what Scripture and the great teachers actually say about him: how he makes a ' +
			'person new, how he assures the heart, and how he fills an ordinary Christian ' +
			'with power for an ordinary life. No hype and no fear — just clear help on ' +
			'knowing the Spirit and walking with him day by day. Each reading is brief, ' +
			'and each points you on to a Christian classic on the Spirit-filled life, ' +
			'free to read in full.'
	},
	'deeper-life': {
		h1: 'Articles on the Deeper Christian Life',
		blurb:
			'Readings on abiding in Christ, surrender, and the deeper life with God — ' +
			'each one pointing you to a classic worth reading in full.',
		intro:
			'There is more to the Christian life than getting in the door. These readings ' +
			'are about the deeper life with God — abiding in Christ, surrender, and the ' +
			'daily death to self that older writers called the way of the cross. They are ' +
			'for the believer who senses that something is missing, who is tired of living ' +
			'on the surface and wants to go on with God. Nothing here is complicated; the ' +
			'deeper life is mostly a matter of trust and obedience. Each short reading ' +
			'opens the theme and sends you to a classic — Murray, Smith, Tozer and others ' +
			'— worth living with, free in full.'
	},
	'grace-and-comfort': {
		h1: 'Articles on Grace & Comfort',
		blurb:
			'Readings on the grace and comfort of God — for grief, guilt, fear and ' +
			'weariness — each one pointing you to a classic that has steadied believers ' +
			'for centuries.',
		intro:
			'When life caves in — grief, guilt, fear, exhaustion — the last thing you ' +
			'need is a lecture. These readings are gentle on purpose. They bring the grace ' +
			'and comfort of God to bear on the places that actually hurt: the loss that ' +
			"will not lift, the sin that will not let go, the anxiety that keeps you up at " +
			'night. They do not rush you or pretend the pain is not real; they point you ' +
			'to the God who meets his people there. Each one is short enough to read on a ' +
			'hard day, and each opens onto a classic that has steadied believers for ' +
			'centuries — free, in full.'
	},
	'revival-and-missions': {
		h1: 'Articles on Revival & Missions',
		blurb:
			'Readings on revival, repentance, and the call to reach the lost — and the ' +
			'classics that carried the gospel to the ends of the earth.',
		intro:
			'Revival is not a program or a passing feeling — it is God reviving his own ' +
			'people, and the overflow has always been mission. These readings look ' +
			'honestly at both: what genuine revival is and how it comes, why it always ' +
			'begins with repentance, and how the same fire has carried the gospel to the ' +
			'ends of the earth. They are for anyone who longs to see God move and wants to ' +
			'understand what to pray for and what to expect. Each short reading opens the ' +
			'theme and sends you on to a classic — Edwards, Finney, the great missionary ' +
			'lives — worth reading in full, free.'
	},
	'faith-and-guidance': {
		h1: 'Articles on Faith & Guidance',
		blurb:
			"Readings on trusting God and finding his will — how to hear his voice, wait " +
			'on him, and grow in faith through every season.',
		intro:
			"How do you trust God when you cannot see the road ahead? These readings are " +
			"about faith and guidance — hearing God's voice, waiting on him, and learning " +
			'to trust when the way is unclear. They are for the believer at a crossroads, ' +
			'and for anyone whose faith feels smaller than the decisions in front of them. ' +
			'You will not find formulas for reading providence like tea leaves; you will ' +
			'find older, wiser help on knowing God well enough to follow him. Each one is ' +
			'short, and each points you to a Christian classic on faith and the will of ' +
			'God, free to read in full.'
	},
	'the-gospel-call': {
		h1: 'Articles on the Gospel Call',
		blurb:
			'Readings on the heart of the gospel — being born again, assurance of ' +
			'salvation, and the oldest invitation there is.',
		intro:
			'Everything else on Ochorus rests on this. These readings return to the heart ' +
			'of the gospel — what it means to be born again, how a person can know they ' +
			'are saved, and the oldest invitation there is: come to Christ. They are ' +
			'written plainly for the seeker who is not sure what Christians actually ' +
			'believe, and for the long-time believer who needs to hear the good news again ' +
			'as good news. Nothing is assumed and nothing is watered down. Each short ' +
			'reading opens the theme and sends you on to a classic of the gospel call — ' +
			'Ryle, Spurgeon, Alleine and others — free, in full.'
	},
	'enduring-classics': {
		h1: 'Guides to the Enduring Christian Classics',
		blurb:
			"Reader's guides to the great Christian classics — what each book is about, " +
			'why it still matters, and how to begin.',
		intro:
			'Some books have outlived every generation that tried to bury them. These are ' +
			"reader's guides to the enduring Christian classics — the ones believers keep " +
			'coming back to across centuries. Each guide tells you what a book is actually ' +
			'about, why it still matters, and how to begin, so a title that once looked ' +
			'forbidding becomes a doorway. They are for anyone who has meant to read the ' +
			'great books and never known where to start. Read the guide in a few minutes, ' +
			'then open the classic itself — the whole work, free — and let a wiser, older ' +
			'voice do what only these books can.'
	},
	'the-way-of-holiness': {
		h1: 'Articles on the Way of Holiness',
		blurb:
			'Readings on holiness and the pursuit of a Christlike life — overcoming sin, ' +
			'walking in humility, and following Jesus closely.',
		intro:
			'Holiness has fallen out of fashion, and the church is poorer for it. These ' +
			'readings recover it — not as grim rule-keeping, but as the beauty of a ' +
			'Christlike life: overcoming besetting sin, walking in humility, and following ' +
			'Jesus closely enough that it costs something. They are for the believer who ' +
			'is tired of losing the same battles and wants to grow. The older writers are ' +
			'bracing and hopeful at once; they take sin seriously and grace more seriously ' +
			'still. Each short reading opens the theme and sends you on to a classic on ' +
			'holiness — Ryle, Bunyan, à Kempis and others — free, in full.'
	},
	'the-preached-word': {
		h1: 'Articles on Great Preaching',
		blurb:
			'Readings on the preached word and the sermons that shaped history — great ' +
			'preaching, and how to read it today.',
		intro:
			'For most of church history the sermon was the main event, and some sermons ' +
			'changed the world. These readings are about the preached word — the great ' +
			'preaching of the past and how to read it today. They open up why a sermon by ' +
			'Whitefield or Spurgeon still burns on the page, what made these preachers, ' +
			'and how ordinary readers can feast on preaching centuries later. They are for ' +
			'anyone who loves a strong sermon, and for preachers looking to sit at the ' +
			'feet of masters. Each short reading points you on to the sermons themselves — ' +
			'the full text, free — worth reading aloud.'
	}
};

/**
 * SEO copy for a topic shelf. Curated where we have it; otherwise a template
 * built from the localized chip title (`title`), so a DB-added topic still gets
 * a sensible, on-brand heading and intro without a code change (untuned, but
 * never wrong).
 */
export function articleTopicSeo(slug: string, title: string): ArticleTopicSeo {
	const curated = CURATED[slug];
	if (curated) return curated;
	// "The Gospel Call" → "the gospel call" for the mid-sentence prose.
	const lower = title.charAt(0).toLowerCase() + title.slice(1);
	return {
		h1: `Articles on ${title}`,
		blurb: `Short readings on ${lower} — each one pointing you to a Christian classic worth reading in full.`,
		intro:
			`Short, plain-spoken readings on ${lower} — written for the reader who wants ` +
			'to go deeper without wading through a whole volume first. Each one opens the ' +
			'theme in a few minutes and sends you on to a Christian classic worth reading ' +
			'in full, free.'
	};
}
