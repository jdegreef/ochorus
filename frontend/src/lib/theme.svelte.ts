import { browser } from '$app/environment';

type Mode = 'dark' | 'light';

class Theme {
	current = $state<Mode>('light');

	init() {
		if (!browser) return;
		const saved = localStorage.getItem('theme');
		this.current = saved === 'dark' ? 'dark' : 'light';
		this.#apply();
	}

	toggle() {
		this.set(this.current === 'dark' ? 'light' : 'dark');
	}

	set(mode: Mode) {
		this.current = mode;
		if (browser) localStorage.setItem('theme', this.current);
		this.#apply();
	}

	#apply() {
		if (browser) document.documentElement.setAttribute('data-theme', this.current);
	}
}

export const theme = new Theme();
