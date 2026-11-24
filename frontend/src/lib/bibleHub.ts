/**
 * The /bible hub's own data and the helpers only its pages draw with: the
 * canon strip, the chapter picker, "Where to start" and its paths, and the
 * "Passages on…" row. Apart from $lib/bible (which the root layout imports for
 * the chrome), so the hub's prose, in every hub locale, loads with the hub
 * rather than with every page.
 */

import {
	BIBLE_DIVISIONS,
	bibleChapterCount,
	byTestament,
	bibleChapterOrder,
	divisionOf,
	type CanonSlot,
	type CanonTestament
} from '$lib/bible';
import { canonIn, canonName, chapterLabel } from '$lib/bibleNames';
import { bibleText, type BibleText } from '$lib/bibleLocales';
import { bookChapterPath } from '$lib/reading-schema';

/**
 * The hub's canon strip: ALL 66 books in canonical order, by testament and
 * division, each slot holding the library's edition or null. Unlike
 * `groupBible`, nothing is dropped — the strip's point is the whole shape of the
 * canon, with the books a language lacks shown as gaps. The names are the
 * canon's short names in `lang` ($lib/bibleNames).
 */
export function canonStrip<
	T extends { series_position?: number | null; word_count?: number | null; chapter_count?: number }
>(books: readonly T[], lang: string): CanonTestament<T>[] {
	const at = new Map<number, T>();
	for (const b of books) {
		const p = b.series_position;
		if (divisionOf(p) && !at.has(p!)) at.set(p!, b);
	}
	// Words where the API sends them; chapters stand in for a book without a count.
	const size = (b: T) => Math.sqrt(b.word_count || (b.chapter_count ?? 0) * 500);
	const largest = Math.max(0, ...[...at.values()].map(size));
	const chaptersOf = (b: T) => bibleChapterCount([b]);
	const most = Math.max(0, ...[...at.values()].map(chaptersOf));
	const slot = (position: number): CanonSlot<T> => {
		const book = at.get(position) ?? null;
		const chapters = book ? chaptersOf(book) : 0;
		return {
			position,
			name: canonName(position, lang) ?? '',
			abbr: canonIn(lang)[position - 1][1],
			book,
			weight: book && largest ? Math.round((size(book) / largest) * 100) / 100 : 0,
			chapters,
			tall: chapters && most ? Math.round((Math.sqrt(chapters) / Math.sqrt(most)) * 100) / 100 : 0
		};
	};
	return byTestament(
		BIBLE_DIVISIONS.map((division) => ({
			division,
			slots: Array.from({ length: division.last - division.first + 1 }, (_, i) =>
				slot(division.first + i)
			)
		}))
	);
}

/** One chip of the hub's chapter picker. */
export interface BibleChapterLink {
	/** The Bible's own chapter number (1 … 150 for Psalms). */
	n: number;
	/** The chip's accessible name and tooltip: "Psalms 23". */
	name: string;
	/** The reader chapter, unlocalized. */
	href: string;
}

/**
 * A Bible book's chapters for the hub's picker, from the book's summary alone.
 * A summary carries no chapter titles, so where the book page reads each
 * chip's number off its title (`chapterNumber`), this counts them and places
 * each by `bibleChapterOrder`. The name is the canon's short name in `lang`, as
 * the canon strip's spines are; a book off the canon falls back to its title.
 */
export function bibleChapters(
	book: {
		slug: string;
		title: string;
		chapter_count?: number;
		series_position?: number | null;
	},
	lang: string
): BibleChapterLink[] {
	const pos = book.series_position;
	return Array.from({ length: bibleChapterCount([book]) }, (_, i) => ({
		n: i + 1,
		name: chapterLabel(pos, i + 1, lang) ?? `${book.title} ${i + 1}`,
		href: bookChapterPath(book.slug, bibleChapterOrder(i + 1), false)
	}));
}

/** One step of the hub's "Where to start" path. */
export interface BibleStart {
	/** The Bible book's slug (its `the-bible` series volume). */
	slug: string;
	/** Why this book, and why now, in each hub locale. */
	why: BibleText;
}

/**
 * The hub's "Where to start": five books for a first reader, in reading order.
 * A Gospel first, the shortest; then the one written "that you may believe";
 * then the beginning; then the prayer book; then the gospel explained. The
 * reasons are the hub's own prose, in each hub locale (`BibleText`); a
 * quotation in them is the Open Word Bible's wording in that language. A step
 * whose book is missing in the series (`bibleStarts`) is left out.
 */
