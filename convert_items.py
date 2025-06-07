import json
import re
import subprocess
import tempfile
from pathlib import Path


def sanitize_ts(ts_path: Path) -> Path:
    text = ts_path.read_text()
    text = re.sub(r"export const Items:.*?=", "globalThis.Items =", text, 1)
    text = re.sub(r"!([\.\[])", r"\1", text)
    text = text.replace("!++", "++")
    tmp = tempfile.NamedTemporaryFile("w+", suffix=".js", delete=False)
    tmp.write(text)
    tmp.flush()
    return Path(tmp.name)


def run_node(js_input: Path, output_json: Path):
    node_script = """
const fs = require('fs');
const vm = require('vm');
const [,, jsPath, outPath] = process.argv;
const code = fs.readFileSync(jsPath, 'utf8');
const context = {};
vm.runInNewContext(code, context);
const Items = context.Items;
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
for (const [id, data] of Object.entries(Items)) {
  plain[id] = sanitize(Object.assign({id}, data));
}
fs.writeFileSync(outPath, JSON.stringify(plain, null, 2));
"""
    with tempfile.NamedTemporaryFile("w+", suffix=".js", delete=False) as helper:
        helper.write(node_script)
        helper.flush()
        subprocess.run([
            "node", helper.name, js_input.as_posix(), output_json.as_posix()
        ], check=True)


def convert(ts_file: Path) -> dict:
    """Convert a Showdown ``items.ts`` file into a plain dictionary."""
    sanitized = sanitize_ts(ts_file)
    with tempfile.NamedTemporaryFile("r+", suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        run_node(sanitized, tmp_path)
        return json.loads(tmp_path.read_text())
    finally:
        sanitized.unlink(missing_ok=True)
        tmp_path.unlink(missing_ok=True)


def main():
    repo_root = Path(__file__).resolve().parent
    out_dir = repo_root / "data"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "items.json"

    data: dict[str, dict] = {}
    for sub in ["3gen_env_Showdown", "2gen_env_Showdown"]:
        ts_file = repo_root / sub / "items.ts"
        if ts_file.exists():
            data.update(convert(ts_file))

    out_file.write_text(json.dumps(data, indent=2))
    print(f"Wrote {out_file}")


if __name__ == "__main__":
    main()
