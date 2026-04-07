import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';

// vi.mock factories are hoisted — declare mocks with vi.hoisted so they
// exist before the factories run.
const { mockHtml, mockCss, MockEditorView, MockEditorState } = vi.hoisted(() => {
	const mockHtml = vi.fn(() => 'html-ext');
	const mockCss = vi.fn(() => 'css-ext');
	const MockEditorView = vi.fn().mockImplementation(function () { return { destroy: vi.fn() }; });
	(MockEditorView as unknown as Record<string, unknown>).updateListener = {
		of: vi.fn((cb: unknown) => cb),
	};
	const MockEditorState = { create: vi.fn((opts: unknown) => opts) };
	return { mockHtml, mockCss, MockEditorView, MockEditorState };
});

vi.mock('codemirror', () => ({ basicSetup: [] }));
vi.mock('@codemirror/view', () => ({ EditorView: MockEditorView }));
vi.mock('@codemirror/state', () => ({ EditorState: MockEditorState }));
vi.mock('@codemirror/lang-html', () => ({ html: mockHtml }));
vi.mock('@codemirror/lang-css', () => ({ css: mockCss }));

import Editor from './Editor.svelte';

beforeEach(() => {
	vi.clearAllMocks();
	(MockEditorView as ReturnType<typeof vi.fn>).mockImplementation(function () { return { destroy: vi.fn() }; });
});

describe('Editor.svelte', () => {
	it('mounts a CodeMirror EditorView on mount', () => {
		render(Editor, { language: 'html', value: '', onChange: vi.fn() });
		expect(MockEditorView).toHaveBeenCalledOnce();
	});

	it('uses html() extension when language is "html"', () => {
		render(Editor, { language: 'html', value: '', onChange: vi.fn() });
		expect(mockHtml).toHaveBeenCalledOnce();
		expect(mockCss).not.toHaveBeenCalled();
	});

	it('uses css() extension when language is "css"', () => {
		render(Editor, { language: 'css', value: '', onChange: vi.fn() });
		expect(mockCss).toHaveBeenCalledOnce();
		expect(mockHtml).not.toHaveBeenCalled();
	});

	it('passes initial value as doc to EditorState.create', () => {
		render(Editor, { language: 'html', value: '<p>hello</p>', onChange: vi.fn() });
		expect(MockEditorState.create).toHaveBeenCalledWith(
			expect.objectContaining({ doc: '<p>hello</p>' })
		);
	});

	it('renders a container div', () => {
		const { container } = render(Editor, { language: 'html', value: '', onChange: vi.fn() });
		expect(container.querySelector('div')).toBeTruthy();
	});
});