export const BIBLE_STARTS: readonly BibleStart[] = [
	{
		slug: 'gospel-of-mark',
		why: {
			en: 'The shortest Gospel, and the quickest: the life of Jesus in one sitting.',
			es: 'El Evangelio más breve y el más ágil: la vida de Jesús de una sentada.'
		}
	},
	{
		slug: 'gospel-of-john',
		why: {
			en: 'Written “so that you may believe”: who Jesus is, in his own words.',
			// John 20:31, OWB-es.
			es: 'Escrito «para que ustedes crean»: quién es Jesús, en sus propias palabras.'
		}
	},
	{
		slug: 'genesis',
		why: {
			en: 'The beginning: creation, the fall, and God’s promise to Abraham.',
			es: 'El principio: la creación, la caída y la promesa de Dios a Abraham.'
		}
	},
	{
		slug: 'psalms',
		why: {
			en: 'The Bible’s prayer book. Read one a day, aloud if you can.',
			es: 'El libro de oración de la Biblia. Conviene leer un salmo al día, en voz alta si se puede.'
		}
	},
	{
		slug: 'romans',
		why: {
			en: 'The gospel set out step by step: sin, grace, faith and new life.',
			es: 'El evangelio expuesto paso a paso: el pecado, la gracia, la fe y la vida nueva.'
		}
	}
];

/** The "Where to start" steps the series has, each with its book, in order. */
export function bibleStarts<T extends { slug: string }>(
	books: readonly T[],
	lang: string
): { book: T; why: string }[] {
	const bySlug = new Map(books.map((b) => [b.slug, b]));
	return BIBLE_STARTS.flatMap((s) => {
		const book = bySlug.get(s.slug);
		return book ? [{ book, why: bibleText(s.why, lang) }] : [];
	});
}

/**
 * The hub's "Passages on…" row: topic shelves whose "In the Bible" section
 * (`scripture_graph.topic_bible_chapters`, on the topic page) names chapters
 * of its own, with the short subject a reader would look for. In this order;
 * a topic the language lacks is left out (`bibleTopics`). English only: the
 * topic pages' "In the Bible" section is (the API sends `bible_chapters` for
 * English alone), so the hub asks for the row only there (`BIBLE_TOPIC_LOCALES`).
 * Chosen for distinct lists: nearly every shelf's list includes Romans 8, so
 * these are the ones whose other chapters differ most.
 */
export const BIBLE_TOPIC_LOCALES: readonly string[] = ['en'];

export const BIBLE_TOPICS: readonly { slug: string; label: string }[] = [
	{ slug: 'prayer', label: 'Prayer' },
	{ slug: 'faith-and-guidance', label: 'Guidance' },
	{ slug: 'grace-and-comfort', label: 'Comfort' },
	{ slug: 'holy-spirit', label: 'The Holy Spirit' },
	{ slug: 'abiding-in-christ', label: 'Abiding in Christ' },
	{ slug: 'victory-over-sin', label: 'Temptation and sin' },
	{ slug: 'the-body-of-christ', label: 'The church' },
	{ slug: 'to-the-ends-of-the-earth', label: 'Mission' }
];

/** The `BIBLE_TOPICS` this language has a shelf for, in order. */
export function bibleTopics(topics: readonly { slug: string }[]): { slug: string; label: string }[] {
	const have = new Set(topics.map((t) => t.slug));
	return BIBLE_TOPICS.filter((t) => have.has(t.slug));
}

/** One step of a "Where to start" path: a chapter (or, with no chapter, a
 *  whole book) by its place in the canon, and why. */
export interface BiblePathStep {
	position: number;
	chapter?: number;
	why: BibleText;
}

/**
 * The hub's other ways in, beside the first reader's five books
 * (`BIBLE_STARTS`): what brought someone here, and four or five chapters for
 * it, each with why, in each hub locale (`BibleText`). The reasons say what
 * the chapter holds in plain words; where they lean on a phrase it is one a
 * reader will meet there (in Spanish, the Open Word Bible's own wording).
 */
