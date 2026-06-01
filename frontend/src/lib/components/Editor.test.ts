import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';

type UpdateCallback = (update: { docChanged: boolean; state: { doc: { toString: () => string } } }) => void;

const { mockHtml, mockCss, MockEditorView, MockEditorState, MockCompartment } = vi.hoisted(() => {
	const mockHtml = vi.fn(() => 'html-ext');
	const mockCss = vi.fn(() => 'css-ext');
	const MockEditorView = vi.fn().mockImplementation(function () { return { destroy: vi.fn(), dispatch: vi.fn() }; });
	(MockEditorView as unknown as Record<string, unknown>).updateListener = {
		of: vi.fn((cb: unknown) => cb),
	};
	(MockEditorView as unknown as Record<string, unknown>).domEventHandlers = vi.fn(() => 'no-paste-ext');
	const MockEditorState = {
		create: vi.fn((opts: unknown) => opts),
		readOnly: { of: vi.fn((val: unknown) => ({ readOnly: val })) },
	};
	const MockCompartment = vi.fn().mockImplementation(function () {
		return { of: vi.fn((ext: unknown) => ext), reconfigure: vi.fn((ext: unknown) => ({ effects: ext })) };
	});
	return { mockHtml, mockCss, MockEditorView, MockEditorState, MockCompartment };
});

vi.mock('codemirror', () => ({ basicSetup: [] }));
vi.mock('@codemirror/view', () => ({ EditorView: MockEditorView }));
vi.mock('@codemirror/state', () => ({ EditorState: MockEditorState, Compartment: MockCompartment }));
vi.mock('@codemirror/lang-html', () => ({ html: mockHtml }));
vi.mock('@codemirror/lang-css', () => ({ css: mockCss }));

import Editor from './Editor.svelte';

beforeEach(() => {
	vi.clearAllMocks();
	(MockEditorView as ReturnType<typeof vi.fn>).mockImplementation(function () { return { destroy: vi.fn(), dispatch: vi.fn() }; });
	(MockEditorView as unknown as Record<string, unknown>).updateListener = {
		of: vi.fn((cb: unknown) => cb),
	};
	(MockEditorView as unknown as Record<string, unknown>).domEventHandlers = vi.fn(() => 'no-paste-ext');
	MockEditorState.readOnly.of = vi.fn((val: unknown) => ({ readOnly: val }));
	(MockCompartment as ReturnType<typeof vi.fn>).mockImplementation(function () {
		return { of: vi.fn((ext: unknown) => ext), reconfigure: vi.fn((ext: unknown) => ({ effects: ext })) };
	});
});

