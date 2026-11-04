import type { Money } from './Money';
import type { Period } from './Period';

/** Any value an extracted field can hold. */
export type FieldValue = string | string[] | Period | Money;
