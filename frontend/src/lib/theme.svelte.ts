import { browser } from '$app/environment';

type Mode = 'dark' | 'light';

class Theme {
	current = $state<Mode>('dark');

	init() {
		if (!browser) return;
		const saved = localStorage.getItem('theme');
		this.current = saved === 'light' ? 'light' : 'dark';
		this.#apply();
	}

	toggle() {
		this.current = this.current === 'dark' ? 'light' : 'dark';
		if (browser) localStorage.setItem('theme', this.current);
		this.#apply();
	}

	#apply() {
		if (browser) document.documentElement.setAttribute('data-theme', this.current);
	}
}

export const theme = new Theme();
