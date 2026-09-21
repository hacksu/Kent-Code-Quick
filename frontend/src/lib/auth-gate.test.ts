import { describe, it, expect } from 'vitest';
import { destinationFor, isWaitingForSignup } from './auth-gate';

describe('destinationFor', () => {
	it('sends admins to the admin console whether or not sign-ups are open', () => {
		expect(destinationFor({ is_admin: true, signup_open: false })).toBe('/admin');
		expect(destinationFor({ is_admin: true, signup_open: true })).toBe('/admin');
	});

	it('sends players to the lobby once sign-ups are open', () => {
		expect(destinationFor({ is_admin: false, signup_open: true })).toBe('/lobby');
	});

	it('sends players back to the landing page while sign-ups are closed', () => {
		expect(destinationFor({ is_admin: false, signup_open: false })).toBe('/');
	});

	it('keeps players out when the server says nothing about sign-ups', () => {
		// An older or partial payload must not be read as "open".
		expect(destinationFor({})).toBe('/');
		expect(destinationFor({ is_admin: false })).toBe('/');
	});
});

describe('isWaitingForSignup', () => {
	it('is true only for a non-admin with sign-ups closed', () => {
		expect(isWaitingForSignup({ is_admin: false, signup_open: false })).toBe(true);
		expect(isWaitingForSignup({ is_admin: false, signup_open: true })).toBe(false);
		expect(isWaitingForSignup({ is_admin: true, signup_open: false })).toBe(false);
	});
});
