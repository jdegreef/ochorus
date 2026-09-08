<!--
	The loading / not-authorised / failed shell every admin page draws around its
	content, paired with `$lib/adminResource.svelte.ts`.

	Unifying it fixes a divergence, not just a duplication. The dashboard's
	denied panel distinguishes *signed out* from *signed in without access* and
	offers a Sign in button; the eight pages copied from it kept only the second
	half, so a signed-out admin who lands on /admin/review — a bookmark, a link
	from a colleague — is told they don't have access and given nothing to click.
	The good branch now runs on every page, and it returns you to the page you
	asked for rather than to /admin.
-->
<script lang="ts" generics="T">
	import type { Snippet } from 'svelte';
	import { page } from '$app/stores';
	import { localizeHref } from '$lib/paraglide/runtime';
	import { loginHref as buildLoginHref } from '$lib/loginHref';
	import { auth } from '$lib/auth.svelte';
	import type { AdminResource } from '$lib/adminResource.svelte';

	let {
		resource,
		errorTitle,
		loadingText = 'Loading…',
		loading,
		panelClass = '',
		children
	}: {
		/** The page's resource — its state decides which branch renders. */
		resource: AdminResource<T>;
		/** Heading for the failure panel, e.g. "Couldn't load users". */
		errorTitle: string;
		/** First-load copy; a few pages say something truer than "Loading…". */
		loadingText?: string;
		/** First-load placeholder — a page can pass a skeleton of its own layout
		 * instead of the bare loadingText. */
		loading?: Snippet;
		/** Extra classes for the panels — detail pages sit below a back-link. */
		panelClass?: string;
		/** The page itself, rendered with the loaded payload. */
		children: Snippet<[T]>;
	} = $props();

	// Come back here after signing in, not to the dashboard: the copied-from
	// original hard-coded /admin, which dropped you a click away from wherever
	// you were actually headed.
	const loginHref = $derived(buildLoginHref($page.url.pathname, $page.url.search));
</script>

{#if resource.loading && !resource.data}
	{#if loading}
		{@render loading()}
	{:else}
		<p class="{panelClass} text-body text-muted">{loadingText}</p>
	{/if}
{:else if resource.denied}
	<div class="{panelClass} rounded-card border border-border bg-surface p-8">
		{#if auth.enabled && !auth.user}
			<h2 class="text-h3 mb-2">Sign in required</h2>
			<p class="mb-5 text-body text-muted">
				The admin dashboard is restricted. Please sign in with an administrator account.
			</p>
			<a class="btn btn-primary" href={localizeHref(loginHref)}>Sign in</a>
		{:else}
			<h2 class="text-h3 mb-2">Not authorised</h2>
			<p class="text-body text-muted">
				{#if auth.user}This account ({auth.user.email}) doesn't have{:else}You don't have{/if}
				access to the admin dashboard.
			</p>
		{/if}
	</div>
{:else if resource.error}
	<div class="{panelClass} rounded-card border border-border bg-surface p-8">
		<h2 class="text-h3 mb-2">{errorTitle}</h2>
		<p class="mb-5 text-body text-muted">{resource.error}</p>
		<button class="btn btn-ghost" onclick={resource.load}>Try again</button>
	</div>
{:else if resource.data}
	{@render children(resource.data)}
{/if}