export const BIBLE_PATHS: readonly {
	id: string;
	label: BibleText;
	lede: BibleText;
	steps: readonly BiblePathStep[];
}[] = [
	{
		id: 'jesus',
		label: { en: 'Who Jesus is', es: 'Quién es Jesús' },
		lede: {
			en: 'Four chapters on who Jesus is, from the people who knew him.',
			es: 'Cuatro capítulos sobre quién es Jesús, contados por quienes lo conocieron.'
		},
		steps: [
			{
				position: 43,
				chapter: 1,
				why: {
					en: 'The Word who was with God and was God, come to live among us.',
					es: 'El Verbo, que estaba con Dios y era Dios, vino a vivir entre nosotros.'
				}
			},
			{
				position: 41,
				chapter: 8,
				why: {
					en: 'Jesus asks his friends the question: who do you say I am?',
					es: 'Jesús les hace a sus amigos la pregunta: ¿quién dicen que soy yo?'
				}
			},
			{
				position: 50,
				chapter: 2,
				why: {
					en: 'He did not hold on to equality with God, but emptied himself.',
					es: 'No se aferró a ser igual a Dios: «se vació a Sí mismo».'
				}
			},
			{
				position: 51,
				chapter: 1,
				why: {
					en: 'The image of the invisible God, in whom all things hold together.',
					es: 'Es «la imagen del Dios que no se ve», y todas las cosas se mantienen unidas en Él.'
				}
			}
		]
	},
	{
		id: 'grief',
		label: { en: 'Grief and hard times', es: 'Duelo y tiempos difíciles' },
		lede: {
			en: 'For a heavy day: chapters to read slowly, and more than once.',
			es: 'Para un día pesado: capítulos para leer despacio, y más de una vez.'
		},
		steps: [
			{
				position: 19,
				chapter: 23,
				why: {
					en: 'The shepherd who walks with you through the darkest valley.',
					es: 'El pastor que acompaña a los suyos por el valle más oscuro.'
				}
			},
			{
				position: 43,
				chapter: 11,
				why: {
					en: 'Jesus weeps at his friend’s grave, then calls him out of it.',
					es: 'Jesús llora ante la tumba de su amigo, y luego lo llama a salir de ella.'
				}
			},
			{
				position: 52,
				chapter: 4,
				why: {
					en: 'Grief with hope: those who have died in Christ are not lost.',
					es: 'Un duelo con esperanza: los que han muerto en Cristo no están perdidos.'
				}
			},
			{
				position: 66,
				chapter: 21,
				why: {
					en: 'The end of the story: no more death, mourning, crying or pain.',
					es: 'El final de la historia: la muerte, el llanto y el dolor quedan atrás para siempre.'
				}
			}
		]
	},
	{
		id: 'wisdom',
		label: { en: 'Wisdom for daily life', es: 'Sabiduría para cada día' },
		lede: {
			en: 'Four chapters for ordinary days: work, worry, words and people.',
			es: 'Cuatro capítulos para los días comunes: el trabajo, las preocupaciones, las palabras y la gente.'
		},
		steps: [
			{
				position: 20,
				chapter: 3,
				why: {
					en: 'Trust the LORD with all your heart, and he will make your paths straight.',
					es: 'Confiar en el SEÑOR de todo corazón, y no en el propio entendimiento.'
				}
			},
			{
				position: 40,
				chapter: 6,
				why: {
					en: 'Prayer, money and worry, from the Sermon on the Mount.',
					es: 'La oración, el dinero y la ansiedad, del Sermón del Monte.'
				}
			},
			{
				position: 59,
				chapter: 1,
				why: {
					en: 'Ask God for wisdom, and be quick to listen and slow to speak.',
					es: 'Pedir sabiduría a Dios, estar dispuesto a escuchar y ser lento para hablar.'
				}
			},
			{
				position: 45,
				chapter: 12,
				why: {
					en: 'A life given to God, and love worked out with the people around you.',
					es: 'Una vida entregada a Dios, y el amor puesto en práctica con los demás.'
				}
			}
		]
	},
	{
		id: 'story',
		label: { en: 'The big story', es: 'La gran historia' },
		lede: {
			en: 'The whole Bible in five chapters, from the first day to the new creation.',
			es: 'Toda la Biblia en cinco capítulos, del primer día a la nueva creación.'
		},
		steps: [
			{
				position: 1,
				chapter: 1,
				why: {
					en: 'In the beginning: God makes the world, and calls it very good.',
					es: 'En el principio: Dios hace el mundo y lo llama muy bueno.'
				}
			},
			{
				position: 1,
				chapter: 12,
				why: {
					en: 'God calls Abram, and promises to bless every nation through him.',
					es: 'Dios llama a Abram y promete bendecir por medio de él a todas las naciones.'
				}
			},
			{
				position: 23,
				chapter: 53,
				why: {
					en: 'The servant who suffers for the sins of others.',
					es: 'El siervo que sufre por los pecados de otros.'
				}
			},
			{
				position: 42,
				chapter: 24,
				why: {
					en: 'The empty tomb, and the risen Jesus on the road to Emmaus.',
					es: 'La tumba vacía, y Jesús resucitado en el camino a Emaús.'
				}
			},
			{
				position: 66,
				chapter: 21,
				why: {
					en: 'All things made new, and God living with his people.',
					es: 'Todas las cosas hechas nuevas, y Dios viviendo con su pueblo.'
				}
			}
		]
	}
];

/**
 * A path's steps the library can open, each with its book, a title ("John 1",
 * "Psalm 23", or the book's own for a whole-book step) and its link
 * (unlocalized). A step whose book or chapter the library lacks is left out.
 */
export function biblePathSteps<
	T extends { slug: string; title: string; chapter_count?: number; series_position?: number | null }
>(
	steps: readonly BiblePathStep[],
	books: readonly T[],
	lang: string
): { book: T; title: string; href: string; why: string }[] {
	const at = new Map(books.flatMap((b) => (b.series_position != null ? [[b.series_position, b] as const] : [])));
	return steps.flatMap((s) => {
		const book = at.get(s.position);
		if (!book) return [];
		const why = bibleText(s.why, lang);
		if (s.chapter == null) return [{ book, title: book.title, href: `/books/${book.slug}`, why }];
		if (s.chapter > bibleChapterCount([book])) return [];
		return [
			{
				book,
				title: chapterLabel(s.position, s.chapter, lang) ?? `${book.title} ${s.chapter}`,
				href: bookChapterPath(book.slug, bibleChapterOrder(s.chapter), false),
				why
			}
		];
	});
}
