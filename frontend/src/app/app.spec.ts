// Tests désactivés pour le POC — l'app dépend de HttpClient + Milvus + Mongo,
// les tests unitaires demandent du mocking conséquent. Hors scope MVP.
// La validation se fait via tests manuels end-to-end (cf. plan §13).

import { describe, it } from 'vitest';

describe('App', () => {
  it.skip('skipped — POC manual testing only', () => {
    // intentionally empty
  });
});
