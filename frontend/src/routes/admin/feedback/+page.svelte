<script lang="ts">
	/**
	 * The reader-feedback queue. Read what people submitted, filter by status and
	 * category, and triage one item — change its status, note it, or take it.
	 *
	 * Same shape as the review queue: an `adminResource` behind an `AdminGate`,
	 * with per-row action state. Gating is UX only — the Django API
	 * (`RequireCapability` on `feedback`) enforces every request.
	 */
	import { ApiError } from '$lib/api';
	import { auth } from '$lib/auth.svelte';
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import {
		getFeedbackQueue,
		triageFeedback,
		FEEDBACK_TRIAGE_STATUSES,
		type FeedbackItem
	} from '$lib/library-admin';

	const CATEGORIES = ['language', 'content', 'feature', 'bug', 'other'] as const;
	const SOURCES = ['menu', 'fab', 'highlight'] as const;
	const SOURCE_LABEL: Record<string, string> = {
		menu: 'account menu',
		fab: 'floating button',
		highlight: 'highlighted text'
	};
	const STATUSES = ['new', ...FEEDBACK_TRIAGE_STATUSES] as const;

	let statusFilter = $state('');
	let categoryFilter = $state('');
	let sourceFilter = $state('');

	const queue = adminResource(
		() =>
			getFeedbackQueue({
				status: statusFilter || undefined,
				category: categoryFilter || undefined,
				source: sourceFilter || undefined
			}),
		"Couldn't load the feedback queue",
		() => `${statusFilter}|${categoryFilter}|${sourceFilter}`
	);

	// Per-row edit + request state, keyed by item id.
	const busy = $state<Record<number, boolean>>({});
	const rowError = $state<Record<number, string>>({});
	const noteDraft = $state<Record<number, string>>({});

	function canAct() {
		return auth.can('feedback', 'act');
	}

	// Only http(s) URLs are safe to render as a clickable link — a stored
	// javascript:/data: page_url would be an XSS sink when an admin clicks it.
	// (The backend also sanitises on ingest; this is defence in depth.)
	function safeHref(u: string): string {
		return /^https?:\/\//i.test(u) ? u : '';
	}

	// A deep-link back to the flagged passage in its own language (the reader
	// route consumes ?p= to jump to the block). Books have a chapter order;
	// sermons are a single page.
	function spotHref(item: FeedbackItem): string {
		if (!item.content_slug) return '';
		const prefix = item.content_language && item.content_language !== 'en' ? `/${item.content_language}` : '';
		const at = item.anchor_block != null ? `?p=${item.anchor_block}` : '';
		if (item.content_kind === 'book' && item.chapter_ref) {
			return `${prefix}/books/${item.content_slug}/${item.chapter_ref}${at}`;
		}
		if (item.content_kind === 'sermon') return `${prefix}/sermons/${item.content_slug}${at}`;
		return '';
	}

	async function triage(item: FeedbackItem, body: Parameters<typeof triageFeedback>[1]) {
		busy[item.id] = true;
		rowError[item.id] = '';
		try {
			const updated = await triageFeedback(item.id, body);
			// Reflect the change locally for instant feedback, then reload so the
			// status counts and the active filter reconcile (a triaged item may no
			// longer match the current filter).
			Object.assign(item, updated);
			void queue.load();
		} catch (e) {
			rowError[item.id] =
				e instanceof ApiError && e.body && typeof e.body === 'object' && 'detail' in e.body
					? String((e.body as { detail: unknown }).detail)
					: e instanceof ApiError
						? e.message
						: 'Something went wrong.';
		} finally {
			busy[item.id] = false;
		}
	}

	function label(s: string) {
		return s.replace(/_/g, ' ');
	}
</script>

