import { browser } from '$app/environment';
import { readJSON, writeJSON } from './persisted';
import { track } from './analytics';
import {
	EMPTY,
	INSTALL_PARAM,
	noteVisit,
	platformFor,
	shouldOffer,
	snooze,
	type InstallPlatform,
	type InstallState
} from './installPrompt';

/** Chrome's install event (not in the DOM typings). */
interface BeforeInstallPromptEvent extends Event {
	prompt(): Promise<void>;
	userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

type InstallWindow = Window & { __ochorusInstall?: BeforeInstallPromptEvent };

const KEY = 'ochorus:install';

/**
 * The "Add to home screen" offer (rules in $lib/installPrompt). `init` runs
 * once from the root layout. Chrome's install event is caught by app.html's
 * boot script, before the app has loaded, and picked up here; a later one is
 * caught here. `touch` runs on every navigation, so "30 minutes away" means
 * away, not "since the last full page load".
 */
class Install {
	platform = $state<InstallPlatform>('none');
	offer = $state(false);
	#event: BeforeInstallPromptEvent | null = null;
	#state: InstallState = EMPTY;
	#standalone = false;
	#shownTracked = false;

	init() {
		if (!browser) return;
		let s: InstallState = { ...EMPTY, ...readJSON<Partial<InstallState>>(KEY, {}) };
		// Arrived via "Open in Chrome" from an in-app browser: they asked.
		const url = new URL(window.location.href);
		if (url.searchParams.has(INSTALL_PARAM)) {
			s = { ...s, requested: true };
			url.searchParams.delete(INSTALL_PARAM);
			history.replaceState(history.state, '', url);
		}
		this.#state = noteVisit(s, Date.now());
		writeJSON(KEY, this.#state);
		this.#standalone =
			window.matchMedia?.('(display-mode: standalone)').matches ||
			(navigator as Navigator & { standalone?: boolean }).standalone === true;
		const w = window as InstallWindow;
		this.#event = w.__ochorusInstall ?? null;
		window.addEventListener('beforeinstallprompt', (e) => {
			e.preventDefault();
			this.#event = e as BeforeInstallPromptEvent;
			this.#refresh();
		});
		window.addEventListener('appinstalled', () => {
			const platform = this.platform;
			this.#save({ ...this.#state, installed: true });
			track('Install prompt', { action: 'installed', platform });
		});
		this.#refresh();
	}

	/** A page view inside the app: keeps the visit count honest. */
	touch() {
		if (!browser || this.#state === EMPTY) return;
		this.#save(noteVisit(this.#state, Date.now()));
	}

	#refresh() {
		this.platform = platformFor(navigator.userAgent, !!this.#event);
		this.offer = shouldOffer(this.#state, this.platform, this.#standalone, Date.now());
	}

	#save(s: InstallState) {
		this.#state = s;
		writeJSON(KEY, s);
		this.#refresh();
	}

	/** The card was actually drawn (once a page session). */
	shown() {
		if (this.#shownTracked) return;
		this.#shownTracked = true;
		track('Install prompt', { action: 'shown', platform: this.platform });
	}

	/** Android: open the browser's own install dialog. */
	async install() {
		const e = this.#event;
		if (!e) return;
		this.#event = null;
		(window as InstallWindow).__ochorusInstall = undefined;
		try {
			await e.prompt();
			const { outcome } = await e.userChoice;
			track('Install prompt', { action: outcome, platform: 'native' });
			if (outcome === 'accepted') this.#save({ ...this.#state, installed: true });
			else this.#save(snooze(this.#state, Date.now()));
		} catch {
			// The event was spent or refused: don't leave a dead button up.
			this.#save(snooze(this.#state, Date.now()));
		}
	}

	/** "Not now", "Got it" (iPhone steps) or "Open in Chrome": away for 30 days. */
	later(action: 'later' | 'done' | 'open_browser' = 'later') {
		track('Install prompt', { action, platform: this.platform });
		this.#save(snooze(this.#state, Date.now()));
	}
}

export const install = new Install();
