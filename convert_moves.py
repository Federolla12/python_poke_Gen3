import json
import subprocess
import tempfile
from pathlib import Path


def compile_ts(ts_file: Path) -> Path:
    """Compile a TypeScript file to JavaScript using esbuild."""
    out = tempfile.NamedTemporaryFile("w+", suffix=".js", delete=False)
    out.close()
    subprocess.run(
        ["npx", "esbuild", ts_file.as_posix(), "--format=cjs", f"--outfile={out.name}"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return Path(out.name)


def run_node(js_input: Path, output_json: Path) -> None:
    node_script = """
const fs = require('fs');
const mod = require(process.argv[2]);
const outPath = process.argv[3];
const Moves = mod.Moves || mod.default || {};
function sanitize(obj) {
  if (Array.isArray(obj)) return obj.map(sanitize);
  if (obj && typeof obj === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(obj)) {
      if (typeof v === 'function') {
        out[k] = v.toString();
      } else {
        out[k] = sanitize(v);
      }
    }
    return out;
  }
  return obj;
}
const plain = {};
for (const [id, data] of Object.entries(Moves)) {
  if (!data.gen || data.gen <= 3) {
    plain[id] = sanitize(Object.assign({id}, data));
  }
}
fs.writeFileSync(outPath, JSON.stringify(plain, null, 2));
"""
    with tempfile.NamedTemporaryFile("w+", suffix=".js", delete=False) as helper:
        helper.write(node_script)
        helper.flush()
        subprocess.run(
            ["node", helper.name, js_input.as_posix(), output_json.as_posix()],
            check=True,
        )
    Path(helper.name).unlink(missing_ok=True)


def convert(ts_file: Path) -> dict:
    """Convert a Showdown ``moves.ts`` file into a plain dictionary."""
    compiled = compile_ts(ts_file)
    with tempfile.NamedTemporaryFile("r+", suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        run_node(compiled, tmp_path)
        return json.loads(tmp_path.read_text())
    finally:
        compiled.unlink(missing_ok=True)
        tmp_path.unlink(missing_ok=True)


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    out_dir = repo_root / "data"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "moves.json"

    data: dict[str, dict] = {}

    base_ts = repo_root / "data" / "base_moves.ts"
    if base_ts.exists():
        data.update(convert(base_ts))

    for sub in ["2gen_env_Showdown", "3gen_env_Showdown"]:
        ts_file = repo_root / sub / "moves.ts"
        if ts_file.exists():
            data.update(convert(ts_file))

    out_file.write_text(json.dumps(data, indent=2))
    print(f"Wrote {out_file}")


if __name__ == "__main__":
    main()
