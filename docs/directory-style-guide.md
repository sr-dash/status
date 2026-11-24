# Directory style guide

The [status page directory](../DIRECTORY.md) is generated from [`directory.yml`](../directory.yml).
Entries are short, factual and written the same way, so readers can compare projects at a glance.
The automatic check on each pull request enforces the rules marked **(checked)**; the maintainer
reviews the rest.

## What belongs in the directory

- **Runs on GitHub alone, Serverless and Self-hosted:** open-source status page software with a
  public repository on GitHub, a licence file, recent activity, and a public page that shows it
  working.
- **Status pages research software depends on:** the official status page of a service that open
  research code, papers or data rely on (code hosting, package indexes, documentation, archives,
  identifiers).
- Not listed: closed-source or paid-only products, personal monitoring dashboards, forks that are not
  the maintained version, and projects that are announced but not yet usable.

## The fields

A project in the first three sections:

```yaml
      - repo: owner/name            # the GitHub repository (checked)
        name: Project name          # the project's own spelling
        live: https://example.org   # a public page that shows it working (optional; checked)
        how: Go, one binary or Docker
        watches: HTTP, TCP, DNS and ICMP
```

A status page in the last section:

```yaml
      - name: Service name
        live: https://status.example.org
        about: What the service covers
```

Only these fields are accepted **(checked)**. Add the entry at the end of its section; the directory
orders projects by GitHub stars when it is built.

## Wording

- **Plain text.** No links, Markdown, HTML or code formatting in `name`, `how`, `watches`, `about`
  or `note` **(checked)**.
- **Sentence case.** Start `how`, `watches`, `about` and `note` with a capital letter **(checked)**.
  Keep the project's own spelling in `name`.
- **Table cells are phrases, not sentences.** `how`, `watches` and `about` end without a full stop or
  other punctuation **(checked)**. `note` is a full sentence and ends with a full stop **(checked)**.
- **Say what it does, not how good it is.** No marketing words such as best, fastest, powerful,
  seamless, robust, cutting-edge or next-gen **(checked)**, no exclamation marks and no emoji
  **(checked)**.
- **Capitals only for short acronyms** such as HTTP, TCP, DNS, TLS or SQL **(checked)**.
- **Lists without the serial comma:** "HTTP, TCP, DNS and ICMP" (the check flags ", and").
- **No abbreviations** such as e.g., i.e. or etc.; name the items instead (the check flags them).
- **Short:** `name` up to 60 characters, `how`, `watches` and `about` up to 120, `note` up to 160
  **(checked)**.
- **`how`** says what it is built with and how it runs: "Python, Docker Compose with SQLite",
  "Cloudflare Workers with KV storage".
- **`watches`** says what it checks: "Uptime and response time, TLS certificates, domain expiry".

## Examples

| | `how` | `watches` |
|---|---|---|
| Good | Go, one binary or Docker | HTTP, TCP, UDP, ICMP and gRPC |
| Not like this | The fastest, most powerful monitor! | http, tcp, udp, icmp, and grpc. |

## After you open the pull request

1. A check posts an overview on the pull request: a preview of your row as it will appear, and
   anything to fix. It updates each time you push.
2. When the check passes, the pull request is labelled `directory: ready for review`.
3. The maintainer reviews it. Once approved, it is merged automatically, and DIRECTORY.md and the
   [directory page](https://sr-dash.github.io/status/directory/) update within minutes.
