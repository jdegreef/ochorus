/*
 * Ochorus "Today" widget for church websites — https://ochorus.com/for/churches/
 *
 *   <script src="https://ochorus.com/embed.js" data-widget="today" data-lang="en" async></script>
 *
 * Puts today's verse, reading and sermon from Ochorus where the tag is, as a
 * lazy iframe of /embed/today. Options, all optional:
 *   data-lang    a language code Ochorus is in (en, es, fr, sw, lg, …); default en
 *   data-theme   light (default), dark, sepia, or auto (follows the visitor's device)
 *   data-height  the starting height in pixels; the widget then sizes itself
 *
 * No cookies, no ads and nothing personal: the widget's views and clicks are
 * counted with the same cookieless, anonymous analytics (Plausible) as
 * ochorus.com itself, and no sign-in or reader data is ever loaded inside it.
 * Source and documentation: frontend/src/lib/embed.ts.
 */
(function () {
	'use strict';
	var HEIGHT_MESSAGE = 'ochorus:embed-height'; // = EMBED_HEIGHT_MESSAGE in $lib/embed
	var THEMES = { light: 1, dark: 1, sepia: 1, auto: 1 };
	// Shared by every copy of this file a page loads, so one listener sizes all.
	var frames = window.__ochorusEmbedFrames || (window.__ochorusEmbedFrames = []);

	function originOf(src) {
		try {
			return new URL(src, location.href).origin;
		} catch (_e) {
			return 'https://ochorus.com';
		}
	}

	function mount(script) {
		script.setAttribute('data-ochorus-mounted', '');
		if ((script.getAttribute('data-widget') || 'today') !== 'today') return;
		var origin = originOf(script.src);
		var lang = (script.getAttribute('data-lang') || 'en').toLowerCase();
		if (!/^[a-z]{2,3}$/.test(lang)) lang = 'en';
		var theme = (script.getAttribute('data-theme') || 'light').toLowerCase();
		if (!THEMES[theme]) theme = 'light';
		var height = parseInt(script.getAttribute('data-height') || '', 10);

		var frame = document.createElement('iframe');
		frame.src =
			origin + (lang === 'en' ? '' : '/' + lang) + '/embed/today' + (theme === 'light' ? '' : '?theme=' + theme);
		frame.title = 'Today from Ochorus';
		frame.setAttribute('loading', 'lazy');
		// Links open ochorus.com in a new tab; the widget can never navigate the
		// church's own page.
		frame.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox');
		frame.style.cssText =
			'display:block;width:100%;max-width:100%;border:0;background:transparent;height:' +
			(height > 0 ? height : 420) +
			'px';
		// The same color-scheme as the page inside, or the browser paints the
		// frame opaque and the card's rounded corners show a square backdrop.
		frame.style.colorScheme = theme === 'dark' ? 'dark' : theme === 'auto' ? 'light dark' : 'light';
		script.parentNode.insertBefore(frame, script.nextSibling);
		frames.push({ frame: frame, origin: origin });
	}

	// Every tag on the page, once each: a page may carry two widgets, or load
	// this file twice.
	var scripts = document.querySelectorAll('script[data-widget]:not([data-ochorus-mounted])');
	for (var i = 0; i < scripts.length; i++) {
		if (/\/embed\.js(\?|#|$)/.test(scripts[i].src)) mount(scripts[i]);
	}

	if (window.__ochorusEmbedListening) return;
	window.__ochorusEmbedListening = true;
	window.addEventListener('message', function (e) {
		var data = e.data;
		if (!data || data.type !== HEIGHT_MESSAGE || typeof data.height !== 'number') return;
		var all = window.__ochorusEmbedFrames;
		for (var j = 0; j < all.length; j++) {
			var f = all[j];
			if (e.source === f.frame.contentWindow && e.origin === f.origin) {
				f.frame.style.height = Math.max(120, Math.min(2000, Math.ceil(data.height))) + 'px';
			}
		}
	});
})();
