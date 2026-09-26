<script lang="ts">
	// Lightweight inline-SVG line icons, matching Take Root's icon set: 24-unit
	// viewBox, no fill, currentColor stroke, round caps/joins. Decorative by
	// default (aria-hidden); pass `label` for an accessible name when the icon
	// has no adjacent text.
	export type IconName =
		| 'info'
		| 'grid'
		| 'book'
		| 'calendar'
		| 'mic'
		| 'users'
		| 'mail'
		| 'search'
		| 'gear'
		| 'sun'
		| 'moon'
		| 'tag'
		| 'list'
		| 'bookmark'
		| 'headphones'
		| 'maximize'
		| 'chevron-left'
		| 'chevron-right'
		| 'play'
		| 'pause'
		| 'skip-back'
		| 'skip-forward'
		| 'close'
		| 'sparkle'
		| 'wind'
		| 'mountain'
		| 'heart'
		| 'flame'
		| 'compass'
		| 'check'
		| 'more'
		| 'download'
		| 'layers'
		| 'quote';

	let {
		name,
		size = 18,
		label,
		strokeWidth = 1.8,
		class: klass = ''
	}: {
		name: IconName;
		size?: number;
		label?: string;
		strokeWidth?: number;
		class?: string;
	} = $props();
</script>

<svg
	class={klass}
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width={strokeWidth}
	stroke-linecap="round"
	stroke-linejoin="round"
	role={label ? 'img' : undefined}
	aria-label={label}
	aria-hidden={label ? undefined : 'true'}
