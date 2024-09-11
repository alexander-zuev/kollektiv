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

# Content for item 1

```markdown
AI & Vectors

# API

* * *

# API

`vecs` is a python client for managing and querying vector stores in PostgreSQL with the [pgvector extension](https://github.com/pgvector/pgvector). This guide will help you get started with using vecs.

If you don't have a Postgres database with the pgvector ready, see [hosting](https://supabase.github.io/vecs/hosting) for easy options.

## Installation [\#](\#installation)

Requires:

- Python 3.7+

You can install vecs using pip:

`
_10
pip install vecs
`

## Usage [\#](\#usage)

## Connecting [\#](\#connecting)

Before you can interact with vecs, create the client to communicate with Postgres. If you haven't started a Postgres instance yet, see [hosting](https://supabase.github.io/vecs/hosting).

`
_10
import vecs
_10
_10
DB_CONNECTION = "postgresql://<user>:<password>@<host>:<port>/<db_name>"
_10
_10
# create vector store client
_10
vx = vecs.create_client(DB_CONNECTION)
`

## Get or Create a Collection [\#](\#get-or-create-a-collection)

You can get a collection (or create if it doesn't exist), specifying the collection's name and the number of dimensions for the vectors you intend to store.

`
_10
docs = vx.get_or_create_collection(name="docs", dimension=3)
`

## Upserting vectors [\#](\#upserting-vectors)

`vecs` combines the concepts of "insert" and "update" into "upsert". Upserting records adds them to the collection if the `id` is not present, or updates the existing record if the `id` does exist.

`
_15
# add records to the collection
_15
docs.upsert(
_15
    records=[\
_15\
        (\
_15\
         "vec0",           # the vector's identifier\
_15\
         [0.1, 0.2, 0.3],  # the vector. list or np.array\
_15\
         {"year": 1973}    # associated  metadata\
_15\
        ),\
_15\
        (\
_15\
         "vec1",\
_15\
         [0.7, 0.8, 0.9],\
_15\
         {"year": 2012}\
_15\
        )\
_15\
    ]
_15
)
`

## Deleting vectors [\#](\#deleting-vectors)

Deleting records removes them from the collection. To delete records, specify a list of `ids` or metadata filters to the `delete` method. The ids of the sucessfully deleted records are returned from the method. Note that attempting to delete non-existent records does not raise an error.

`
_10
docs.delete(ids=["vec0", "vec1"])
_10
# or delete by a metadata filter
_10
docs.delete(filters={"year": {"$eq": 2012}})
`

## Create an index [\#](\#create-an-index)

Collections can be queried immediately after being created.
However, for good throughput, the collection should be indexed after records have been upserted.

Only one index may exist per-collection. By default, creating an index will replace any existing index.

To create an index:

`
_10
docs.create_index()
`

You may optionally provide a distance measure and index method.

Available options for distance `measure` are:

- `vecs.IndexMeasure.cosine_distance`
- `vecs.IndexMeasure.l2_distance`
- `vecs.IndexMeasure.max_inner_product`

which correspond to different methods for comparing query vectors to the vectors in the database.

If you aren't sure which to use, the default of cosine\_distance is the most widely compatible with off-the-shelf embedding methods.

Available options for index `method` are:

- `vecs.IndexMethod.auto`
- `vecs.IndexMethod.hnsw`
- `vecs.IndexMethod.ivfflat`

Where `auto` selects the best available index method, `hnsw` uses the [HNSW](https://github.com/pgvector/pgvector#hnsw) method and `ivfflat` uses [IVFFlat](https://github.com/pgvector/pgvector#ivfflat).

HNSW and IVFFlat indexes both allow for parameterization to control the speed/accuracy tradeoff. vecs provides sane defaults for these parameters. For a greater level of control you can optionally pass an instance of `vecs.IndexArgsIVFFlat` or `vecs.IndexArgsHNSW` to `create_index`'s `index_arguments` argument. Descriptions of the impact for each parameter are available in the [pgvector docs](https://github.com/pgvector/pgvector).

When using IVFFlat indexes, the index must be created **after** the collection has been populated with records. Building an IVFFlat index on an empty collection will result in significantly reduced recall. You can continue upserting new documents after the index has been created, but should rebuild the index if the size of the collection more than doubles since the last index operation.

HNSW indexes can be created immediately after the collection without populating records.

To manually specify `method`, `measure`, and `index_arguments` add them as arguments to `create_index` for example:

`
_10
docs.create_index(
_10
    method=IndexMethod.hnsw,
_10
    measure=IndexMeasure.cosine_distance,
_10
    index_arguments=IndexArgsHNSW(m=8),
_10
)
`

The time required to create an index grows with the number of records and size of vectors.
For a few thousand records expect sub-minute a response in under a minute. It may take a few
minutes for larger collections.

## Query [\#](\#query)

Given a collection `docs` with several records:

### Basic [\#](\#basic)

The simplest form of search is to provide a query vector.

Indexes are essential for good performance. See [creating an index](#create-an-index) for more info.

If you do not create an index, every query will return a warning

`
_10
query does not have a covering index for cosine_similarity. See Collection.create_index
`

that incldues the `IndexMeasure` you should index.

`
_10
docs.query(
_10
    data=[0.4,0.5,0.6],          # required
_10
    limit=5,                     # number of records to return
_10
    filters={},                  # metadata filters
_10
    measure="cosine_distance",   # distance measure to use
_10
    include_value=False,         # should distance measure values be returned?
_10
    include_metadata=False,      # should record metadata be returned?
_10
)
`

Which returns a list of vector record `ids`.

### Metadata Filtering [\#](\#metadata-filtering)

The metadata that is associated with each record can also be filtered during a query.

As an example, `{"year": {"$eq": 2005}}` filters a `year` metadata key to be equal to 2005

In context:

`
_10
docs.query(
_10
    data=[0.4,0.5,0.6],
_10
    filters={"year": {"$eq": 2012}}, # metadata filters
_10
)
`

For a complete reference, see the [metadata guide](metadata).

### Disconnect [\#](\#disconnect)

When you're done with a collection, be sure to disconnect the client from the database.

`
_10
vx.disconnect()
`

alternatively, use the client as a context manager and it will automatically close the connection on exit.

`
_10
import vecs
_10
_10
DB_CONNECTION = "postgresql://<user>:<password>@<host>:<port>/<db_name>"
_10
_10
# create vector store client
_10
with vecs.create_client(DB_CONNECTION) as vx:
_10
    # do some work here