describe('Editor.svelte - basic setup', () => {
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

describe('Editor.svelte - readonly prop', () => {
	it('passes readOnly false by default', () => {
		render(Editor, { language: 'html', value: '', onChange: vi.fn() });
		expect(MockEditorState.readOnly.of).toHaveBeenCalledWith(false);
	});

	it('passes readOnly true when readonly prop is set', () => {
		render(Editor, { language: 'html', value: '', onChange: vi.fn(), readonly: true });
		expect(MockEditorState.readOnly.of).toHaveBeenCalledWith(true);
	});
});

describe('Editor.svelte - clipboard blocking', () => {
	it('registers domEventHandlers extension for paste/copy/cut', () => {
		render(Editor, { language: 'html', value: '', onChange: vi.fn() });
		expect(
			(MockEditorView as unknown as Record<string, { of: ReturnType<typeof vi.fn> }>).domEventHandlers
		).toHaveBeenCalledOnce();
		const handlers = (
			(MockEditorView as unknown as Record<string, ReturnType<typeof vi.fn>>).domEventHandlers
		).mock.calls[0][0] as Record<string, (e: Event) => void>;
		expect(typeof handlers.paste).toBe('function');
		expect(typeof handlers.copy).toBe('function');
		expect(typeof handlers.cut).toBe('function');
	});

	it('paste handler calls preventDefault', () => {
		render(Editor, { language: 'html', value: '', onChange: vi.fn() });
		const handlers = (
			(MockEditorView as unknown as Record<string, ReturnType<typeof vi.fn>>).domEventHandlers
		).mock.calls[0][0] as Record<string, (e: Event) => void>;
		const e = { preventDefault: vi.fn() } as unknown as Event;
		handlers.paste(e);
		expect(e.preventDefault).toHaveBeenCalled();
	});

	it('copy handler calls preventDefault', () => {
		render(Editor, { language: 'html', value: '', onChange: vi.fn() });
		const handlers = (
			(MockEditorView as unknown as Record<string, ReturnType<typeof vi.fn>>).domEventHandlers
		).mock.calls[0][0] as Record<string, (e: Event) => void>;
		const e = { preventDefault: vi.fn() } as unknown as Event;
		handlers.copy(e);
		expect(e.preventDefault).toHaveBeenCalled();
	});

	it('cut handler calls preventDefault', () => {
		render(Editor, { language: 'html', value: '', onChange: vi.fn() });
		const handlers = (
			(MockEditorView as unknown as Record<string, ReturnType<typeof vi.fn>>).domEventHandlers
		).mock.calls[0][0] as Record<string, (e: Event) => void>;
		const e = { preventDefault: vi.fn() } as unknown as Event;
		handlers.cut(e);
		expect(e.preventDefault).toHaveBeenCalled();
	});

	it('CodeMirror paste handler calls onCopyAttempt', () => {
		const onCopyAttempt = vi.fn();
		render(Editor, { language: 'html', value: '', onChange: vi.fn(), onCopyAttempt });
		const handlers = (
			(MockEditorView as unknown as Record<string, ReturnType<typeof vi.fn>>).domEventHandlers
		).mock.calls[0][0] as Record<string, (e: Event) => void>;
		handlers.paste({ preventDefault: vi.fn() } as unknown as Event);
		expect(onCopyAttempt).toHaveBeenCalledOnce();
	});

	it('CodeMirror copy handler calls onCopyAttempt', () => {
		const onCopyAttempt = vi.fn();
		render(Editor, { language: 'html', value: '', onChange: vi.fn(), onCopyAttempt });
		const handlers = (
			(MockEditorView as unknown as Record<string, ReturnType<typeof vi.fn>>).domEventHandlers
		).mock.calls[0][0] as Record<string, (e: Event) => void>;
		handlers.copy({ preventDefault: vi.fn() } as unknown as Event);
		expect(onCopyAttempt).toHaveBeenCalledOnce();
	});

	it('adds document-level capture listeners on mount', () => {
		const addSpy = vi.spyOn(document, 'addEventListener');
		render(Editor, { language: 'html', value: '', onChange: vi.fn() });
		const captureListeners = addSpy.mock.calls.filter((c) => c[2] === true).map((c) => c[0]);
		expect(captureListeners).toContain('paste');
		expect(captureListeners).toContain('copy');
	});

	it('document-level paste capture calls preventDefault', () => {
		const addSpy = vi.spyOn(document, 'addEventListener');
		render(Editor, { language: 'html', value: '', onChange: vi.fn() });
		const pasteCall = addSpy.mock.calls.find((c) => c[0] === 'paste' && c[2] === true);
		const listener = pasteCall?.[1] as (e: Event) => void;
		const e = { preventDefault: vi.fn() } as unknown as Event;
		listener(e);
		expect(e.preventDefault).toHaveBeenCalled();
	});

	it('document-level paste capture calls onCopyAttempt', () => {
		const addSpy = vi.spyOn(document, 'addEventListener');
		const onCopyAttempt = vi.fn();
		render(Editor, { language: 'html', value: '', onChange: vi.fn(), onCopyAttempt });
		const pasteCall = addSpy.mock.calls.find((c) => c[0] === 'paste' && c[2] === true);
		const listener = pasteCall?.[1] as (e: Event) => void;
		listener({ preventDefault: vi.fn() } as unknown as Event);
		expect(onCopyAttempt).toHaveBeenCalledOnce();
	});

	it('removes document-level capture listeners on destroy', () => {
		const removeSpy = vi.spyOn(document, 'removeEventListener');
		const { unmount } = render(Editor, { language: 'html', value: '', onChange: vi.fn() });
		unmount();
		const captureRemovals = removeSpy.mock.calls.filter((c) => c[2] === true).map((c) => c[0]);
		expect(captureRemovals).toContain('paste');
		expect(captureRemovals).toContain('copy');
	});
});

describe('Editor.svelte - debounced onChange', () => {
	function renderWithUpdateCapture(onChange: (value: string) => void) {
		let captured: UpdateCallback | null = null;
		(MockEditorView as unknown as Record<string, unknown>).updateListener = {
			of: vi.fn((cb: UpdateCallback) => { captured = cb; return cb; }),
		};
		render(Editor, { language: 'html', value: '', onChange });
		return { trigger: (doc: string) => captured?.({ docChanged: true, state: { doc: { toString: () => doc } } }) };
	}

	it('does not call onChange immediately on doc change', () => {
		vi.useFakeTimers();
		const onChange = vi.fn();
		const { trigger } = renderWithUpdateCapture(onChange);
		trigger('<p>new</p>');
		expect(onChange).not.toHaveBeenCalled();
		vi.useRealTimers();
	});

	it('calls onChange after 300ms', () => {
		vi.useFakeTimers();
		const onChange = vi.fn();
		const { trigger } = renderWithUpdateCapture(onChange);
		trigger('<p>new</p>');
		vi.advanceTimersByTime(300);
		expect(onChange).toHaveBeenCalledWith('<p>new</p>');
		vi.useRealTimers();
	});

	it('debounces rapid changes into a single call', () => {
		vi.useFakeTimers();
		const onChange = vi.fn();
		const { trigger } = renderWithUpdateCapture(onChange);
		trigger('a');
		vi.advanceTimersByTime(100);
		trigger('ab');
		vi.advanceTimersByTime(100);
		trigger('abc');
		vi.advanceTimersByTime(300);
		expect(onChange).toHaveBeenCalledOnce();
		expect(onChange).toHaveBeenCalledWith('abc');
		vi.useRealTimers();
	});
});
