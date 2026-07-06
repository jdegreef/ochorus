<script lang="ts">
	// The Ochorus mark — an open book with a quill rising from its pages, echoing
	// the ochorus.com logo in the app's line-icon style (currentColor stroke, so
	// it works in both themes). Decorative: always paired with the wordmark.
	let { size = 24 }: { size?: number } = $props();
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width="1.6"
	stroke-linecap="round"
	stroke-linejoin="round"
	aria-hidden="true"
>
	<!-- quill: a feather rising from the page, tip to the upper-left -->
	<path d="M12.4 13.6C11 8.9 8.2 5.5 4 3.4c4.7-.5 8.2 1.3 10.4 5.6" />
	<path d="M12.4 13.6l-.4 2.6" />
	<!-- open book -->
	<path d="M3 19.6c3-.8 6-.6 9 .8 3-1.4 6-1.6 9-.8" />
	<path d="M3 19.6v-5c2-.5 4-.5 6-.1" />
	<path d="M21 19.6v-5c-2-.5-4-.5-6 0" />
	<path d="M12 16.2v4.2" />
</svg>
