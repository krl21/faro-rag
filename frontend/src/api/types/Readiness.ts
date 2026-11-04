/** Body of `GET /health/ready`: status of each dependency (`worker` was requested). */
export type Readiness = Partial<Record<'database' | 'redis' | 'worker', 'ok' | 'error'>>;
