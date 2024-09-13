# Content for item 0

```markdown
[Anthropic home page![light logo](https://mintlify.s3-us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3-us-west-1.amazonaws.com/anthropic/logo/dark.svg)](/)

English

Search...

Search

Navigation

Using the API

Versions

[Welcome](/en/home) [User Guides](/en/docs/welcome) [API Reference](/en/api/getting-started) [Prompt Library](/en/prompt-library/library) [Release Notes](/en/release-notes/overview) [Developer Newsletter](/en/developer-newsletter/overview)

For any given API version, we will preserve:

- Existing input parameters
- Existing output parameters

However, we may do the following:

- Add additional optional inputs
- Add additional values to the output
- Change conditions for specific error types
- Add new variants to enum-like output values (for example, streaming event types)

Generally, if you are using the API as documented in this reference, we will not break your usage.

## [​](\#version-history)  Version history

We always recommend using the latest API version whenever possible. Previous versions are considered deprecated and may be unavailable for new users.

- `2023-06-01`
  - New format for [streaming](/en/api/streaming) server-sent events (SSE):
    - Completions are incremental. For example, `" Hello"`, `" my"`, `" name"`, `" is"`, `" Claude." ` instead of `" Hello"`, `" Hello my"`, `" Hello my name"`, `" Hello my name is"`, `" Hello my name is Claude."`.
    - All events are [named events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent%5Fevents/Using%5Fserver-sent%5Fevents#named%5Fevents), rather than [data-only events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent%5Fevents/Using%5Fserver-sent%5Fevents#data-only%5Fmessages).
    - Removed unnecessary `data: [DONE]` event.
  - Removed legacy `exception` and `truncated` values in responses.
- `2023-01-01`: Initial release.

[IP addresses](/en/api/ip-addresses) [Errors](/en/api/errors)

On this page

- [Version history](#version-history)
```

----
