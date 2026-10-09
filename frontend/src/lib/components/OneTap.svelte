<script lang="ts">
	import { page } from '$app/stores';
	import { auth } from '$lib/auth.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { listen } from '$lib/listen.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { signInSheet } from '$lib/signInSheet.svelte';
	import { cancelOneTap, oneTapAllowedOn, promptOneTap } from '$lib/oneTap';

	/**
	 * When to offer Google One Tap ($lib/oneTap): a signed-out reader, on a page
	 * that doesn't already ask its own way, a few seconds after arriving so the
	 * page is read before anything is asked. Not over the sign-up panel, focus
	 * mode or Listen, the same places the layout's own prompts keep out of. And
	 * never in a page session that has been signed in: right after a sign-out
	 * (a shared device, say) it would offer the account just left.
	 * Renders nothing; the prompt is Google's (or the browser's).
	 */
	const DELAY_MS = 4000;

	let beenSignedIn = $state(false);
	$effect(() => {
		if (auth.user) beenSignedIn = true;
	});

	const wanted = $derived(
		auth.initialized &&
			!auth.user &&
			!beenSignedIn &&
			!signInSheet.open &&
			!readerUi.focus &&
			listen.status === 'idle' &&
			oneTapAllowedOn($page.url.pathname)
	);

	$effect(() => {
		if (!wanted) {
			cancelOneTap();
			return;
		}
		const timer = setTimeout(() => promptOneTap(getLang()), DELAY_MS);
		return () => clearTimeout(timer);
	});
</script>
