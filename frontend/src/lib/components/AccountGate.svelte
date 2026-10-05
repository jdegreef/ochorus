<!--
	The reader's own pages — My Bookshelf and My Notebook — are signed-in only.
	A signed-out reader is sent to the "create account" form, which pitches the
	page they asked for beside it (LoginPitch), and comes back to the same URL,
	query included (`/notebook?view=prayers`), after signing in.

	Nothing gathered signed-out is lost on the way: hearts, progress, marks and
	journal entries are device-local and merge into the account on sign-in
	(readingSync's mergeOnSignIn). With auth unconfigured (local dev) there is no
	account to ask for, so the page stays open.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { auth } from '$lib/auth.svelte';
	import { localizeHref } from '$lib/href';
	import { loginHref, withSignup } from '$lib/loginHref';

	let { children }: { children: Snippet } = $props();

	$effect(() => {
		if (auth.enabled && auth.initialized && !auth.user) {
			const href = withSignup(loginHref($page.url.pathname, $page.url.search));
			void goto(localizeHref(href), { replaceState: true });
		}
	});
</script>

<!-- Hidden until the session resolves, so a signed-out reader never sees the
     page flash before the redirect. -->
{#if !auth.enabled || auth.user}
	{@render children()}
{/if}
