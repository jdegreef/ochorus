/**
 * The Open Word Bible — the translation the library's Bible is printed in.
 *
 * Like Ochorus Originals (`$lib/originals`) it is a byline, not a person
 * (`Author.is_imprint`): the Bible's 66 books are "by" it, but it has no life
 * to tell, so its name links to a page about the translation, /open-word-bible,
 * rather than to an author page with a monogram (`authorPath`). The books
 * themselves live on the Bible hub, /bible ($lib/bible).
 */
import type { BibleText } from './bibleLocales';

export const OWB_SLUG = 'open-word-bible';
export const OWB_PATH = '/open-word-bible';
/** The translation's own home: every sentence's reasoning, every level. */
export const OWB_URL = 'https://openwordbible.org';
export const OWB_READ_URL = 'https://openwordbible.org/read/';

/** The three levels OWB translates every sentence at; Ochorus prints Balanced.
 *  Named and described in each hub locale, for the /open-word-bible page. */
export const OWB_LEVELS: readonly { code: 'OWB-L' | 'OWB-B' | 'OWB-R'; name: BibleText; aim: BibleText }[] = [
	{
		code: 'OWB-L',
		name: { en: 'Literal', es: 'Literal', fr: 'Littéral', pt: 'Literal' },
		aim: {
			en: 'Follows the Hebrew and Greek closely, with any word it supplies in brackets: for study beside the original.',
			es: 'Sigue de cerca el hebreo y el griego, con entre corchetes toda palabra que añade: para estudiar junto al original.',
			fr: 'Suit de près l’hébreu et le grec, en mettant entre crochets tout mot ajouté : pour l’étude, à côté de l’original.',
			pt: 'Segue de perto o hebraico e o grego, com entre colchetes toda palavra que acrescenta: para estudar ao lado do original.'
		}
	},
	{
		code: 'OWB-B',
		name: { en: 'Balanced', es: 'Equilibrado', fr: 'Équilibré', pt: 'Equilibrado' },
		aim: {
			en: 'Accurate and natural: faithful to the original, and easy to read. This is the text you read on Ochorus.',
			es: 'Exacto y natural: fiel al original y fácil de leer. Es el texto que se lee en Ochorus.',
			fr: 'Exact et naturel : fidèle à l’original et facile à lire. C’est le texte qu’on lit sur Ochorus.',
			pt: 'Exato e natural: fiel ao original e fácil de ler. É o texto que se lê no Ochorus.'
		}
	},
	{
		code: 'OWB-R',
		name: { en: 'Readable', es: 'Sencillo', fr: 'Simple', pt: 'Simples' },
		aim: {
			en: 'Plain modern language, made explicit where it helps: for a first reading, or a young reader.',
			es: 'Lenguaje moderno y sencillo, explícito donde ayuda: para una primera lectura o un lector joven.',
			fr: 'Une langue moderne et simple, explicite là où cela aide : pour une première lecture, ou un jeune lecteur.',
			pt: 'Linguagem moderna e simples, explícita onde ajuda: para uma primeira leitura ou um leitor jovem.'
		}
	}
];

/** The languages OWB is translating into, English first (its README's list),
 *  named in each hub locale. */
export const OWB_LANGUAGES: readonly BibleText[] = [
	{ en: 'English', es: 'Inglés', fr: 'Anglais', pt: 'Inglês' },
	{ en: 'Spanish', es: 'Español', fr: 'Espagnol', pt: 'Espanhol' },
	{ en: 'French', es: 'Francés', fr: 'Français', pt: 'Francês' },
	{ en: 'Swahili', es: 'Suajili', fr: 'Swahili', pt: 'Suaíli' },
	{ en: 'Vietnamese', es: 'Vietnamita', fr: 'Vietnamien', pt: 'Vietnamita' },
	{ en: 'Korean', es: 'Coreano', fr: 'Coréen', pt: 'Coreano' },
	{ en: 'Portuguese', es: 'Portugués', fr: 'Portugais', pt: 'Português' },
	{ en: 'Amharic', es: 'Amárico', fr: 'Amharique', pt: 'Amárico' },
	{ en: 'Hindi', es: 'Hindi', fr: 'Hindi', pt: 'Híndi' },
	{ en: 'Russian', es: 'Ruso', fr: 'Russe', pt: 'Russo' },
	{ en: 'Ukrainian', es: 'Ucraniano', fr: 'Ukrainien', pt: 'Ucraniano' },
	{ en: 'Japanese', es: 'Japonés', fr: 'Japonais', pt: 'Japonês' }
];

/** The three covers fanned beside the page's heading (the fan shows three):
 *  the Law, the Psalms and a Gospel, Hebrew and Greek names side by side. */
export const OWB_FAN = ['genesis', 'psalms', 'gospel-of-john'] as const;
