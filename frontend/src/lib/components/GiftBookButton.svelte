<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import ModalShell from '$lib/components/ModalShell.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { SITE_URL } from '$lib/config';
	import { track } from '$lib/analytics';
	import {
		GIFT_CREATED_EVENT,
		GIFT_NAME_MAX,
		GIFT_NOTE_MAX,
		cleanGiftName,
		cleanGiftNote,
		giftCap,
		giftHash,
		giftLength
	} from '$lib/gift';

	/**
	 * The book page's "Give this book": a small sheet that takes the giver's
	 * first name and a short note and turns them into a gift link ($lib/gift),
	 * sent through the page's own share control (the OS share sheet in the
	 * app and on phones — $lib/platform — else copy / WhatsApp / email).
	 *
	 * Nothing is stored anywhere: the link carries the gift in its fragment.
	 * Sits in the `.action-strip` like Share: icon-only in the wide row, an
	 * icon over a short label ("Give") in the narrow strip.
	 */
	interface Props {
		slug: string;
		language: string;
		title: string;
	}
	let { slug, language, title }: Props = $props();
	const t = i18n.t;
	const headingId = $props.id();

	let open = $state(false);
	let name = $state('');
	let note = $state('');

	const cleanName = $derived(cleanGiftName(name));
	const cleanNote = $derived(cleanGiftNote(note));
	const left = $derived(GIFT_NOTE_MAX - giftLength(note));
	// SITE_URL, not location.origin: in the app the origin is capacitor://.
	const link = $derived(
		cleanName.text
			? `${SITE_URL}${localizeHref('/gift')}${giftHash({ slug, lang: language, name: cleanName.text, note: cleanNote.text })}`
			: ''
	);
	const shareTitle = $derived(t('gift.shareTitle').replace('%t%', () => title));

	// Typing past a cap keeps what fits (graphemes, so an emoji isn't halved).
	const capName = () => (name = giftCap(name, GIFT_NAME_MAX));
	const capNote = () => (note = giftCap(note, GIFT_NOTE_MAX));
</script>

<button
	type="button"
	class="btn btn-sm btn-ghost"
	onclick={() => (open = true)}
	aria-haspopup="dialog"
	aria-label={t('gift.give')}
	title={t('gift.give')}
>
	<Icon name="gift" size={18} strokeWidth={1.7} />
	<span class="btn-label">{t('gift.giveShort')}</span>
</button>

{#if open}
	<ModalShell onClose={() => (open = false)} ariaLabelledby={headingId} width="28rem">
		<h2 id={headingId} class="mb-1 text-h3">{t('gift.give')}</h2>
		<p class="mb-4 text-small text-muted">{t('gift.intro')}</p>

		<label class="mb-3 block">
			<span class="mb-1 block text-small text-muted">{t('gift.nameLabel')}</span>
			<input
				class="field w-full"
				type="text"
				dir="auto"
				autocomplete="given-name"
				bind:value={name}
				oninput={capName}
			/>
		</label>

		<label class="block">
			<span class="mb-1 block text-small text-muted">{t('gift.noteLabel')}</span>
			<textarea
				class="field w-full"
				rows="4"
				dir="auto"
				placeholder={t('gift.notePlaceholder')}
				bind:value={note}
				oninput={capNote}
			></textarea>
		</label>
		<p class="mt-1 text-small text-muted" aria-live="polite">
			{t('gift.charsLeft').replace('%n%', String(Math.max(0, left)))}
			{#if cleanNote.removedLinks || cleanName.removedLinks}
				<span class="block">{t('gift.linksRemoved')}</span>
			{/if}
		</p>

		<div class="mt-4 flex flex-wrap items-center gap-3">
			{#if link}
				<ShareButton
					url={link}
					title={shareTitle}
					label={t('gift.send')}
					showLabel
					size="md"
					onshare={() => track(GIFT_CREATED_EVENT, { language })}
				/>
			{:else}
				<p class="text-small text-muted">{t('gift.nameNeeded')}</p>
			{/if}
			<button type="button" class="btn btn-ghost ms-auto" onclick={() => (open = false)}>
				{t('a11y.close')}
			</button>
		</div>
	</ModalShell>
{/if}
