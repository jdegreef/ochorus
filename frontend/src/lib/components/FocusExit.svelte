<script lang="ts">
	import Icon from './Icon.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { i18n } from '$lib/i18n.svelte';

	// The "Exit focus" pill, pinned top-end over a reading surface — one copy of
	// what the reader, a sermon and an author bio each pasted by hand. The CALLER
	// guards visibility (readerUi.focus, and the reader also hides it mid-peek),
	// so this is just the button.
	const t = i18n.t;
</script>

<button
	class="fixed end-4 top-4 z-30 rounded-full border border-border bg-surface/90 px-3 py-1.5 text-small text-muted shadow-md backdrop-blur hover:text-text"
	onclick={() => readerUi.exitFocus()}
>
	<Icon name="close" size={14} />
	{t('reader.exitFocus')}
</button>
