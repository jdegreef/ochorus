import { browser } from '$app/environment';
import { readJSON, writeJSON } from './persisted';
import { track } from './analytics';
import {
	EMPTY,
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

const KEY = 'ochorus:install';

/**
 * The "Add to home screen" offer (rules in $lib/installPrompt). `init` runs
 * once from the root layout: it counts the visit, catches Chrome's install
 * event (so the browser's own mini-infobar doesn't fire at a random moment),
 * and notes an install however it happened.
 */
class Install {
	platform = $state<InstallPlatform>('none');
	offer = $state(false);
	#event: BeforeInstallPromptEvent | null = null;
	#state: InstallState = EMPTY;
	#standalone = false;

	init() {
		if (!browser) return;
		this.#state = noteVisit({ ...EMPTY, ...readJSON<Partial<InstallState>>(KEY, {}) }, Date.now());
		writeJSON(KEY, this.#state);
		this.#standalone =
			window.matchMedia?.('(display-mode: standalone)').matches ||
			(navigator as Navigator & { standalone?: boolean }).standalone === true;
		window.addEventListener('beforeinstallprompt', (e) => {
			e.preventDefault();
			this.#event = e as BeforeInstallPromptEvent;
			this.#refresh();
		});
		window.addEventListener('appinstalled', () => {
			this.#save({ ...this.#state, installed: true });
			track('Install prompt', { action: 'installed', platform: this.platform });
		});
		this.#refresh();
	}

	#refresh() {
		this.platform = platformFor(navigator.userAgent, !!this.#event);
		const was = this.offer;
		this.offer = shouldOffer(this.#state, this.platform, this.#standalone, Date.now());
		if (this.offer && !was) track('Install prompt', { action: 'shown', platform: this.platform });
	}

	#save(s: InstallState) {
		this.#state = s;
		writeJSON(KEY, s);
		this.#refresh();
	}

	/** Android: open the browser's own install dialog. */
	async install() {
		const e = this.#event;
		if (!e) return;
		this.#event = null;
		await e.prompt();
		const { outcome } = await e.userChoice;
		track('Install prompt', { action: outcome, platform: 'native' });
		if (outcome === 'accepted') this.#save({ ...this.#state, installed: true });
		else this.#save(snooze(this.#state, Date.now()));
	}

	/** "Not now": away for 30 days. */
	later() {
		track('Install prompt', { action: 'later', platform: this.platform });
		this.#save(snooze(this.#state, Date.now()));
	}
}

export const install = new Install();
