/** Monetary amount. The API serializes decimals as strings. */
export interface Money {
  amount: string | number;
  currency: string;
}
