# Contributing

1. Add or edit a file in `patterns/`: one POSIX extended regex per line, ASCII,
   LF endings, and a final newline. No blank lines, comments, or PCRE syntax.
   Patterns must work with `LC_ALL=C grep -E`.
2. Add new endpoints and aliases to `catalog.json`. Describe what matches and
   known limitations. Aliases are generated from the same source file.
3. Add matching and nonmatching inputs to `tests/cases.json`. For fixes, include
   the failing input as a regression case. Consider boundaries and long inputs.
4. Run the tests and build:

   ```sh
   python3 -m unittest discover -s tests -v
   python3 scripts/build.py
   ```

Open a pull request explaining the change. Linux and macOS checks must pass.
Preserve existing endpoints and document intentional behavior changes.
Use original or compatibly licensed patterns with attribution where needed.
Contributions are under the project's MIT license.
