<script lang="ts">
	import type { BookDetail } from '$lib/library-public';
	import { plateDate, plateName, plateStyle } from '$lib/bookplate';
	import { getProgressRecord } from '$lib/progress';
	import { auth } from '$lib/auth.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { withSignup } from '$lib/loginHref';
	import { seenOnView, withSource } from '$lib/signupSource';
	import { openFrom } from '$lib/signInSheet.svelte';
	import Arrow from '$lib/components/Arrow.svelte';
	import Bookplate from '$lib/components/Bookplate.svelte';
	import BookplateNameField from '$lib/components/BookplateNameField.svelte';
	import BookplateSave from '$lib/components/BookplateSave.svelte';

	/**
	 * The finish panel's bookplate (BookFinished): this book, made out to the
	 * reader, dated the day they finished it. A plate needs a name, and the
	 * name is the account's — so a signed-out reader sees the plate with its
	 * name line blank and an offer to sign in to keep it, never a wall: the
	 * finished moment is theirs either way. Signed in without a display name,
	 * they write one on the blank line.
	 *
	 * `ticks` re-reads the finish stamp when a sync brings the account's in.
	 */
	let { book, ticks = 0 }: { book: BookDetail; ticks?: number } = $props();
	const t = i18n.t;

	const name = $derived(auth.user ? plateName(auth.displayName) : null);
	const at = $derived.by(() => {
		void ticks;
		return getProgressRecord(book.slug)?.finished_at ?? Date.now();
	});
	const date = $derived(plateDate(at, getLang()));
	const style = $derived(plateStyle(book.author, book.slug));
	const signupHref = $derived(withSource(withSignup(localizeHref('/login')), 'bookplate'));
</script>

{#if auth.initialized}
	<section class="mt-8" aria-labelledby="bookplate-h">
		<h3 id="bookplate-h" class="eyebrow text-gold">{t('bookplate.heading')}</h3>
		<div class="mt-3">
			<Bookplate {name} title={book.title} author={book.author.name} {date} {style} lang={book.language}>
				{#snippet blank()}
					{#if auth.user}
						<BookplateNameField />
					{:else}
						<span class="blank-line"><span class="sr-only">{t('bookplate.yourName')}</span></span>
					{/if}
				{/snippet}
			</Bookplate>
		</div>
		{#if name}
			<div class="mt-4 flex flex-wrap items-center justify-center gap-3">
				<BookplateSave slug={book.slug} {name} title={book.title} author={book.author.name} {date} {style} />
				<a class="text-small text-muted hover:text-accent" href="{localizeHref('/favorites')}#bookplates"
					>{t('bookplate.all')} <Arrow /></a
				>
			</div>
		{:else if !auth.user && auth.enabled}
			<div class="keep mt-4">
				<p class="font-semibold text-text">{t('bookplate.keepTitle')}</p>
				<p class="text-small text-muted">{t('bookplate.keepBody')}</p>
				<a
					class="btn btn-primary btn-sm mt-3"
					href={signupHref}
					use:seenOnView={'bookplate'}
					onclick={(e) => openFrom(e, 'bookplate')}>{t('login.createAccountLink')}</a
				>
			</div>
		{/if}
	</section>
{/if}

<style>
	/* An unwritten plate's name line: a rule waiting for a hand. */
	.blank-line {
		display: block;
		width: 70%;
		height: 2.25rem;
		margin-inline: auto;
		border-bottom: 1px dashed color-mix(in srgb, var(--text) 45%, transparent);
	}
	.keep {
		max-width: 26rem;
		margin-inline: auto;
	}
</style>
