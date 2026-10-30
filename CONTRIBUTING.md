# Contributing

Found a Python behavior that surprised you? Please add it.

## What makes a good pitfall

- **Surprising.** Readable code that does something other than what it says.
- **Minimal.** Reproducible in a handful of lines, with no third-party packages.
- **Fixable.** There is a clear, idiomatic way to avoid it.
- **Verified.** The output shown is what CPython actually prints, not what you remember it printing.

## Adding one

1. Create `examples/NN_short_name.py`, numbered after the last example. Show the trap, `assert` the surprising result, then show and `assert` the fix. Follow the layout of the existing files.
2. Add a section to `README.md` under the matching category, with **The Trap** snippet, a short **Why**, **The fix**, and a link to your example. Add a row to the Contents table.
3. Run every example locally:

   ```sh
   for f in examples/*.py; do python "$f" || echo "FAILED: $f"; done
   ```

4. Open a pull request. CI runs the examples on CPython 3.10 to 3.14.

If behavior differs between Python versions, say which versions in the README and guard the example with `sys.version_info`.
