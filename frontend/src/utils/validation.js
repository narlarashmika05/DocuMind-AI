// Mirrors the backend password rule so users see problems before submitting.
export function passwordProblem(password) {
  if (password.length < 8) return 'Password must be at least 8 characters'
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
    return 'Password must contain at least one letter and one number'
  }
  return ''
}
