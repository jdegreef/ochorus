/**
 * The Open Word Bible — the translation the library's Bible is printed in.
 *
 * Like Ochorus Originals (`$lib/originals`) it is a byline, not a person
 * (`Author.is_imprint`): the Bible's 66 books are 'by' it, but it has no life
 * to tell, so its name links to a page about the translation, /open-word-bible,
 * rather than to an author page with a monogram (`authorPath`). The books
 * themselves live on the Bible hub, /bible ($lib/bible).
 */
export const OWB_SLUG = 'open-word-bible';
export const OWB_PATH = '/open-word-bible';
/** The translation's own home: every sentence's reasoning, every level. */
export const OWB_URL = 'https://openwordbible.org';
export const OWB_READ_URL = 'https://openwordbible.org/read/';

/** The three levels OWB translates every sentence at; Ochorus prints Balanced. */
export const OWB_LEVELS = [
	{
		code: 'OWB-L',
		name: 'Literal',
		aim: 'Follows the Hebrew and Greek closely, with any word it supplies in brackets: for study beside the original.'
	},
	{
		code: 'OWB-B',
		name: 'Balanced',
		aim: 'Accurate and natural: faithful to the original, and easy to read. This is the text you read on Ochorus.'
	},
	{
		code: 'OWB-R',
		name: 'Readable',
		aim: 'Plain modern language, made explicit where it helps: for a first reading, or a young reader.'
	}
] as const;

/** The languages OWB is translating into, English first (its README's list). */
export const OWB_LANGUAGES = [
	'English',
	'Spanish',
	'French',
	'Swahili',
	'Vietnamese',
	'Korean',
	'Portuguese',
	'Amharic',
	'Hindi',
	'Russian',
	'Ukrainian',
	'Japanese'
] as const;

/** The three covers fanned beside the page's heading (the fan shows three):
 *  the Law, the Psalms and a Gospel, Hebrew and Greek names side by side. */
export const OWB_FAN = ['genesis', 'psalms', 'gospel-of-john'] as const;
