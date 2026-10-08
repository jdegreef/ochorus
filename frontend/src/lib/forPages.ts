import type { IconName } from '$lib/components/Icon.svelte';
import { toCoverBook, type BookSummary, type CoverBook } from './library-public';
import { LIVE_LOCALES } from './live-locales.generated';

/**
 * The "Ochorus for …" pages — one page per group we want to reach (churches,
 * homeschool families, parents), each saying what Ochorus is worth to THAT
 * reader and pointing into the library. Linked from the footer's bottom row.
 *
 * One route (`/for/[group]/`) renders every entry here, so a new group is a
 * new entry, not a new page. ENGLISH-ONLY for now, like the footer's Discover
 * hubs: this is pitch copy the founder is still shaping, and putting it into
 * ten catalogues before it settles would mean every edit lands ten times. So
 * the copy lives here as content, the footer row renders only for English
 * readers, and the pages advertise only an English URL (sitemap, hreflang).
 *
 * Keep every claim true of the live site. Nothing here mentions how a
 * translation was made — review state is admin-only (root CLAUDE.md).
 */

export interface ForLink {
	/** Unlocalized path, no trailing slash — the page applies `localizeHref`. */
	href: string;
	label: string;
}

export interface ForPoint {
	icon: IconName;
	title: string;
	body: string;
	link?: ForLink;
}

export interface ForPage {
	/** The URL segment: /for/<slug>/ — one of `FOR_LINKS` ($lib/forLinks). */
	slug: string;
	title: string;
	lead: string;
	/** The search result: <title> (" — Ochorus" is added) and meta description. */
	seoTitle: string;
	seoDescription: string;
	primary: ForLink;
	secondary: ForLink;
	pointsHeading: string;
	points: ForPoint[];
	ideasHeading: string;
	ideas: { title: string; body: string }[];
	picksNote: string;
	/** Book slugs, in shelf order. The build picks the first `SHELF_SIZE`
	 *  published in English out of the live list (routes/for-shelves), so an
	 *  unpublished slug drops and the next one takes its place. */
	picks: string[];
	questions: { q: string; a: string }[];
	closeHeading: string;
	closeBody: string;
}

/** The live languages besides English, by their English names, from the
 *  registry's "Go live" list — so the copy names exactly what the site
 *  serves, and a language taken live reaches it on the next build. ICU calls
 *  Luganda "Ganda"; Ochorus uses the name its readers use. */
const inEnglish = new Intl.DisplayNames(['en'], { type: 'language' });
const OTHER_LANGUAGES = LIVE_LOCALES.filter((l) => l !== 'en').map((l) =>
	l === 'lg' ? 'Luganda' : (inEnglish.of(l) ?? l)
);
/** "a, b and c". */
const series = (xs: string[]) => (xs.length < 2 ? xs.join('') : `${xs.slice(0, -1).join(', ')} and ${xs.at(-1)}`);

const FREE_ANSWER =
	'Yes. Every book and sermon on Ochorus is free to read, with no paywall, no subscription and no ads. The classics themselves are in the public domain, and Ochorus is a ministry, not a business.';