_10
    pass
_10
_10
# connections are now closed
`

## Adapters [\#](\#adapters)

Adapters are an optional feature to transform data before adding to or querying from a collection. Adapters make it possible to interact with a collection using only your project's native data type (eg. just raw text), rather than manually handling vectors.

For a complete list of available adapters, see [built-in adapters](https://supabase.github.io/vecs/concepts_adapters#built-in-adapters).

As an example, we'll create a collection with an adapter that chunks text into paragraphs and converts each chunk into an embedding vector using the `all-MiniLM-L6-v2` model.

First, install `vecs` with optional dependencies for text embeddings:

`
_10
pip install "vecs[text_embedding]"
`

Then create a collection with an adapter to chunk text into paragraphs and embed each paragraph using the `all-MiniLM-L6-v2` 384 dimensional text embedding model.

`
_16
import vecs
_16
from vecs.adapter import Adapter, ParagraphChunker, TextEmbedding
_16
_16
# create vector store client
_16
vx = vecs.Client("postgresql://<user>:<password>@<host>:<port>/<db_name>")
_16
_16
# create a collection with an adapter
_16
docs = vx.get_or_create_collection(
_16
    name="docs",
_16
    adapter=Adapter(
_16
        [\
_16\
            ParagraphChunker(skip_during_query=True),\
_16\
            TextEmbedding(model='all-MiniLM-L6-v2'),\
_16\
        ]
_16
    )
_16
)
`

With the adapter registered against the collection, we can upsert records into the collection passing in text rather than vectors.

`
_15
# add records to the collection using text as the media type
_15
docs.upsert(
_15
    records=[\
_15\
        (\
_15\
         "vec0",\
_15\
         "four score and ....", # <- note that we can now pass text here\
_15\
         {"year": 1973}\
_15\
        ),\
_15\
        (\
_15\
         "vec1",\
_15\
         "hello, world!",\
_15\
         {"year": "2012"}\
_15\
        )\
_15\
    ]
_15
)
`

Similarly, we can query the collection using text.

`
_10
_10
# search by text
_10
docs.query(data="foo bar")
`

* * *

## Deprecated [\#](\#deprecated)

### Create collection [\#](\#create-collection)

Deprecated: use [get\_or\_create\_collection](#get-or-create-a-collection)

You can create a collection to store vectors specifying the collections name and the number of dimensions in the vectors you intend to store.

`
_10
docs = vx.create_collection(name="docs", dimension=3)
`

### Get an existing collection [\#](\#get-an-existing-collection)

Deprecated: use [get\_or\_create\_collection](#get-or-create-a-collection)

To access a previously created collection, use `get_collection` to retrieve it by name

`
_10
docs = vx.get_collection(name="docs")
`
```

