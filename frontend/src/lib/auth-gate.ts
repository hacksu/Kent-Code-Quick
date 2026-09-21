export interface AuthedUser {
	is_admin?: boolean;
	signup_open?: boolean;
}

export function destinationFor(user: AuthedUser): '/admin' | '/lobby' | '/' {
	if (user.is_admin) return '/admin';
	return user.signup_open === true ? '/lobby' : '/';
}

export function isWaitingForSignup(user: AuthedUser): boolean {
	return !user.is_admin && user.signup_open !== true;
}
