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
		name: { en: 'Literal', es: 'Literal', fr: 'Littéral', pt: 'Literal', sw: 'Halisi', am: 'ቃል በቃል' },
		aim: {
			en: 'Follows the Hebrew and Greek closely, with any word it supplies in brackets: for study beside the original.',
			es: 'Sigue de cerca el hebreo y el griego, con entre corchetes toda palabra que añade: para estudiar junto al original.',
			fr: 'Suit de près l’hébreu et le grec, en mettant entre crochets tout mot ajouté : pour l’étude, à côté de l’original.',
			pt: 'Segue de perto o hebraico e o grego, com entre colchetes toda palavra que acrescenta: para estudar ao lado do original.',
			sw: 'Inafuata Kiebrania na Kigiriki kwa karibu, na kila neno inaloongeza liko ndani ya mabano: kwa kujifunza sambamba na asili.',
			am: 'ዕብራይስጡንና ግሪኩን በቅርበት ይከተላል፤ የሚጨምረውንም ቃል በቅንፍ ያስቀምጣል፦ ከመጀመሪያው ጽሑፍ ጎን ለጥናት።'
		}
	},
	{
		code: 'OWB-B',
		name: { en: 'Balanced', es: 'Equilibrado', fr: 'Équilibré', pt: 'Equilibrado', sw: 'Uwiano', am: 'ሚዛናዊ' },
		aim: {
			en: 'Accurate and natural: faithful to the original, and easy to read. This is the text you read on Ochorus.',
			es: 'Exacto y natural: fiel al original y fácil de leer. Es el texto que se lee en Ochorus.',
			fr: 'Exact et naturel : fidèle à l’original et facile à lire. C’est le texte qu’on lit sur Ochorus.',
			pt: 'Exato e natural: fiel ao original e fácil de ler. É o texto que se lê no Ochorus.',
			sw: 'Sahihi na ya kawaida: aminifu kwa asili, na rahisi kusoma. Hili ndilo andiko unalosoma katika Ochorus.',
			am: 'ትክክለኛና ተፈጥሯዊ፦ ለመጀመሪያው ጽሑፍ ታማኝ፣ ለማንበብም ቀላል። በOchorus የሚያነቡት ጽሑፍ ይህ ነው።'
		}
	},
	{
		code: 'OWB-R',
		name: { en: 'Readable', es: 'Sencillo', fr: 'Simple', pt: 'Simples', sw: 'Rahisi', am: 'ቀላል' },
		aim: {
			en: 'Plain modern language, made explicit where it helps: for a first reading, or a young reader.',
			es: 'Lenguaje moderno y sencillo, explícito donde ayuda: para una primera lectura o un lector joven.',
			fr: 'Une langue moderne et simple, explicite là où cela aide : pour une première lecture, ou un jeune lecteur.',
			pt: 'Linguagem moderna e simples, explícita onde ajuda: para uma primeira leitura ou um leitor jovem.',
			sw: 'Lugha rahisi ya kisasa, inayoeleza wazi pale inaposaidia: kwa usomaji wa kwanza, au kwa msomaji kijana.',
			am: 'ግልጽ የዘመኑ ቋንቋ፣ በሚረዳበትም ቦታ ሐሳቡን ያብራራል፦ ለመጀመሪያ ንባብ ወይም ለወጣት አንባቢ።'
		}
	}
];

/** The languages OWB is translating into, English first (its README's list),
 *  named in each hub locale. */
export const OWB_LANGUAGES: readonly BibleText[] = [
	{ en: 'English', es: 'Inglés', fr: 'Anglais', pt: 'Inglês', sw: 'Kiingereza', am: 'እንግሊዝኛ' },
	{ en: 'Spanish', es: 'Español', fr: 'Espagnol', pt: 'Espanhol', sw: 'Kihispania', am: 'ስፓኒሽ' },
	{ en: 'French', es: 'Francés', fr: 'Français', pt: 'Francês', sw: 'Kifaransa', am: 'ፈረንሳይኛ' },
	{ en: 'Swahili', es: 'Suajili', fr: 'Swahili', pt: 'Suaíli', sw: 'Kiswahili', am: 'ስዋሂሊ' },
	{ en: 'Vietnamese', es: 'Vietnamita', fr: 'Vietnamien', pt: 'Vietnamita', sw: 'Kivietinamu', am: 'ቬትናምኛ' },
	{ en: 'Korean', es: 'Coreano', fr: 'Coréen', pt: 'Coreano', sw: 'Kikorea', am: 'ኮሪያኛ' },
	{ en: 'Portuguese', es: 'Portugués', fr: 'Portugais', pt: 'Português', sw: 'Kireno', am: 'ፖርቱጋልኛ' },
	{ en: 'Amharic', es: 'Amárico', fr: 'Amharique', pt: 'Amárico', sw: 'Kiamhari', am: 'አማርኛ' },
	{ en: 'Hindi', es: 'Hindi', fr: 'Hindi', pt: 'Híndi', sw: 'Kihindi', am: 'ሂንዲ' },
	{ en: 'Russian', es: 'Ruso', fr: 'Russe', pt: 'Russo', sw: 'Kirusi', am: 'ሩሲያኛ' },
	{ en: 'Ukrainian', es: 'Ucraniano', fr: 'Ukrainien', pt: 'Ucraniano', sw: 'Kiukreni', am: 'ዩክሬንኛ' },
	{ en: 'Japanese', es: 'Japonés', fr: 'Japonais', pt: 'Japonês', sw: 'Kijapani', am: 'ጃፓንኛ' }
];

/** The three covers fanned beside the page's heading (the fan shows three):
 *  the Law, the Psalms and a Gospel, Hebrew and Greek names side by side. */
export const OWB_FAN = ['genesis', 'psalms', 'gospel-of-john'] as const;
