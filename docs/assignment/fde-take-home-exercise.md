# Field Deployed Engineer: Build Exercise

Build a small system that pulls public data, transforms it, runs an agent or
reasoning loop over each item, and serves the result.

## What to build

1. **Ingest** a public data source (no signup required). Pick from the list
   below or bring your own.
1. **Transform** in
   [Redpanda Connect](https://docs.redpanda.com/redpanda-connect/) by filtering,
   projecting, and routing. Connect does the plumbing.
1. **Reason** over each item with an LLM, in a service you write in any
   language. This is more than a single prompt. Your code will handle routing,
   multi-step extraction, retries on bad output, and confidence-based branching.
   Put this in your own code, not in a Connect `branch` processor. It consumes
   from a topic (or reads the store) and writes results. Make sure it is code
   you understand and can defend, not just generate. Make the model do work a
   rule cannot. Most feeds hand you metadata such as a comment, a title, a flag,
   or a number, and piping that into a model to get a label is a regex wearing a
   costume, because deleting the model leaves a rule that does the same job. The
   signal that needs a model usually lives in content the feed does not give you
   directly and you have to go fetch, such as the actual change, the linked
   body, or the file contents. Enriching the record before you reason is part of
   the exercise, not an add-on.
1. **Serve** the result somewhere we can see it. A web page, a JSON endpoint, or
   a CLI that reads from the store all work. Use Postgres or a Redpanda topic
   (or both) for storage.
1. **Test** the riskiest logic in your reasoning service, such as the
   dirty-output parse, the fallback, or the branching. Write one real test that
   fails if that logic breaks. This is not coverage theater.
1. **Run locally** with `docker compose up`.

Use AI tools however you like for the build. The write-up below is the
exception. Write it yourself, in your own words, without the help of AI.

## Stack (all free, all local, all open source)

| Piece       | Image                                       | Notes                                                                          |
| ----------- | ------------------------------------------- | ------------------------------------------------------------------------------ |
| Broker      | `docker.redpanda.com/redpandadata/redpanda` | Use `--mode=dev-container` for single-node.                                    |
| Pipeline    | `docker.redpanda.com/redpandadata/connect`  | Apache-2.0. [docs](https://docs.redpanda.com/redpanda-connect/)                |
| LLM, local  | `ollama/ollama` plus any open-weights model | Use `ollama_chat`, or point `openai_chat_completion`'s `server_address` at it. |
| LLM, hosted | OpenAI, Anthropic, or Bedrock, your call    | Include a `.env.example`.                                                      |
| Storage     | `postgres:16`                               | Or just a topic if you prefer.                                                 |

**Off-limits:** Redpanda Cloud (signup), Enterprise Connect connectors (CDC,
Snowflake Streaming, Iceberg, Salesforce, see
[licensing](https://docs.redpanda.com/redpanda-connect/get-started/licensing/)),
and `a2a_message` (hard-wired to Redpanda Cloud OAuth2).

## Pick a data source

| Source                       | URL                                                                          | Shape                                                                                                                      |
| ---------------------------- | ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **Wikipedia recent-changes** | `https://stream.wikimedia.org/v2/stream/recentchange`                        | SSE firehose, about 50 per second, no auth. Set a `User-Agent` header, because Wikimedia returns 403 to anonymous clients. |
| **Hacker News Firebase**     | `https://hacker-news.firebaseio.com/v0/`                                     | Poll-based. `/newstories.json` returns IDs, then a secondary fetch per item.                                               |
| **USGS earthquakes**         | `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson` | GeoJSON, polled. Time is epoch-ms, not seconds. The same items re-appear every poll, so dedupe.                            |
| **GitHub public events**     | `https://api.github.com/events`                                              | PRs, issues, and pushes. 60 requests per hour anonymous, so set `GITHUB_TOKEN` for 5k per hour.                            |
| **Your own**                 | Bluesky firehose, GDELT, NOAA, Reddit JSON, OpenSky                          | Bring it.                                                                                                                  |

## Hints (so you spend the time on judgment, not trivia)

These are things we hit ourselves while writing the reference solution. They are
not stumpers, and we do not want you to rediscover them.

- **Filter before the model.** Firehoses are noisy. Drop bots, heartbeats, and
  irrelevant namespaces first. Calling the model on every record is the wrong
  shape.
- **SSE in Connect** is `http_client` with `stream.enabled: true` plus the
  `lines` scanner. Strip the `data: ` prefix in Bloblang. Use
  `.catch(deleted())` on `parse_json()`, because Bloblang does not fail-closed
  inside `if`, so a single non-JSON heartbeat will pass through as a raw string
  and break everything downstream.
- **Bloblang `mapping` rebuilds `root` from scratch.** A trailing mapping that
  sets one field will drop everything else. Start with `root = this` or fold
  field changes into one block. Inside `branch.result_map` the rule inverts,
  because branch grafts your assignments back in, so a partial `root.X = ...` is
  correct there.
- **Use `branch` for LLM calls.** `request_map` builds the prompt, and
  `result_map` grafts the model output back onto the original message. Do not
  overwrite your payload with the model response.
- **Small or local models produce dirty JSON.** Extract the first `{...}` block,
  fall back to a default on parse failure, and normalize labels with
  `.string().trim().lowercase()`. Models drift outside your enum.
- **First-poll cold-start LLM failures pass through `branch` silently**, so rows
  land unclassified. Pair with an UPSERT sink so a later poll fixes them.
- **For poll-based sources, dedupe** with a Connect `cache` resource keyed on
  item id, or upsert. Without one of these you will either reprocess or hit a
  primary-key conflict every poll.
- **Public APIs need a User-Agent.** Wikipedia returns 403 without one, and
  GitHub rejects empty user agents.
- **Postgres `TIMESTAMPTZ` rejects raw epoch numbers.** Format to an ISO string
  in Bloblang first.

## Required write-up (about 30 minutes)

> Write it yourself, without the help of AI. Use AI freely to build the system.
> The write-up is the one part we ask you to write yourself, in your own words.
> It is how we read your judgment before the walkthrough, and the walkthrough
> assumes you wrote it. AI-generated tradeoffs are obvious, and we will treat
> them as an anti-signal.

In your `README.md`, include a **Tradeoffs** section of half a page to a page.
Pick two of the pairs below, whichever are most relevant to what you actually
built. Write one paragraph each covering what you chose, the alternative, and
when you would flip. Cite anything that shaped your thinking.

- Connect as the sink versus app-side writes from your reasoning service.
- One topic with a label column versus topic-per-label routing.
- One classification call versus a multi-step reasoning loop.
- Reasoning service as a worker consuming a topic versus invoked synchronously
  by the serve layer.
- Where the parse and validation of model output lives, in Connect before the
  topic or in your service.
- How you bound LLM cost and latency, by filtering in Connect first, batching in
  the service, or gating on confidence.

Also include a short paragraph on what surprised you and where this would break
in production.

Finally, write a **"Why this matters"** paragraph of three or four sentences for
a non-technical stakeholder at the customer, not for us. Say who would actually
use this, what decision or action it drives, and what it costs them when it is
wrong or missing. If you picked a demo dataset, state the real use case you are
standing in for. We are reading whether you can frame technical work as customer
value without a PM to translate, which is a core part of the job the rest of the
exercise does not test.

## Deliverable

A git repo (zip or link) containing:

- `README.md` with copy-pasteable run instructions, the Tradeoffs section,
  surprises, production-failure notes, and the "Why this matters" paragraph.
- `docker-compose.yml` with everything needed to run, including any model proxy.
- Connect configs, app code, schema, and seeds.
- `.env.example` if you use a hosted LLM.

We will run it. Cleanly starting is part of the signal.

## Walkthrough (60 minutes, follow-up session)

Screen-share, bring it up live, and walk us through it. We will ask why this
source, why this transform shape, why this agent topology, where the failure
modes live, who this is for and why they would care, and what you would change
for a real customer. The walkthrough assumes you wrote the write-up yourself, so
expect us to push on the tradeoffs you named.

**Pre-walkthrough extension (sent about 2 days before).** Once you have
submitted, we send you one small, specific change to make to your reasoning
service, scoped to under an hour. For example, add a confidence tier and route
urgent items to a new topic, skip the LLM for a known-bot comment pattern, or
thread a new field through end to end. Make it on your own time, AI tools are
fine, and return it as a diff (a branch or a second commit). We read the diff
before the session.

In the walkthrough you walk us through that diff: what you changed, why it goes
where it goes, what you checked, and where it could break. We also pick a couple
of spots in your original code and ask you to trace an input or tell us what
happens on a malformed model response. There is no coding in the session. It is
defending real code you produced ahead of time. We are reading whether you
understand and can change the code you shipped. It does not matter whether an
agent wrote it, only that you can own it. This is why the reasoning loop has to
be code you wrote, not config, because a Connect pipeline gives us nothing to
extend or read line by line.

---