>
	{#if name === 'info'}
		<circle cx="12" cy="12" r="9" />
		<path d="M12 11v5" />
		<path d="M12 8h.01" />
	{:else if name === 'grid'}
		<rect x="4" y="4" width="6.5" height="6.5" rx="1.4" />
		<rect x="13.5" y="4" width="6.5" height="6.5" rx="1.4" />
		<rect x="4" y="13.5" width="6.5" height="6.5" rx="1.4" />
		<rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.4" />
	{:else if name === 'book'}
		<path d="M12 6.5C10.5 5 8 4.5 5 5v12c3-.5 5.5 0 7 1.5" />
		<path d="M12 6.5C13.5 5 16 4.5 19 5v12c-3-.5-5.5 0-7 1.5" />
		<path d="M12 6.5v12" />
	{:else if name === 'calendar'}
		<rect x="4" y="5" width="16" height="15" rx="2" />
		<path d="M8 3v4M16 3v4M4 10h16" />
	{:else if name === 'mic'}
		<rect x="9" y="3" width="6" height="11" rx="3" />
		<path d="M5 11a7 7 0 0 0 14 0" />
		<path d="M12 18v3" />
	{:else if name === 'users'}
		<circle cx="9" cy="8" r="3.2" />
		<path d="M3.5 19.5c.6-3.2 2.8-5 5.5-5s4.9 1.8 5.5 5" />
		<path d="M15.5 5.2a3.2 3.2 0 0 1 0 5.6" />
		<path d="M17.5 14.9c1.6.7 2.7 2.2 3 4.6" />
	{:else if name === 'mail'}
		<rect x="3" y="5.5" width="18" height="13" rx="2" />
		<path d="m4 7.5 8 6 8-6" />
	{:else if name === 'search'}
		<circle cx="11" cy="11" r="7" />
		<path d="m21 21-4.3-4.3" />
	{:else if name === 'gear'}
		<circle cx="12" cy="12" r="3" />
		<path
			d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56V21a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-1.11-1.56 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.56-1.03H3a2 2 0 1 1 0-4h.09A1.7 1.7 0 0 0 4.65 8.9a1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.7 1.7 0 0 0 1.87.34h.08A1.7 1.7 0 0 0 10.12 3V3a2 2 0 1 1 4 0v.09c0 .68.4 1.3 1.03 1.56a1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87v.08c.26.63.88 1.03 1.56 1.03H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.56 1.03Z"
		/>
	{:else if name === 'sun'}
		<circle cx="12" cy="12" r="4" />
		<path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
	{:else if name === 'moon'}
		<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
	{:else if name === 'tag'}
		<path d="M4 4h7l9 9-7 7-9-9V4z" />
		<circle cx="8" cy="8" r="1.4" />
	{:else if name === 'list'}
		<path d="M8.5 6.5h11M8.5 12h11M8.5 17.5h11" />
		<path d="M4.5 6.5h.01M4.5 12h.01M4.5 17.5h.01" />
	{:else if name === 'bookmark'}
		<path d="M6.5 4h11a1 1 0 0 1 1 1v15l-6.5-3.8L5.5 20V5a1 1 0 0 1 1-1z" />
	{:else if name === 'headphones'}
		<path d="M4 14v-2a8 8 0 0 1 16 0v2" />
		<path d="M4 14h2a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z" />
		<path d="M20 14h-2a1 1 0 0 0-1 1v4a1 1 0 0 0 1 1h1a1 1 0 0 0 1-1z" />
	{:else if name === 'maximize'}
		<path d="M4 9V5a1 1 0 0 1 1-1h4M20 9V5a1 1 0 0 0-1-1h-4M4 15v4a1 1 0 0 0 1 1h4M20 15v4a1 1 0 0 1-1 1h-4" />
	{:else if name === 'chevron-left'}
		<path d="M15 6l-6 6 6 6" />
	{:else if name === 'chevron-right'}
		<path d="M9 6l6 6-6 6" />
	{:else if name === 'play'}
		<path d="M8 5.5v13l11-6.5z" fill="currentColor" stroke="none" />
	{:else if name === 'pause'}
		<path d="M9 5v14M15 5v14" />
	{:else if name === 'skip-back'}
		<path d="M18 6.5v11L9.5 12zM6 5.5v13" />
	{:else if name === 'skip-forward'}
		<path d="M6 6.5v11L14.5 12zM18 5.5v13" />
	{:else if name === 'close'}
		<path d="M6 6l12 12M18 6L6 18" />
	{:else if name === 'sparkle'}
		<path d="M12 3l1.7 5.6c.2.6.6 1 1.2 1.2L20.5 11.5l-5.6 1.7c-.6.2-1 .6-1.2 1.2L12 20l-1.7-5.6c-.2-.6-.6-1-1.2-1.2L3.5 11.5l5.6-1.7c.6-.2 1-.6 1.2-1.2z" />
	{:else if name === 'wind'}
		<path d="M3 8.5h10.5A2.5 2.5 0 1 0 11 6" />
		<path d="M3 12.5h15A2.5 2.5 0 1 1 15.5 15" />
		<path d="M3 16.5h8.5A2.5 2.5 0 1 1 9 19" />
	{:else if name === 'mountain'}
		<path d="M3 20h18L14 6l-3.2 6-2.3-3z" />
		<path d="m10.8 12 1.2-2 2 4" />
	{:else if name === 'heart'}
		<path d="M12 20.5S4 15.9 4 10.3A4.3 4.3 0 0 1 12 8a4.3 4.3 0 0 1 8 2.3c0 5.6-8 10.2-8 10.2z" />
	{:else if name === 'flame'}
		<path d="M12 2c1.6 3.2 4.6 4.7 4.6 8.6a4.6 4.6 0 0 1-9.2 0c0-2 1-3.3 2.1-4.3.2 1.4 1 2.3 2 2.3 1.3 0 1.9-1.2 1.6-2.6C12.8 4.9 12 3.6 12 2z" />
	{:else if name === 'compass'}
		<circle cx="12" cy="12" r="9" />
		<path d="m15.6 8.4-2 5.2-5.2 2 2-5.2z" />
	{:else if name === 'check'}
		<path d="M5 12.5l4.5 4.5L19 7" />
	{:else if name === 'more'}
		<circle cx="5.5" cy="12" r="1.2" />
		<circle cx="12" cy="12" r="1.2" />
		<circle cx="18.5" cy="12" r="1.2" />
	{:else if name === 'download'}
		<path d="M12 4v11m-5-5 5 5 5-5M5 20h14" />
	{:else if name === 'quote'}
		<!-- A pair of opening quotation marks: the author's Quotes page. -->
		<path d="M5 17V11a4 4 0 0 1 4-4M14 17V11a4 4 0 0 1 4-4" />
		<rect x="5" y="13" width="4" height="4" rx="0.5" />
		<rect x="14" y="13" width="4" height="4" rx="0.5" />
	{:else if name === 'layers'}
		<!-- Book spines side by side: the Bookshelf's spine view. -->
		<path d="M5 4v16M9.5 4v16M14 6l4 14M3 20h18" />
	{/if}
</svg>
