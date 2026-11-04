import { setupServer } from 'msw/node';

/** Mock API at the network level. Each test registers its handlers with `server.use`. */
export const server = setupServer();

/** Absolute URL of an API path, as the client builds it in jsdom. */
export const apiUrl = (path: string) => `http://localhost:3000/api${path}`;