<svelte:head>
	<title>Admin · Feedback — Ochorus</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="mx-auto max-w-4xl px-5 py-10">
	<h1 class="mb-1 text-h2">Reader feedback</h1>
	<p class="mb-6 text-body text-muted">
		Suggestions from readers and language admins. Triage each one; changes are audited.
	</p>

	<AdminGate resource={queue} errorTitle="Couldn't load the feedback queue">
		{#snippet children(data)}
			<!-- Status filter chips, with counts. -->
			<div class="mb-5 flex flex-wrap items-center gap-2">
				<button
					class="btn btn-sm"
					class:btn-primary={statusFilter === ''}
					onclick={() => (statusFilter = '')}>All ({data.total})</button
				>
				{#each STATUSES as s (s)}
					{#if data.counts[s]}
						<button
							class="btn btn-sm"
							class:btn-primary={statusFilter === s}
							onclick={() => (statusFilter = s)}>{label(s)} ({data.counts[s]})</button
						>
					{/if}
				{/each}
				<select class="field ms-auto" bind:value={categoryFilter} aria-label="Filter by category">
					<option value="">All types</option>
					{#each CATEGORIES as c (c)}
						<option value={c}>{c}</option>
					{/each}
				</select>
				<select class="field" bind:value={sourceFilter} aria-label="Filter by source">
					<option value="">Any source</option>
					{#each SOURCES as s (s)}
						<option value={s}>{SOURCE_LABEL[s]}</option>
					{/each}
				</select>
			</div>

			{#if data.items.length === 0}
				<p class="rounded-card border border-border bg-surface p-8 text-body text-muted">
					Nothing here.
				</p>
			{:else}
				<ul class="space-y-4">
					{#each data.items as item (item.id)}
						<li class="rounded-card border border-border bg-surface p-4">
							<div class="mb-2 flex flex-wrap items-center gap-2 text-small text-muted">
								<span class="rounded border border-border px-2 py-0.5 font-medium text-text"
									>{item.category}</span
								>
								{#if item.submitter_role}
									<span
										class="rounded border border-accent-soft-border bg-accent-soft px-2 py-0.5 font-medium text-accent"
										>{label(item.submitter_role)}</span
									>
								{/if}
								<span>{item.submitter_email}</span>
								{#if item.content_slug}
									<span>· {item.content_kind}: {item.content_slug}{item.content_language
											? ` (${item.content_language})`
											: ''}{item.chapter_ref ? ` · ch. ${item.chapter_ref}` : ''}</span>
								{/if}
								{#if item.similar}
									<span class="rounded bg-accent-soft px-2 py-0.5 font-medium text-accent"
										>{item.similar} similar</span
									>
								{/if}
								<span class="ms-auto">{new Date(item.created_at).toLocaleDateString()}</span>
							</div>

							<p class="mb-3 whitespace-pre-wrap text-body">{item.body}</p>

							{#if item.selected_text}
								<blockquote
									class="mb-2 border-s-2 border-accent bg-accent-soft px-3 py-1.5 text-small italic text-text"
									>{item.selected_text}</blockquote
								>
								{#if item.suggested_text}
									<p class="mb-2 text-small">
										<span class="font-medium text-text">Suggested:</span>
										<span class="whitespace-pre-wrap">{item.suggested_text}</span>
									</p>
								{/if}
								{#if spotHref(item)}
									<a
										class="mb-3 inline-block text-small text-accent"
										href={spotHref(item)}
										target="_blank"
										rel="noopener noreferrer">Open the passage →</a
									>
								{/if}
							{/if}

							{#if safeHref(item.page_url)}
								<a
									class="mb-3 block truncate text-small text-accent"
									href={safeHref(item.page_url)}
									target="_blank"
									rel="noopener noreferrer">{item.page_url}</a
								>
							{:else if item.page_url}
								<p class="mb-3 truncate text-small text-muted">{item.page_url}</p>
							{/if}

							{#if canAct()}
								<div class="flex flex-wrap items-center gap-2 border-t border-border pt-3">
									<label class="text-small text-muted">
										Status
										<select
											class="field ms-1"
											value={item.status}
											disabled={busy[item.id]}
											onchange={(e) =>
												triage(item, { status: (e.currentTarget as HTMLSelectElement).value })}
										>
											{#each STATUSES as s (s)}
												<option value={s}>{label(s)}</option>
											{/each}
										</select>
									</label>
									{#if item.assignee_email}
										<span class="text-small text-muted">→ {item.assignee_email}</span>
									{:else if auth.user}
										<button
											class="btn btn-sm"
											disabled={busy[item.id]}
											onclick={() => triage(item, { assignee_email: auth.user!.email })}
											>Assign to me</button
										>
									{/if}
								</div>

								<div class="mt-2 flex items-start gap-2">
									<textarea
										class="field w-full"
										rows="1"
										placeholder="Add a note…"
										value={noteDraft[item.id] ?? item.admin_note}
										oninput={(e) =>
											(noteDraft[item.id] = (e.currentTarget as HTMLTextAreaElement).value)}
									></textarea>
									<button
										class="btn btn-sm btn-primary"
										disabled={busy[item.id]}
										onclick={() => triage(item, { admin_note: noteDraft[item.id] ?? item.admin_note })}
										>Save note</button
									>
								</div>
							{:else if item.admin_note}
								<p class="border-t border-border pt-3 text-small text-muted">{item.admin_note}</p>
							{/if}

							{#if rowError[item.id]}
								<p class="mt-2 text-small text-danger">{rowError[item.id]}</p>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		{/snippet}
	</AdminGate>
</div>
