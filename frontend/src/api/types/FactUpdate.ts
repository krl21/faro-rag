import type { FactValue } from './FactValue';

/** Body of `PATCH /documents/{id}/facts/{fact_id}`: at least one of both. */
export interface FactUpdate {
  label?: string;
  /** Replaces the whole value; for a table row, every column that must remain. */
  value?: FactValue;
}
