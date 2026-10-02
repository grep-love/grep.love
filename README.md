# grep.love

Shared regular expressions for grep. Fetch a pattern from the website and search
locally—your files stay on your machine.

## Patterns

| Endpoint | Matches |
| --- | --- |
| `/ips`, `/ipv4` | IPv4 addresses, with octets from 0 to 255 |
| `/domains` | ASCII domain-shaped text, including subdomains |

Use `grep -E -f` to read these extended regular expressions. The website provides
copyable curl examples using its current address. From a checkout:

```sh
grep -Er -f patterns/ipv4 ./logs
grep -E -f patterns/domains file1
```

Patterns select whole lines. `/ips` currently supports IPv4 only; `/domains` is a
heuristic, so filenames such as `report.txt` also match. See
[catalog.json](catalog.json) for each pattern's scope and limitations.

Use `LC_ALL=C` for predictable ASCII matching. The website's `<(...)` examples
require Bash or Zsh. For scripts, download and check the pattern before running
grep: errors inside process substitution do not propagate to grep. Keep a local
copy when you need repeatable results, since hosted patterns can change.

## Development

Requires Python 3.10+, grep, curl, and Bash. No package dependencies.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 -m http.server 8000 --directory _site
```

Open http://localhost:8000. Build output goes to `_site/` and is not committed.
Tests run against GNU grep on Linux and system grep on macOS in CI.

## Contributing

New patterns and fixes are welcome. Include matching and nonmatching examples;
see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
