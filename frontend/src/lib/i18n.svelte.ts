import { browser } from '$app/environment';

/**
 * Lightweight UI-string i18n. This is deliberately a small in-repo dictionary
 * rather than a full ICU/Paraglide setup: the *content* (books) is the main
 * multilingual surface, and the chrome has few strings. Adding a locale = adding
 * one entry to `MESSAGES`; missing keys fall back to English, then to the key.
 *
 * The active UI locale defaults to the chosen content language but can diverge.
 */

type Dict = Record<string, string>;

const EN: Dict = {
	'nav.about': 'About Us',
	'nav.books': 'Books',
	'nav.sermons': 'Sermons',
	'nav.biographies': 'Biographies',
	'nav.contact': 'Contact',
	'nav.search': 'Search',
	'reader.focus': 'Focus',
	'reader.exitFocus': 'Exit focus',
	'reader.contents': 'Contents',
	'reader.previous': 'Previous',
	'reader.next': 'Next',
	'reader.backToContents': 'Back to contents',
	'reader.textSettings': 'Text settings',
	'reader.size': 'Size',
	'reader.spacing': 'Spacing',
	'reader.width': 'Width',
	'reader.typeface': 'Typeface',
	'reader.copyQuote': 'Copy quote',
	'reader.share': 'Share',
	'reader.highlight': 'Highlight',
	'reader.note': 'Note',
	'spacing.compact': 'Compact',
	'spacing.normal': 'Normal',
	'spacing.relaxed': 'Relaxed',
	'width.narrow': 'Narrow',
	'width.normal': 'Normal',
	'width.wide': 'Wide',
	'font.serif': 'Serif',
	'font.sans': 'Sans',
	'font.dyslexic': 'Dyslexic',
	'search.placeholder': 'Search books, authors, text…',
	'search.title': 'Search',
	'search.noResults': 'No results for',
	'search.prompt': 'Type at least two characters to search.',
	'pwa.offline': 'Offline — reading from your device',
	'pwa.ready': 'Ochorus is ready to read offline.',
	'pwa.dismiss': 'Dismiss',
	'pwa.updateReady': 'A new version is available.',
	'pwa.refresh': 'Refresh',
	'reader.listen': 'Listen',
	'reader.pause': 'Pause',
	'reader.resume': 'Resume',
	'reader.speed': 'Speed',
	'reader.voice': 'Voice',
	'reader.stopListening': 'Stop listening',
	'nav.plans': 'Plans',
	'plans.title': 'Reading Plans',
	'plans.tagline': 'A chapter a day, in order — build a habit around a classic.',
	'plans.none': 'No plans available in this language yet.',
	'plans.days': 'days',
	'plans.day': 'Day',
	'plans.of': 'of',
	'plans.start': 'Start the plan',
	'plans.continue': 'Continue',
	'plans.finished': 'Plan finished',
	'plans.today': 'Today',
	'plans.markDone': 'Mark day done',
	'plans.dayDone': 'Day complete',
	'plans.todaysReading': "Today's reading",
	'plans.all': 'All plans',
	'continue.title': 'Continue reading',
	'continue.chapter': 'Chapter',
	'account.title': 'My account',
	'account.signedInAs': 'Signed in as',
	'account.syncNote': 'your reading place, highlights and notes sync across devices.',
	'account.signedOutNote': 'Sign in (top right) to sync your reading across devices.',
	'account.localNote': 'Your reading progress is saved on this device.',
	'account.signOut': 'Sign out'
};

// Add locale dictionaries here as translations are reviewed, e.g. `sw: { ... }`.
const MESSAGES: Record<string, Dict> = { en: EN };

const KEY = 'ochorus:ui-locale';

class I18n {
	locale = $state('en');

	init(fallback = 'en') {
		if (browser) this.locale = localStorage.getItem(KEY) || fallback;
	}

	set(locale: string) {
		this.locale = locale;
		if (browser) localStorage.setItem(KEY, locale);
	}

	t = (key: string): string => {
		const dict = MESSAGES[this.locale] ?? EN;
		return dict[key] ?? EN[key] ?? key;
	};
}

export const i18n = new I18n();
