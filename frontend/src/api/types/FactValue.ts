/** Value of a free datum: plain text, or a table row as column -> value (in column order). */
export type FactValue = string | Record<string, string>;
