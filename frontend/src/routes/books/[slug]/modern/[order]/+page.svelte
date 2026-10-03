<script lang="ts">
	// The same reading surface as the original edition; `data.edition` is what
	// switches it to Modern English (canonical, links, marks).
	import ChapterPage from '../../[order]/+page.svelte';

	let { data } = $props();
</script>

<ChapterPage {data} />
