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
		slug: 'small-groups',
		title: 'Free books for your small group or Bible study',
		lead: 'Choose a classic for the term and everyone in the group can read it, free, on their own phone. Prayer, holiness, grace and the life of faith, from Murray, Tozer, Brother Lawrence, Hannah Whitall Smith and many more.',
		seoTitle: 'Free Books for Small Groups and Bible Studies',
		seoDescription:
			'Free Christian classics, sermons and reading plans for small groups and Bible studies. Everyone reads the same book on their own phone, no account needed.',
		primary: { href: '/plans', label: 'Find a reading plan' },
		secondary: { href: '/books', label: 'Browse the books' },
		pointsHeading: 'Why small groups use Ochorus',
		points: [
			{
				icon: 'users',
				title: 'Everyone can have the book',
				body: 'Every book is free, so nobody is left out for the price of a copy. Send one link to the group and everyone can start reading that evening.',
				link: { href: '/books', label: 'Browse the books' }
			},
			{
				icon: 'calendar',
				title: 'A pace the whole group can keep',
				body: 'Reading plans set out one short reading a day, so the group arrives at the meeting having read the same chapters.',
				link: { href: '/plans', label: 'See the reading plans' }
			},
			{
				icon: 'mic',
				title: 'Sermons that fit one evening',
				body: 'A sermon by Spurgeon, Moody or Wesley is short enough to read in the week and talk through in an hour, and many come with study questions.',
				link: { href: '/sermons', label: 'Read the sermons' }
			},
			{
				icon: 'tag',
				title: 'Find a book by its theme',
				body: 'Topics gather books and sermons on prayer, suffering, holiness, the Holy Spirit and more, so you can choose a study that meets the group where it is.',
				link: { href: '/topics', label: 'Browse the topics' }
			}
		],
		ideasHeading: 'Ways to use it in your group',
		ideas: [
			{
				title: 'A book a term',
				body: 'Pick one classic, read a chapter or two a week, and spend the meeting on what struck each person.'
			},
			{
				title: 'A sermon a week',
				body: 'Read one sermon before you meet and use its study questions to open the conversation.'
			},
			{
				title: 'Read together on a plan',
				body: 'Start a reading plan on the same day and talk through each week’s readings when you meet.'
			},
			{
				title: 'Meet the writers',
				body: 'Many writers have a full biography, so the group can hear the story behind a book before reading it.'
			}
		],
		picksNote: 'Short classics that open good conversations.',
		picks: [
			'the-pursuit-of-god',
			'absolute-surrender',
			'the-practice-of-the-presence-of-god',
			'the-christians-secret-of-a-happy-life-4',
			'humility-2',
			'school-of-prayer',
			'the-god-of-all-comfort',
			'power-through-prayer'
		],
		questions: [
			{ q: 'Is Ochorus really free?', a: FREE_ANSWER },
			{
				q: 'Does everyone in the group need an account?',
				a: 'No. Anyone can read without signing up. A free account is optional: it keeps a reader’s progress, notes and saved books in step across their devices.'
			},
			{
				q: 'Are there discussion questions?',
				a: 'Many sermons come with study questions and answers, drawn from the sermon itself. For books, a reading plan gives the group a shared pace, and the chapters are short enough to talk through.'
			},
			{
				q: 'Can we read it without a phone?',
				a: 'Yes. Ochorus works on any computer or tablet as well, and some books can be downloaded as free PDF and EPUB files from the book’s page.'
			}
		],
		closeHeading: 'Choose your group’s next book',
		closeBody: 'Start with a reading plan, or browse the library and pick a classic to read together.'
	},
	{
		slug: 'youth',
		title: 'Free books your teenagers will actually read',
		lead: 'The great classics retold for teens, true stories of people who met God before they were grown, and thirty-day devotionals written for young people. Free on their own phone, with no ads and no account needed.',
		seoTitle: 'Free Christian Books for Youth Ministries',
		seoDescription:
			'Free Christian books for youth groups and teens: classics retold, true stories of faith and thirty-day devotionals. On any phone, no ads, no account needed.',
		primary: { href: '/teens', label: 'Books for teens' },
		secondary: { href: '/plans', label: 'Reading plans' },
		pointsHeading: 'Why youth ministries use Ochorus',
		points: [
			{
				icon: 'layers',
				title: 'Classics in words teens read',
				body: 'The Pilgrim’s Progress, All of Grace and others, retold for teenagers without losing what they say. Each one links to the full original for when they want more.',
				link: { href: '/teens', label: 'See the teens editions' }
			},
			{
				icon: 'heart',
				title: 'True stories worth telling',
				body: 'C. S. Lewis, Corrie ten Boom, Elisabeth Elliot, Watchman Nee and others, told for teens: real people who trusted God when it cost them.',
				link: { href: '/teens', label: 'Meet them' }
			},
			{
				icon: 'calendar',
				title: 'Thirty days with God',
				body: 'Devotionals like Anchored and Rooted give a teenager a few minutes a day for a month, and reading plans keep a whole group on the same page.',
				link: { href: '/plans', label: 'See the reading plans' }
			},
			{
				icon: 'headphones',
				title: 'On their phone, ready to listen',
				body: 'Everything works on a phone with no sign-up, and any chapter can be read aloud with Listen, for the bus, the walk or the drive home from camp.'
			}
		],
		ideasHeading: 'Ways to use it in your youth ministry',
		ideas: [
			{
				title: 'A thirty-day challenge',
				body: 'Start the group on the same devotional after a retreat or camp, and check in each week on how it is going.'
			},
			{
				title: 'A book for the term',
				body: 'Read a teens edition together, a chapter or two a week, and spend youth group on the questions it raises.'
			},
			{
				title: 'Heroes night',
				body: 'Tell one true story of faith each week, then point the group to the full biography to read at home.'
			},
			{
				title: 'Something to hand a new believer',
				body: 'Send a young person who has just come to faith a link to All of Grace for teens and a short reading plan.'
			}
		],
		picksNote: 'Teens editions and devotionals to start with.',
		picks: [
			'pilgrims-progress-teens',
			'all-of-grace-teens',
			'anchored-1',
			'rooted-1',
			'c-s-lewis-a-life-teens',
			'corrie-ten-boom-a-life-teens',
			'elisabeth-elliot-a-life-teens',
			'they-were-young-1'
		],
		questions: [
			{ q: 'Is Ochorus really free?', a: FREE_ANSWER },
			{
				q: 'Do teens need to sign up?',
				a: 'No. Anyone can read without an account. A free account is optional: it keeps reading progress, notes and saved books in step across devices.'
			},
			{
				q: 'What ages are the teens books for?',
				a: 'The teens editions are written for older children and teenagers. For younger members, the books for young readers retell the same classics more simply.'
			},
			{
				q: 'Is it safe to send teenagers to?',
				a: 'Ochorus has no ads and nothing to buy. It is a library of Christian books, and nothing else competes for their attention.'
			}
		],
		closeHeading: 'Give your group something good to read',
		closeBody: 'Start with the books for teens, or pick a reading plan to go through together.'
	},
	{
		slug: 'missionaries',
		title: 'Christian classics to share, free, in the languages you serve',
		lead: 'A free library you can hand to anyone with a link: no payment, no sign-up. The great classics, sermons and missionary biographies, many published as full editions in other languages.',
		seoTitle: 'Free Christian Books for Missionaries',
		seoDescription:
			'Free Christian classics, sermons and missionary biographies to share with the people you serve, with full editions in several languages. No payment or sign-up.',
		primary: { href: '/books', label: 'Browse the library' },
		secondary: { href: '/biographies', label: 'Missionary lives' },
		pointsHeading: 'Why missionaries use Ochorus',
		points: [
			{
				icon: 'share',
				title: 'Free to share with anyone',
				body: 'Every book and sermon is free, with no account needed, so a new believer can be sent a link and start reading straight away.',
				link: { href: '/books', label: 'Browse the books' }
			},
			{
				icon: 'globe',
				title: 'Full editions in other languages',
				body: `Books are published as full editions in ${series(OTHER_LANGUAGES)} as well as English, with more languages on the way, so people can read in their own language.`
			},
			{
				icon: 'compass',
				title: 'The lives of those who went before',
				body: 'Hudson Taylor, David Brainerd, Amy Carmichael, George Müller, Samuel Ajayi Crowther and others, in their own words and in biographies.',
				link: { href: '/biographies', label: 'Read the biographies' }
			},
			{
				icon: 'calendar',
				title: 'A path for new believers',
				body: 'Reading plans take a new Christian through a book one short reading a day, and clear books like The Way to God make a good first step.',
				link: { href: '/plans', label: 'See the reading plans' }
			}
		],
		ideasHeading: 'Ways to use it in your mission',
		ideas: [
			{
				title: 'Discipleship by link',
				body: 'Send each new believer the same short reading plan, and talk through what they read when you meet.'
			},
			{
				title: 'Training local leaders',
				body: 'Read Baxter’s The Reformed Pastor or Torrey’s How to Bring Men to Christ with the people you are training.'
			},
			{
				title: 'Strength for the long haul',
				body: 'When the work is hard, read the journals and letters of those who served before you.'
			},
			{
				title: 'Supporters at home',
				body: 'Point your praying friends to the same missionary biographies that shaped your own calling.'
			}
		],
		picksNote: 'Lives and books that have sent people out.',
		picks: [
			'a-retrospect',
			'life-and-diary-of-david-brainerd',
			'things-as-they-are',
			'george-muller-of-bristol',
			'journal-of-an-expedition-up-the-niger',
			'evangelization-of-the-world',
			'how-to-bring-men-to-christ',
			'separation-and-service'
		],
		questions: [
			{ q: 'Is Ochorus really free?', a: FREE_ANSWER },
			{
				q: 'Do the people I serve need an account?',
				a: 'No. Anyone with the link can read, with nothing to pay and no sign-up. A free account is optional and only keeps a reader’s progress and notes in step across devices.'
			},
			{
				q: 'Which languages are available?',
				a: `Besides English, books are published in ${series(OTHER_LANGUAGES)}. Each language has its own editions, so the shelf in each language shows only what has been published in it.`
			},
			{
				q: 'Can we read without an internet connection?',
				a: 'Yes. Use Download on a book’s page to save it for reading offline, and some books can also be downloaded as free PDF and EPUB files.'
			},
			{
				q: 'Can we request a book in a language we serve?',
				a: 'Please contact us. We would be glad to hear which books and languages would help your work most.'
			}
		],
		closeHeading: 'Share the classics with the people you serve',
		closeBody: 'Browse the library, or start with the lives of the missionaries who went before you.'
	},
	{
		slug: 'schools',
		title: 'Free Christian classics for your classroom',
		lead: 'Primary sources from twenty centuries of the church, free for every student on any device. Augustine, Athanasius, Bunyan and Chesterton, true lives of faith, and many classics retold for children and teens.',
		seoTitle: 'Free Christian Classics for Schools',
		seoDescription:
			'Free Christian classics for schools: primary sources for Bible, history and literature, missionary biographies, and editions for children and teens.',
		primary: { href: '/books', label: 'Browse the library' },
		secondary: { href: '/teens', label: 'Books for teens' },
		pointsHeading: 'Why schools use Ochorus',
		points: [
			{
				icon: 'book',
				title: 'Assigned reading at no cost',
				body: 'Every book is free to read, so a whole class can read the same text with no textbook budget and no licences to manage.',
				link: { href: '/books', label: 'Browse the books' }
			},
			{
				icon: 'layers',
				title: 'One text, several reading levels',
				body: 'Many classics come in a children’s edition, a teens edition and the full original, so a mixed class can read the same story at different levels.',
				link: { href: '/young-readers', label: 'See the young-reader editions' }
			},
			{
				icon: 'users',
				title: 'Biographies for every era',
				body: 'Long-form lives of the writers, from the early church to the twentieth century, give students the history behind each book.',
				link: { href: '/biographies', label: 'Read the biographies' }
			},
			{
				icon: 'quote',
				title: 'Quotations with their sources',
				body: 'Each quotation links to the chapter it comes from, so students can check a quote in context and cite it properly.',
				link: { href: '/quotes', label: 'Browse the quotes' }
			}
		],
		ideasHeading: 'Ways to use it in your school',
		ideas: [
			{
				title: 'Church history from the sources',
				body: 'Read Athanasius’ On the Incarnation, Augustine’s Confessions and Foxe’s Book of Martyrs alongside the history they lived through.'
			},
			{
				title: 'Literature with a Christian heritage',
				body: 'Teach The Pilgrim’s Progress, George MacDonald and G. K. Chesterton, with editions for younger readers where they exist.'
			},
			{
				title: 'Biography projects',
				body: 'Let each student pick a writer, read the biography, and present what that person believed and why it mattered.'
			},
			{
				title: 'Chapel and devotions',
				body: 'Use a reading plan or a short sermon for a school chapel or a class devotion.'
			}
		],
		picksNote: 'Classics that work in the classroom.',
		picks: [
			'pilgrims-progress-teens',
			'on-the-incarnation',
			'confessions',
			'foxes-book-of-martyrs',
			'orthodoxy',
			'samuel-ajayi-crowther-a-life-teens',
			'hurlbuts-life-of-christ',
			'c-s-lewis-a-life-teens'
		],
		questions: [
			{ q: 'Is Ochorus really free?', a: FREE_ANSWER },
			{
				q: 'Do students need accounts?',
				a: 'No. Students can read without signing up. A free account is optional: it keeps a reader’s progress, notes and saved books in step across their devices.'
			},
			{
				q: 'What ages is it suitable for?',
				a: 'The children’s editions suit younger pupils and reading aloud, the teens editions suit older children and teenagers, and the full originals suit senior students.'
			},
			{
				q: 'Can we print or download the books?',
				a: 'Some books can be downloaded as free PDF and EPUB files from the book’s page. If you would like to print books for your school, please contact us first.'
			}
		],
		closeHeading: 'Bring the classics into your classroom',
		closeBody: 'Browse the library, or start with the books written for teens.'
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
