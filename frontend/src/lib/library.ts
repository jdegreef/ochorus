import { apiFetch } from './api';

export interface Author {
	slug: string;
	name: string;
	bio: string;
	birth_year: number | null;
	death_year: number | null;
}

export type SourceType = 'public_domain' | 'ai_reviewed' | 'ai_unreviewed';

export interface BookSummary {
	slug: string;
	language: string;
	title: string;
	subtitle: string;
	author: Author;
	source_type: SourceType;
	cover_color: string;
	chapter_count: number;
}

export interface ChapterToc {
	order: number;
	title: string;
	word_count: number;
}

export interface BookDetail extends BookSummary {
	description: string;
	source_url: string;
	chapters: ChapterToc[];
}

export interface ChapterNav {
	order: number;
	title: string;
}

export interface Chapter {
	order: number;
	title: string;
	body_html: string;
	word_count: number;
	book_title: string;
	book_slug: string;
	prev: ChapterNav | null;
	next: ChapterNav | null;
}

export const listBooks = (language = 'en') =>
	apiFetch<BookSummary[]>(`/api/library/books/?language=${language}`);

export const getBook = (slug: string, language = 'en') =>
	apiFetch<BookDetail>(`/api/library/books/${slug}/?language=${language}`);

export const getChapter = (slug: string, order: number, language = 'en') =>
	apiFetch<Chapter>(`/api/library/books/${slug}/chapters/${order}/?language=${language}`);
