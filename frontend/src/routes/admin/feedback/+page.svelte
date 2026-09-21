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
	const STATUSES = ['new', ...FEEDBACK_TRIAGE_STATUSES] as const;

	let statusFilter = $state('');
	let categoryFilter = $state('');

	const queue = adminResource(
		() =>
			getFeedbackQueue({
				status: statusFilter || undefined,
				category: categoryFilter || undefined
			}),
		"Couldn't load the feedback queue",
		() => `${statusFilter}|${categoryFilter}`
	);

	// Per-row edit + request state, keyed by item id.
	const busy = $state<Record<number, boolean>>({});
	const rowError = $state<Record<number, string>>({});
	const noteDraft = $state<Record<number, string>>({});

	function canAct() {
		return auth.can('feedback', 'act');
	}

	async function triage(item: FeedbackItem, body: Parameters<typeof triageFeedback>[1]) {
		busy[item.id] = true;
		rowError[item.id] = '';
		try {
			const updated = await triageFeedback(item.id, body);
			// Reflect the change locally so the row updates without a full reload.
			Object.assign(item, updated);
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
								<span class="ms-auto">{new Date(item.created_at).toLocaleDateString()}</span>
							</div>

							<p class="mb-3 whitespace-pre-wrap text-body">{item.body}</p>

							{#if item.page_url}
								<a
									class="mb-3 block truncate text-small text-accent"
									href={item.page_url}
									target="_blank"
									rel="noopener">{item.page_url}</a
								>
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
