<script lang="ts">
	import GoogleMark from '$lib/components/GoogleMark.svelte';
	import { i18n } from '$lib/i18n.svelte';

	/** "Continue with Google" — one button for /login and the sign-up panel. */
	let { onclick, disabled = false }: { onclick: () => void; disabled?: boolean } = $props();
	const t = i18n.t;
</script>

<!-- A plain ghost `.btn`: it used to re-implement .btn in scoped CSS (its own
     padding, radius, fill and a 0.5 disabled opacity) and drifted from every
     other button. Google's own brand fill is not used, so it is an ordinary
     button with the G glyph. -->
<button class="btn btn-ghost w-full" data-google-signin type="button" {onclick} {disabled}>
	<GoogleMark />
	{t('login.google')}
</button>