export const FOR_PAGES: ForPage[] = [
	{
		slug: 'churches',
		title: 'A free Christian library for your whole congregation',
		lead: 'Ochorus puts the great classics of the faith in every member’s pocket. Murray, Spurgeon, Bunyan, Augustine, Müller and hundreds of other books and sermons, free to read on any phone or computer. No subscriptions, no licences, no budget line.',
		seoTitle: 'Free Christian Books for Churches',
		seoDescription:
			`Classic Christian books, sermons and reading plans for your whole congregation, free to read in ${LIVE_LOCALES.length} languages. No subscriptions and no account needed.`,
		primary: { href: '/plans', label: 'Browse reading plans' },
		secondary: { href: '/books', label: 'Explore the library' },
		pointsHeading: 'Why churches use Ochorus',
		points: [
			{
				icon: 'book',
				title: 'Free for every member',
				body: 'Every book and sermon is free to read, and nobody needs an account. Share one link from the pulpit or in the church newsletter, and anyone can start reading that day.',
				link: { href: '/books', label: 'Browse the books' }
			},
			{
				icon: 'calendar',
				title: 'Read together, a chapter a day',
				body: 'Reading plans take a congregation through a book one short reading a day. They are ready-made for a sermon series, Lent, a season of prayer or a class for new believers.',
				link: { href: '/plans', label: 'See the reading plans' }
			},
			{
				icon: 'mic',
				title: 'Sermons from the great preachers',
				body: 'Hundreds of sermons by Spurgeon, Moody, Wesley, Whitefield, Edwards and others, many with study questions. A help in sermon preparation, and short enough for a one-week study.',
				link: { href: '/sermons', label: 'Read the sermons' }
			},
			{
				icon: 'globe',
				title: 'In the languages your people speak',
				body: `Books are published as full editions in ${series(OTHER_LANGUAGES)} as well as English, with more languages on the way, so members can read in their own language.`
			}
		],
		ideasHeading: 'Ways to use it in your church',
		ideas: [
			{
				title: 'A church-wide reading plan',
				body: 'Choose a plan, announce it on Sunday, and read the same chapter together all week. Small groups can pick up the conversation midweek.'
			},
			{
				title: 'A book for your small groups',
				body: 'Choose one classic for the term. Everyone can afford it because it costs nothing, and nobody is left out for want of a copy.'
			},
			{
				title: 'Help new believers grow',
				body: 'Start new Christians on clear, warm books like Moody’s The Way to God and Spurgeon’s All of Grace, then a short reading plan.'
			},
			{
				title: 'Children and youth, too',
				body: 'Young-reader editions retell the great classics for children and teens, so Sunday school and youth group can read the same stories at their own level.'
			}
		],
		picksNote: 'Classics that have fed congregations for generations.',
		picks: [
			'school-of-prayer',
			'power-through-prayer',
			'the-way-to-god',
			'all-of-grace',
			'absolute-surrender',
			'pilgrims-progress',
			'the-reformed-pastor',
			'the-imitation-of-christ'
		],
		questions: [
			{ q: 'Is Ochorus really free?', a: FREE_ANSWER },
			{
				q: 'Do our members need to create an account?',
				a: 'No. Anyone can read without signing up. A free account is optional: it keeps a reader’s progress, notes and saved books in step across their devices.'
			},
			{
				q: 'Which writers are in the library?',
				a: 'The library spans the whole history of the church: early church fathers such as Augustine and Athanasius, Reformers such as Luther and Calvin, the Puritans, the great revival preachers, missionaries such as Hudson Taylor and Amy Carmichael, and leaders of the East African Revival.'
			},
			{
				q: 'Can we print books for our members?',
				a: 'Some books can be downloaded as free PDF and EPUB files from the book’s page. If you would like to print books for your church or an outreach, please contact us first. We would be glad to talk it through.'
			},
			{
				q: 'How can our church support the work?',
				a: 'Besides the free library, Ochorus prints books and gives them away at pastors’ conferences and in churches, schools and prisons across East Africa. If your church would like to take part, contact us.'
			}
		],
		closeHeading: 'Bring the classics to your congregation',
		closeBody:
			'Start with a reading plan everyone can follow, or browse the library and choose a book to read together.'
	},
	{
		slug: 'homeschool',
		title: 'A free library of Christian classics for your homeschool',
		lead: 'Living books from twenty centuries of the church, free to read on any device. Bunyan, Augustine, Müller, Hudson Taylor and George MacDonald, with many classics retold in editions for children and for teens.',
		seoTitle: 'Free Christian Classics for Homeschool',
		seoDescription:
			'Free Christian living books for homeschool families and co-ops: classics, missionary biographies and editions for children and teens, with reading plans.',
		primary: { href: '/young-readers', label: 'Books for young readers' },
		secondary: { href: '/plans', label: 'Reading plans' },
		pointsHeading: 'Why homeschool families use Ochorus',
		points: [
			{
				icon: 'book',
				title: 'A free living-books shelf',
				body: 'Classic Christian books for history, literature, biography and Bible. No curriculum fees and no subscriptions, for one family or a whole co-op.',
				link: { href: '/books', label: 'Browse the books' }
			},
			{
				icon: 'layers',
				title: 'The same story at every level',
				body: 'Many classics come in a children’s edition, a teens edition and the full original. Brothers and sisters can read the same story together, each at their own level.',
				link: { href: '/young-readers', label: 'See the young-reader editions' }
			},
			{
				icon: 'calendar',
				title: 'A schedule already made',
				body: 'Reading plans set out one short reading a day, including five-minute family devotions. The notebook keeps highlights and notes, and prints.',
				link: { href: '/plans', label: 'See the reading plans' }
			},
			{
				icon: 'headphones',
				title: 'Read-aloud built in',
				body: 'Any chapter can be read aloud with Listen: for read-aloud time, for a young reader following the words, or in the car.'
			}
		],
		ideasHeading: 'Ways to use it in your homeschool',
		ideas: [
			{
				title: 'Church history from the sources',
				body: 'Read Augustine’s Confessions, Athanasius’ On the Incarnation and Foxe’s Book of Martyrs alongside your history lessons, with the author biographies for background.'
			},
			{
				title: 'Missionary biographies',
				body: 'True stories of George Müller, Hudson Taylor, Mary Slessor and Samuel Ajayi Crowther, many retold for children and teens.'
			},
			{
				title: 'Co-op book clubs',
				body: 'Every family can read the same book at no cost. Share one link and meet to talk it over.'
			},
			{
				title: 'Morning time',
				body: 'Open the day with a family devotions plan or a reading from Spurgeon’s Morning by Morning.'
			}
		],
		picksNote: 'Books that work well across ages.',
		picks: [
			'pilgrims-progress-children',
			'pilgrims-progress-teens',
			'hurlbuts-life-of-christ',
			'the-life-of-trust-children',
			'samuel-ajayi-crowther-a-life-teens',
			'the-princess-and-the-goblin',
			'foxes-book-of-martyrs',
			'confessions',
			'on-the-incarnation'
		],
		questions: [
			{ q: 'Is Ochorus really free?', a: FREE_ANSWER },
			{
				q: 'What ages is Ochorus for?',
				a: 'All of them. The children’s editions are written for younger readers and for reading aloud together, the teens editions for older children, and the full originals for older students and parents.'
			},
			{
				q: 'Are the children’s editions faithful to the originals?',
				a: 'Each young-reader edition retells the classic in simpler words, keeping its story and its message. Every edition’s page links to the others, so a reader can move up to the teens edition and the full text when they are ready.'
			},
			{
				q: 'Can we read without an internet connection?',
				a: 'Yes. Use Download on a book’s page to save it for reading offline, and some books can also be downloaded as free PDF and EPUB files.'
			},
			{
				q: 'Can our co-op or association share Ochorus with families?',
				a: 'Please do. Link to this page or to any book, plan or writer. If you would like to talk about using Ochorus with a larger group, contact us.'
			}
		],
		closeHeading: 'Start this term’s reading',
		closeBody:
			'Browse the editions for young readers, or pick a reading plan to work through together.'
	},
	{
		slug: 'parents',
		title: 'Great Christian books for your children, free',
		lead: 'True stories of faith and courage, classic tales and short family devotions, written for children and teens. Free to read on any device, with no ads and no account needed.',
		seoTitle: 'Free Christian Books for Your Children',
		seoDescription:
			'Free Christian books for children and teens: true stories of faith, the classics retold and five-minute family devotions. No ads and no account needed.',
		primary: { href: '/young-readers', label: 'Books for children' },
		secondary: { href: '/teens', label: 'Books for teens' },
		pointsHeading: 'Why parents use Ochorus',
		points: [
			{
				icon: 'heart',
				title: 'Heroes worth looking up to',
				body: 'Real men and women who trusted God, among them George Müller, Hudson Taylor, Mary Slessor, Amanda Smith and Samuel Ajayi Crowther, with their stories told for children and teens.',
				link: { href: '/young-readers', label: 'Meet them' }
			},
			{
				icon: 'calendar',
				title: 'Five-minute family devotions',
				body: 'Short reading plans made for families: one chapter a night, read aloud together at bedtime or the breakfast table.',
				link: { href: '/plans', label: 'See the reading plans' }
			},
			{
				icon: 'layers',
				title: 'Books that grow with them',
				body: 'Many classics come in a children’s edition, a teens edition and the original. A child who loves The Pilgrim’s Progress at seven can read the whole book at seventeen.',
				link: { href: '/teens', label: 'Books for teens' }
			},
			{
				icon: 'headphones',
				title: 'Listen together',
				body: 'Any chapter can be read aloud with Listen, so children can follow the words, or listen in the car.'
			}
		],
		ideasHeading: 'Ways families use it',
		ideas: [
			{
				title: 'Bedtime stories',
				body: 'Read a chapter of a children’s edition together, or let Listen read it while they follow along.'
			},
			{
				title: 'A daily habit for teens',
				body: 'Thirty-day devotionals like Anchored and Rooted are written for teenagers to read on their own phone, a few minutes a day.'
			},
			{
				title: 'Talk about it',
				body: 'The chapters are short, so there is time to talk about what you read and pray together afterwards.'
			},
			{
				title: 'Something safe to hand them',
				body: 'No ads, no feeds and nothing to buy. Just good books, ready whenever they want to read.'
			}
		],
		picksNote: 'Favourites for reading together.',
		picks: [
			'pilgrims-progress-children',
			'brave-for-god',
			'the-life-of-trust-children',
			'samuel-ajayi-crowther-a-life-children',
			'amanda-smith-autobiography-children',
			'divine-songs-for-children',
			'anchored-1',
			'daughters-of-the-king-1',
			'sons-of-the-king-1'
		],
		questions: [
			{ q: 'Is Ochorus really free?', a: FREE_ANSWER },
			{
				q: 'Does my child need an account?',
				a: 'No. Anyone can read without signing up. A free account is optional: it keeps reading progress, notes and saved books in step across devices.'
			},
			{
				q: 'What ages are the books for?',
				a: 'The books for young readers are for children to read with a grown-up or on their own, the teens books are for older children and teenagers, and the full classics are there when they are ready for more.'
			},
			{
				q: 'Is it safe for children to use?',
				a: 'Ochorus has no ads and nothing to buy. It is a library of Christian books, and nothing else competes for your child’s attention.'
			}
		],
		closeHeading: 'Find a book to read together tonight',
		closeBody: 'Start with the books for children, or the books for teens.'
	}
];

/** The page for a URL segment, or undefined. */
export const forPage = (slug: string): ForPage | undefined => FOR_PAGES.find((p) => p.slug === slug);

/** How many books a page's starter shelf shows: one row of the desktop grid.
 *  `picks` runs longer, so an unpublished pick leaves a backup in its place. */
export const SHELF_SIZE = 6;

/** A page's starter shelf: its picks out of the live English list (pass
 *  `listBooks('en')`), in the
 *  page's order, the first `SHELF_SIZE` that are published, trimmed to what a
 *  cover card draws. Built once at build time (routes/for-shelves). */
export function forShelf(english: BookSummary[], slugs: string[]): CoverBook[] {
	const bySlug = new Map(english.map((b) => [b.slug, b]));
	return slugs
		.flatMap((s) => {
			const b = bySlug.get(s);
			return b ? [toCoverBook(b)] : [];
		})
		.slice(0, SHELF_SIZE);
}
