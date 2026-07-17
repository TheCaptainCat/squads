/**
 * The three reserved meta types that exist in every squad regardless of a project's own
 * customized work-item vocabulary (roles, skills, and operators are infrastructure, not work).
 * Filtering keys on these exact type strings so the browse views stay spec-agnostic: a project
 * that renames/drops/re-prefixes its work-item types never needs this list touched.
 */
const RESERVED_TYPES: ReadonlySet<string> = new Set(['role', 'skill', 'operator']);

export function isReservedType(type: string): boolean {
  return RESERVED_TYPES.has(type);
}