----

# Content for item 2

```markdown
AI & Vectors

# LangChain

* * *

[LangChain](https://langchain.com/) is a popular framework for working with AI, Vectors, and embeddings. LangChain supports using Supabase as a [vector store](https://js.langchain.com/docs/modules/indexes/vector_stores/integrations/supabase), using the `pgvector` extension.

## Initializing your database [\#](\#initializing-your-database)

Prepare you database with the relevant tables:

DashboardSQL

1. Go to the [SQL Editor](https://supabase.com/dashboard/project/_/sql) page in the Dashboard.
2. Click **LangChain** in the Quick start section.
3. Click **Run**.

## Usage [\#](\#usage)

You can now search your documents using any Node.js application. This is intended to be run on a secure server route.

``
_28
import { SupabaseVectorStore } from 'langchain/vectorstores/supabase'
_28
import { OpenAIEmbeddings } from 'langchain/embeddings/openai'
_28
import { createClient } from '@supabase/supabase-js'
_28
_28
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY
_28
if (!supabaseKey) throw new Error(`Expected SUPABASE_SERVICE_ROLE_KEY`)
_28
_28
const url = process.env.SUPABASE_URL
_28
if (!url) throw new Error(`Expected env var SUPABASE_URL`)
_28
_28
export const run = async () => {
_28
const client = createClient(url, supabaseKey)
_28
_28
const vectorStore = await SupabaseVectorStore.fromTexts(
_28
    ['Hello world', 'Bye bye', "What's this?"],
_28
    [{ id: 2 }, { id: 1 }, { id: 3 }],
_28
    new OpenAIEmbeddings(),
_28
    {
_28
      client,
_28
      tableName: 'documents',
_28
      queryName: 'match_documents',
_28
    }
_28
)
_28
_28
const resultOne = await vectorStore.similaritySearch('Hello world', 1)
_28
_28
console.log(resultOne)
_28
}
``

### Simple metadata filtering [\#](\#simple-metadata-filtering)

Given the above `match_documents` Postgres function, you can also pass a filter parameter to only return documents with a specific metadata field value. This filter parameter is a JSON object, and the `match_documents` function will use the Postgres JSONB Containment operator `@>` to filter documents by the metadata field values you specify. See details on the [Postgres JSONB Containment operator](https://www.postgresql.org/docs/current/datatype-json.html#JSON-CONTAINMENT) for more information.

``
_32
import { SupabaseVectorStore } from 'langchain/vectorstores/supabase'
_32
import { OpenAIEmbeddings } from 'langchain/embeddings/openai'
_32
import { createClient } from '@supabase/supabase-js'
_32
_32
// First, follow set-up instructions above
_32
_32
const privateKey = process.env.SUPABASE_SERVICE_ROLE_KEY
_32
if (!privateKey) throw new Error(`Expected env var SUPABASE_SERVICE_ROLE_KEY`)
_32
_32
const url = process.env.SUPABASE_URL
_32
if (!url) throw new Error(`Expected env var SUPABASE_URL`)
_32
_32
export const run = async () => {
_32
const client = createClient(url, privateKey)
_32
_32
const vectorStore = await SupabaseVectorStore.fromTexts(
_32
    ['Hello world', 'Hello world', 'Hello world'],
_32
    [{ user_id: 2 }, { user_id: 1 }, { user_id: 3 }],
_32
    new OpenAIEmbeddings(),
_32
    {
_32
      client,
_32
      tableName: 'documents',
_32
      queryName: 'match_documents',
_32
    }
_32
)
_32
_32
const result = await vectorStore.similaritySearch('Hello world', 1, {
_32
    user_id: 3,
_32
})
_32
_32
console.log(result)
_32
}
``

### Advanced metadata filtering [\#](\#advanced-metadata-filtering)

You can also use query builder-style filtering ( [similar to how the Supabase JavaScript library works](https://supabase.com/docs/reference/javascript/using-filters)) instead of passing an object. Note that since the filter properties will be in the metadata column, you need to use arrow operators ( `->` for integer or `->>` for text) as defined in [Postgrest API documentation](https://postgrest.org/en/stable/references/api/tables_views.html?highlight=operators#json-columns) and specify the data type of the property (e.g. the column should look something like `metadata->some_int_value::int`).

``
_62
import { SupabaseFilterRPCCall, SupabaseVectorStore } from 'langchain/vectorstores/supabase'
_62
import { OpenAIEmbeddings } from 'langchain/embeddings/openai'
_62
import { createClient } from '@supabase/supabase-js'
_62
_62
// First, follow set-up instructions above
_62
_62
const privateKey = process.env.SUPABASE_SERVICE_ROLE_KEY
_62
if (!privateKey) throw new Error(`Expected env var SUPABASE_SERVICE_ROLE_KEY`)
_62
_62
const url = process.env.SUPABASE_URL
_62
if (!url) throw new Error(`Expected env var SUPABASE_URL`)
_62
_62
export const run = async () => {
_62
const client = createClient(url, privateKey)
_62
_62
const embeddings = new OpenAIEmbeddings()
_62
_62
const store = new SupabaseVectorStore(embeddings, {
_62
    client,
_62
    tableName: 'documents',
_62
})
_62
_62
const docs = [\
_62\
    {\
_62\
      pageContent:\
_62\
        'This is a long text, but it actually means something because vector database does not understand Lorem Ipsum. So I would need to expand upon the notion of quantum fluff, a theoretical concept where subatomic particles coalesce to form transient multidimensional spaces. Yet, this abstraction holds no real-world application or comprehensible meaning, reflecting a cosmic puzzle.',\
_62\
      metadata: { b: 1, c: 10, stuff: 'right' },\
_62\
    },\
_62\
    {\
_62\
      pageContent:\
_62\
        'This is a long text, but it actually means something because vector database does not understand Lorem Ipsum. So I would need to proceed by discussing the echo of virtual tweets in the binary corridors of the digital universe. Each tweet, like a pixelated canary, hums in an unseen frequency, a fascinatingly perplexing phenomenon that, while conjuring vivid imagery, lacks any concrete implication or real-world relevance, portraying a paradox of multidimensional spaces in the age of cyber folklore.',\
_62\
      metadata: { b: 2, c: 9, stuff: 'right' },\
_62\
    },\
_62\
    { pageContent: 'hello', metadata: { b: 1, c: 9, stuff: 'right' } },\
_62\
    { pageContent: 'hello', metadata: { b: 1, c: 9, stuff: 'wrong' } },\
_62\
    { pageContent: 'hi', metadata: { b: 2, c: 8, stuff: 'right' } },\
_62\
    { pageContent: 'bye', metadata: { b: 3, c: 7, stuff: 'right' } },\
_62\
    { pageContent: "what's this", metadata: { b: 4, c: 6, stuff: 'right' } },\
_62\
]
_62
_62
await store.addDocuments(docs)
_62
_62
const funcFilterA: SupabaseFilterRPCCall = (rpc) =>
_62
    rpc
_62
      .filter('metadata->b::int', 'lt', 3)
_62
      .filter('metadata->c::int', 'gt', 7)
_62
      .textSearch('content', `'multidimensional' & 'spaces'`, {
_62
        config: 'english',
_62
      })
_62
_62
const resultA = await store.similaritySearch('quantum', 4, funcFilterA)
_62
_62
const funcFilterB: SupabaseFilterRPCCall = (rpc) =>
_62
    rpc
_62
      .filter('metadata->b::int', 'lt', 3)
_62
      .filter('metadata->c::int', 'gt', 7)
_62
      .filter('metadata->>stuff', 'eq', 'right')
_62
_62
const resultB = await store.similaritySearch('hello', 2, funcFilterB)
_62
_62
console.log(resultA, resultB)
_62
}
``

## Hybrid search [\#](\#hybrid-search)

LangChain supports the concept of a hybrid search, which combines Similarity Search with Full Text Search. Read the official docs to get started: [Supabase Hybrid Search](https://js.langchain.com/docs/modules/indexes/retrievers/supabase-hybrid).

You can install the LangChain Hybrid Search function though our [database.dev package manager](https://database.dev/langchain/hybrid_search).

## Resources [\#](\#resources)

- Official [LangChain site](https://langchain.com/).
- Official [LangChain docs](https://js.langchain.com/docs/modules/indexes/vector_stores/integrations/supabase).
- Supabase [Hybrid Search](https://js.langchain.com/docs/modules/indexes/retrievers/supabase-hybrid).
```

----

