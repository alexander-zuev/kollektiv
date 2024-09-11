# Content for item 0

```markdown
AI & Vectors

# Vector search with Next.js and OpenAI

## Learn how to build a ChatGPT-style doc search powered by Next.js, OpenAI, and Supabase.

* * *

While our [Headless Vector search](/docs/guides/ai/examples/headless-vector-search) provides a toolkit for generative Q&A, in this tutorial we'll go more in-depth, build a custom ChatGPT-like search experience from the ground-up using Next.js. You will:

1. Convert your markdown into embeddings using OpenAI.
2. Store you embeddings in Postgres using pgvector.
3. Deploy a function for answering your users' questions.

You can read our [Supabase Clippy](https://supabase.com/blog/chatgpt-supabase-docs) blog post for a full example.

We assume that you have a Next.js project with a collection of `.mdx` files nested inside your `pages` directory. We will start developing locally with the Supabase CLI and then push our local database changes to our hosted Supabase project. You can find the [full Next.js example on GitHub](https://github.com/supabase-community/nextjs-openai-doc-search).

## Create a project [\#](\#create-a-project)

1. [Create a new project](https://supabase.com/dashboard) in the Supabase Dashboard.
2. Enter your project details.
3. Wait for the new database to launch.

## Prepare the database [\#](\#prepare-the-database)

Let's prepare the database schema. We can use the "OpenAI Vector Search" quickstart in the [SQL Editor](https://supabase.com/dashboard/project/_/sql), or you can copy/paste the SQL below and run it yourself.

DashboardSQL

1. Go to the [SQL Editor](https://supabase.com/dashboard/project/_/sql) page in the Dashboard.
2. Click **OpenAI Vector Search**.
3. Click **Run**.

## Pre-process the knowledge base at build time [\#](\#pre-process-the-knowledge-base-at-build-time)

With our database set up, we need to process and store all `.mdx` files in the `pages` directory. You can find the full script [here](https://github.com/supabase-community/nextjs-openai-doc-search/blob/main/lib/generate-embeddings.ts), or follow the steps below:

1

### Generate Embeddings

Create a new file `lib/generate-embeddings.ts` and copy the code over from [GitHub](https://github.com/supabase-community/nextjs-openai-doc-search/blob/main/lib/generate-embeddings.ts).

`
1
curl \
2
https://raw.githubusercontent.com/supabase-community/nextjs-openai-doc-search/main/lib/generate-embeddings.ts \
3
-o "lib/generate-embeddings.ts"
`

2

### Set up environment variables

We need some environment variables to run the script. Add them to your `.env` file and make sure your `.env` file is not committed to source control!
You can get your local Supabase credentials by running `supabase status`.

`
1
NEXT_PUBLIC_SUPABASE_URL=
2
NEXT_PUBLIC_SUPABASE_ANON_KEY=
3
SUPABASE_SERVICE_ROLE_KEY=
4
5
# Get your key at https://platform.openai.com/account/api-keys
6
OPENAI_API_KEY=
`

3

### Run script at build time

Include the script in your `package.json` script commands to enable Vercel to automaticall run it at build time.

`
1
"scripts": {
2
"dev": "next dev",
3
"build": "pnpm run embeddings && next build",
4
"start": "next start",
5
"embeddings": "tsx lib/generate-embeddings.ts"
6
},
`

## Create text completion with OpenAI API [\#](\#create-text-completion-with-openai-api)

Anytime a user asks a question, we need to create an embedding for their question, perform a similarity search, and then send a text completion request to the OpenAI API with the query and then context content merged together into a prompt.

All of this is glued together in a [Vercel Edge Function](https://vercel.com/docs/concepts/functions/edge-functions), the code for which can be found on [GitHub](https://github.com/supabase-community/nextjs-openai-doc-search/blob/main/pages/api/vector-search.ts).

1

### Create Embedding for Question

In order to perform similarity search we need to turn the question into an embedding.

``
1
const embeddingResponse = await fetch('https://api.openai.com/v1/embeddings', {
2
method: 'POST',
3
headers: {
4
    Authorization: `Bearer ${openAiKey}`,
5
    'Content-Type': 'application/json',
6
},
7
body: JSON.stringify({
8
    model: 'text-embedding-ada-002',
9
    input: sanitizedQuery.replaceAll('\n', ' '),
10
}),
11
})
12
13
if (embeddingResponse.status !== 200) {
14
throw new ApplicationError('Failed to create embedding for question', embeddingResponse)
15
}
16
17
const {
18
data: [{ embedding }],
19
} = await embeddingResponse.json()
``

2

### Perform similarity search

Using the `embeddingResponse` we can now perform similarity search by performing an remote procedure call (RPC) to the database function we created earlier.

`
1
const { error: matchError, data: pageSections } = await supabaseClient.rpc(
2
'match_page_sections',
3
{
4
    embedding,
5
    match_threshold: 0.78,
6
    match_count: 10,
7
    min_content_length: 50,
8
}
9
)
`

3

### Perform text completion request

With the relevant content for the user's question identified, we can now build the prompt and make a text completion request via the OpenAI API.

If successful, the OpenAI API will respond with a `text/event-stream` response that we can simply forward to the client where we'll process the event stream to smoothly print the answer to the user.

``
1
const prompt = codeBlock`
2
${oneLine`
3
    You are a very enthusiastic Supabase representative who loves
4
    to help people! Given the following sections from the Supabase
5
    documentation, answer the question using only that information,
6
    outputted in markdown format. If you are unsure and the answer
7
    is not explicitly written in the documentation, say
8
    "Sorry, I don't know how to help with that."
9
`}
10
11
Context sections:
12
${contextText}
13
14
Question: """
15
${sanitizedQuery}
16
"""
17
18
Answer as markdown (including related code snippets if available):
19
`
20
21
const completionOptions: CreateCompletionRequest = {
22
model: 'gpt-3.5-turbo-instruct',
23
prompt,
24
max_tokens: 512,
25
temperature: 0,
26
stream: true,
27
}
28
29
const response = await fetch('https://api.openai.com/v1/completions', {
30
method: 'POST',
31
headers: {
32
    Authorization: `Bearer ${openAiKey}`,
33
    'Content-Type': 'application/json',
34
},
35
body: JSON.stringify(completionOptions),
36
})
37
38
if (!response.ok) {
39
const error = await response.json()
40
throw new ApplicationError('Failed to generate completion', error)
41
}
42
43
// Proxy the streamed SSE response from OpenAI
44
return new Response(response.body, {
45
headers: {
46
    'Content-Type': 'text/event-stream',
47
},
48
})
``

## Display the answer on the frontend [\#](\#display-the-answer-on-the-frontend)

In a last step, we need to process the event stream from the OpenAI API and print the answer to the user. The full code for this can be found on [GitHub](https://github.com/supabase-community/nextjs-openai-doc-search/blob/main/components/SearchDialog.tsx).

``
1
const handleConfirm = React.useCallback(
2
async (query: string) => {
3
    setAnswer(undefined)
4
    setQuestion(query)
5
    setSearch('')
6
    dispatchPromptData({ index: promptIndex, answer: undefined, query })
7
    setHasError(false)
8
    setIsLoading(true)
9
10
    const eventSource = new SSE(`api/vector-search`, {
11
      headers: {
12
        apikey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '',
13
        Authorization: `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY}`,
14
        'Content-Type': 'application/json',
15
      },
16
      payload: JSON.stringify({ query }),
17
    })
18
19
    function handleError<T>(err: T) {
20
      setIsLoading(false)
21
      setHasError(true)
22
      console.error(err)
23
    }
24
25
    eventSource.addEventListener('error', handleError)
26
    eventSource.addEventListener('message', (e: any) => {
27
      try {
28
        setIsLoading(false)
29
30
        if (e.data === '[DONE]') {
31
          setPromptIndex((x) => {
32
            return x + 1
33
          })
34
          return
35
        }
36
37
        const completionResponse: CreateCompletionResponse = JSON.parse(e.data)
38
        const text = completionResponse.choices[0].text
39
40
        setAnswer((answer) => {
41
          const currentAnswer = answer ?? ''
42
43
          dispatchPromptData({
44
            index: promptIndex,
45
            answer: currentAnswer + text,
46
          })
47
48
          return (answer ?? '') + text
49
        })
50
      } catch (err) {
51
        handleError(err)
52
      }
53
    })
54
55
    eventSource.stream()
56
57
    eventSourceRef.current = eventSource
58
59
    setIsLoading(true)
60
},
61
[promptIndex, promptData]
62
)
``

## Learn more [\#](\#learn-more)

Want to learn more about the awesome tech that is powering this?

- Read about how we built [ChatGPT for the Supabase Docs](https://supabase.com/blog/chatgpt-supabase-docs).
- Read the pgvector Docs for [Embeddings and vector similarity](https://supabase.com/docs/guides/database/extensions/pgvector)
- Watch Greg's video for a full breakdown:

Watch video guide

![Video guide preview](https://supabase.com/docs/_next/image?url=http%3A%2F%2Fimg.youtube.com%2Fvi%2FxmfNUCjszh4%2F0.jpg&w=3840&q=75&dpl=dpl_8T75GeYs2RqN59z5hY7ru4dxhiVp)

### Is this helpful?

YesNo

Thanks for your feedback!

On this page

- [Create a project](#create-a-project)
- [Prepare the database](#prepare-the-database)
- [Pre-process the knowledge base at build time](#pre-process-the-knowledge-base-at-build-time)
- [Create text completion with OpenAI API](#create-text-completion-with-openai-api)
- [Display the answer on the frontend](#display-the-answer-on-the-frontend)
- [Learn more](#learn-more)

1. We only collect analytics essential to ensuring smooth operation of our services. [Learn more](https://supabase.com/privacy)





   AcceptOpt out[Learn more](https://supabase.com/privacy)
```

----

