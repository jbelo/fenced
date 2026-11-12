// Runs as the operator UID in an isolated container. Only manifest-listed files
// are managed; user programs, credentials and all unlisted paths are untouched.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const home = '/home/agent';
const ledger = '.fenced-managed.json';
const hash = data => crypto.createHash('sha256').update(data).digest('hex');
function checked(relative) {
  if (path.isAbsolute(relative) || relative.split('/').some(p => !p || p === '.' || p === '..')) throw Error('invalid path');
  let current = home;
  for (const component of relative.split('/')) {
    current = path.join(current, component);
    if (fs.existsSync(current) || (() => { try { fs.lstatSync(current); return true; } catch { return false; } })()) {
      if (fs.lstatSync(current).isSymbolicLink()) throw Error('symlink conflict');
    }
  }
  return current;
}
function atomic(relative, data) {
  const target = checked(relative);
  fs.mkdirSync(path.dirname(target), {recursive: true, mode: 0o755});
  const temporary = path.join(path.dirname(target), '.fenced-' + crypto.randomUUID());
  fs.writeFileSync(temporary, data, {mode: 0o644, flag: 'wx'});
  fs.renameSync(temporary, target);
}
try {
  const bundle = JSON.parse(fs.readFileSync(0, 'utf8'));
  const previous = fs.existsSync(checked(ledger)) ? JSON.parse(fs.readFileSync(checked(ledger), 'utf8')) : {};
  const changes = [];
  // Check every destination before writing anything. tmux is seed-only.
  for (const [relative, content] of Object.entries(bundle)) {
    const target = checked(relative), desired = Buffer.from(content, 'base64');
    if (fs.existsSync(target)) {
      if (!fs.lstatSync(target).isFile()) throw Error('non-file conflict');
      if (relative === '.tmux.conf') continue;
      const current = hash(fs.readFileSync(target));
      if (current === hash(desired)) continue; // Also recovers interrupted installs.
      if (previous[relative] !== current) throw Error('user-modified managed file: ' + relative);
    }
    changes.push([relative, desired]);
  }
  for (const [relative, desired] of changes) {
    // The old ledger still permits retry before rename; matching desired content
    // permits recovery after rename but before the ledger update.
    atomic(relative, desired);
    previous[relative] = hash(desired);
    atomic(ledger, JSON.stringify(previous));
  }
  // Adopt identical seed content, but never take ownership of a custom tmux config.
  for (const [relative, content] of Object.entries(bundle)) {
    if (relative !== '.tmux.conf') previous[relative] = hash(Buffer.from(content, 'base64'));
  }
  atomic(ledger, JSON.stringify(previous));
} catch (error) {
  console.error('managed-file conflict or access failure: ' + error.message);
  process.exit(1);
}
