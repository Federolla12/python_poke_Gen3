// convertMoves.js
const fs = require('fs');
const path = require('path');
// require ts-node so we can import a .ts file directly
require('ts-node').register();

const allMoves = require(path.resolve(__dirname, 'moves.ts')).Moves;

// Helper to strip out functions, keep only serializable data
function sanitize(obj) {
  if (Array.isArray(obj)) return obj.map(sanitize);
  if (obj && typeof obj === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(obj)) {
      if (typeof v === 'function') continue;
      out[k] = sanitize(v);
    }
    return out;
  }
  return obj;
}

const plain = {};
for (const [id, data] of Object.entries(allMoves)) {
  // keep only Gen 3 entries (if TS file has multiple gens)
  if (data.gen && data.gen <= 3) {
    plain[id] = sanitize({
      id,
      name: data.name,
      type: data.type,
      category: data.category,
      basePower: data.basePower,
      accuracy: data.accuracy,
      pp: data.pp,
      priority: data.priority,
      flags: data.flags,
      // any other fields you care about: multihit, recoil, heal, etc.
    });
  }
}

fs.mkdirSync(path.join(__dirname, 'data'), { recursive: true });
fs.writeFileSync(
  path.join(__dirname, 'data', 'moves.json'),
  JSON.stringify(plain, null, 2),
  'utf8'
);
console.log('→ data/moves.json created with', Object.keys(plain).length, 'moves');
