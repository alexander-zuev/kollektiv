Markdown content for item 0

 AI & Vectors

# Semantic Text Deduplication

## Finding duplicate movie reviews with Supabase Vecs.

* * *

This guide will walk you through a ["Semantic Text Deduplication"](https://github.com/supabase/supabase/blob/master/examples/ai/semantic_text_deduplication.ipynb) example using Colab and Supabase Vecs. You'll learn how to find similar movie reviews using embeddings, and remove any that seem like duplicates. You will:

1. Launch a Postgres database that uses pgvector to store embeddings
2. Launch a notebook that connects to your database
3. Load the IMDB dataset
4. Use the `sentence-transformers/all-MiniLM-L6-v2` model to create an embedding representing the semantic meaning of each review.
5. Search for all duplicates.

## Project setup [\#](\#project-setup)

Let's create a new Postgres database. This is as simple as starting a new Project in Supabase:

1. [Create a new project](https://database.new/) in the Supabase dashboard.
2. Enter your project details. Remember to store your password somewhere safe.

Your database will be available in less than a minute.

**Finding your credentials:**

You can find your project credentials inside the project [settings](https://supabase.com/dashboard/project/_/settings/), including:

- [Database credentials](https://supabase.com/dashboard/project/_/settings/database): connection strings and connection pooler details.
- [API credentials](https://supabase.com/dashboard/project/_/settings/database): your serverless API URL and `anon` / `service_role` keys.

## Launching a notebook [\#](\#launching-a-notebook)

Launch our [`semantic_text_deduplication`](https://github.com/supabase/supabase/blob/master/examples/ai/semantic_text_deduplication.ipynb) notebook in Colab:

[![](https://supabase.com/docs/img/ai/colab-badge.svg)](https://colab.research.google.com/github/supabase/supabase/blob/master/examples/ai/semantic_text_deduplication.ipynb)

At the top of the notebook, you'll see a button `Copy to Drive`. Click this button to copy the notebook to your Google Drive.

## Connecting to your database [\#](\#connecting-to-your-database)

Inside the Notebook, find the cell which specifies the `DB_CONNECTION`. It will contain some code like this:

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

Replace the `DB_CONNECTION` with your own connection string for your database. You can find the Postgres connection string in the [Database Settings](https://supabase.com/dashboard/project/_/settings/database) of your Supabase project.

SQLAlchemy requires the connection string to start with `postgresql://` (instead of `postgres://`). Don't forget to rename this after copying the string from the dashboard.

You must use the "connection pooling" string (domain ending in `*.pooler.supabase.com`) with Google Colab since Colab does not support IPv6.

## Stepping through the notebook [\#](\#stepping-through-the-notebook)

Now all that's left is to step through the notebook. You can do this by clicking the "execute" button ( `ctrl+enter`) at the top left of each code cell. The notebook guides you through the process of creating a collection, adding data to it, and querying it.

You can view the inserted items in the [Table Editor](https://supabase.com/dashboard/project/_/editor/), by selecting the `vecs` schema from the schema dropdown.

![Colab documents](https://supabase.com/docs/img/ai/google-colab/colab-documents.png)

## Deployment [\#](\#deployment)

If you have your own infrastructure for deploying Python apps, you can continue to use `vecs` as described in this guide.

Alternatively if you would like to quickly deploy using Supabase, check out our guide on using the [Hugging Face Inference API](/docs/guides/ai/hugging-face) in Edge Functions using TypeScript.

## Next steps [\#](\#next-steps)

You can now start building your own applications with Vecs. Check our [examples](/docs/guides/ai#examples) for ideas.

----

Markdown content for item 1

 AI & Vectors

# Semantic Image Search with Amazon Titan

## Implement semantic image search with Amazon Titan and Supabase Vector in Python.

* * *

[Amazon Bedrock](https://aws.amazon.com/bedrock) is a fully managed service that offers a choice of high-performing foundation models (FMs) from leading AI companies like AI21 Labs, Anthropic, Cohere, Meta, Mistral AI, Stability AI, and Amazon. Each model is accessible through a common API which implements a broad set of features to help build generative AI applications with security, privacy, and responsible AI in mind.

[Amazon Titan](https://aws.amazon.com/bedrock/titan/) is a family of foundation models (FMs) for text and image generation, summarization, classification, open-ended Q&A, information extraction, and text or image search.

In this guide we'll look at how we can get started with Amazon Bedrock and Supabase Vector in Python using the Amazon Titan multimodal model and the [vecs client](/docs/guides/ai/vecs-python-client).

You can find the full application code as a Python Poetry project on [GitHub](https://github.com/supabase/supabase/tree/master/examples/ai/aws_bedrock_image_search).

## Create a new Python project with Poetry [\#](\#create-a-new-python-project-with-poetry)

[Poetry](https://python-poetry.org/) provides packaging and dependency management for Python. If you haven't already, install poetry via pip:

`
_10
pip install poetry
`

Then initialize a new project:

`
_10
poetry new aws_bedrock_image_search
`

## Spin up a Postgres Database with pgvector [\#](\#spin-up-a-postgres-database-with-pgvector)

If you haven't already, head over to [database.new](https://database.new) and create a new project. Every Supabase project comes with a full Postgres database and the [pgvector extension](/docs/guides/database/extensions/pgvector) preconfigured.

When creating your project, make sure to note down your database password as you will need it to construct the `DB_URL` in the next step.

You can find the database connection string in your Supabase Dashboard [database settings](https://supabase.com/dashboard/project/_/settings/database). Select "Use connection pooling" with `Mode: Session` for a direct connection to your Postgres database. It will look something like this:

`
_10
postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
`

## Install the dependencies [\#](\#install-the-dependencies)

We will need to add the following dependencies to our project:

- [`vecs`](https://github.com/supabase/vecs#vecs): Supabase Vector Python Client.
- [`boto3`](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html): AWS SDK for Python.
- [`matplotlib`](https://matplotlib.org/): for displaying our image result.

`
_10
poetry add vecs boto3 matplotlib
`

## Import the necessary dependencies [\#](\#import-the-necessary-dependencies)

At the top of your main python script, import the dependencies and store your `DB URL` from above in a variable:

`
_10
import sys
_10
import boto3
_10
import vecs
_10
import json
_10
import base64
_10
from matplotlib import pyplot as plt
_10
from matplotlib import image as mpimg
_10
from typing import Optional
_10
_10
DB_CONNECTION = "postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres"
`

Next, get the [credentials to your AWS account](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html) and instantiate the `boto3` client:

`
_10
bedrock_client = boto3.client(
_10
    'bedrock-runtime',
_10
    region_name='us-west-2',
_10
    # Credentials from your AWS account
_10
    aws_access_key_id='<replace_your_own_credentials>',
_10
    aws_secret_access_key='<replace_your_own_credentials>',
_10
    aws_session_token='<replace_your_own_credentials>',
_10
)
`

## Create embeddings for your images [\#](\#create-embeddings-for-your-images)

In the root of your project, create a new folder called `images` and add some images. You can use the images from the example project on [GitHub](https://github.com/supabase/supabase/tree/master/examples/ai/aws_bedrock_image_search/images) or you can find license free images on [unsplash](https://unsplash.com).

To send images to the Amazon Bedrock API we need to need to encode them as `base64` strings. Create the following helper methods:

`
_44
def readFileAsBase64(file_path):
_44
    """Encode image as base64 string."""
_44
    try:
_44
        with open(file_path, "rb") as image_file:
_44
            input_image = base64.b64encode(image_file.read()).decode("utf8")
_44
        return input_image
_44
    except:
_44
        print("bad file name")
_44
        sys.exit(0)
_44
_44
_44
def construct_bedrock_image_body(base64_string):
_44
    """Construct the request body.
_44
_44
    https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-titan-embed-mm.html
_44
    """
_44
    return json.dumps(
_44
        {
_44
            "inputImage": base64_string,
_44
            "embeddingConfig": {"outputEmbeddingLength": 1024},
_44
        }
_44
    )
_44
_44
_44
def get_embedding_from_titan_multimodal(body):
_44
    """Invoke the Amazon Titan Model via API request."""
_44
    response = bedrock_client.invoke_model(
_44
        body=body,
_44
        modelId="amazon.titan-embed-image-v1",
_44
        accept="application/json",
_44
        contentType="application/json",
_44
    )
_44
_44
    response_body = json.loads(response.get("body").read())
_44
    print(response_body)
_44
    return response_body["embedding"]
_44
_44
_44
def encode_image(file_path):
_44
    """Generate embedding for the image at file_path."""
_44
    base64_string = readFileAsBase64(file_path)
_44
    body = construct_bedrock_image_body(base64_string)
_44
    emb = get_embedding_from_titan_multimodal(body)
_44
    return emb
`

Next, create a `seed` method, which will create a new Supabase Vector Collection, generate embeddings for your images, and upsert the embeddings into your database:

`
_40
def seed():
_40
    # create vector store client
_40
    vx = vecs.create_client(DB_CONNECTION)
_40
_40
    # get or create a collection of vectors with 1024 dimensions
_40
    images = vx.get_or_create_collection(name="image_vectors", dimension=1024)
_40
_40
    # Generate image embeddings with Amazon Titan Model
_40
    img_emb1 = encode_image('./images/one.jpg')
_40
    img_emb2 = encode_image('./images/two.jpg')
_40
    img_emb3 = encode_image('./images/three.jpg')
_40
    img_emb4 = encode_image('./images/four.jpg')
_40
_40
    # add records to the *images* collection
_40
    images.upsert(
_40
        records=[\
_40\
            (\
_40\
                "one.jpg",       # the vector's identifier\
_40\
                img_emb1,        # the vector. list or np.array\
_40\
                {"type": "jpg"}  # associated  metadata\
_40\
            ), (\
_40\
                "two.jpg",\
_40\
                img_emb2,\
_40\
                {"type": "jpg"}\
_40\
            ), (\
_40\
                "three.jpg",\
_40\
                img_emb3,\
_40\
                {"type": "jpg"}\
_40\
            ), (\
_40\
                "four.jpg",\
_40\
                img_emb4,\
_40\
                {"type": "jpg"}\
_40\
            )\
_40\
        ]
_40
    )
_40
    print("Inserted images")
_40
_40
    # index the collection for fast search performance
_40
    images.create_index()
_40
    print("Created index")
`

Add this method as a script in your `pyproject.toml` file:

`
_10
[tool.poetry.scripts]
_10
seed = "image_search.main:seed"
_10
search = "image_search.main:search"
`

After activating the virtual environtment with `poetry shell` you can now run your seed script via `poetry run seed`. You can inspect the generated embeddings in your Supabase Dashboard by visiting the [Table Editor](https://supabase.com/dashboard/project/_/editor), selecting the `vecs` schema, and the `image_vectors` table.

## Perform an image search from a text query [\#](\#perform-an-image-search-from-a-text-query)

With Supabase Vector we can easily query our embeddings. We can use either an image as the search input or alternatively we can generate an embedding from a string input and use that as the query input:

`
_28
def search(query_term: Optional[str] = None):
_28
    if query_term is None:
_28
        query_term = sys.argv[1]
_28
_28
    # create vector store client
_28
    vx = vecs.create_client(DB_CONNECTION)
_28
    images = vx.get_or_create_collection(name="image_vectors", dimension=1024)
_28
_28
    # Encode text query
_28
    text_emb = get_embedding_from_titan_multimodal(json.dumps(
_28
        {
_28
            "inputText": query_term,
_28
            "embeddingConfig": {"outputEmbeddingLength": 1024},
_28
        }
_28
    ))
_28
_28
    # query the collection filtering metadata for "type" = "jpg"
_28
    results = images.query(
_28
        data=text_emb,                      # required
_28
        limit=1,                            # number of records to return
_28
        filters={"type": {"$eq": "jpg"}},   # metadata filters
_28
    )
_28
    result = results[0]
_28
    print(result)
_28
    plt.title(result)
_28
    image = mpimg.imread('./images/' + result)
_28
    plt.imshow(image)
_28
    plt.show()
`

By limiting the query to one result, we can show the most relevant image to the user. Finally we use `matplotlib` to show the image result to the user.

That's it, go ahead and test it out by running `poetry run search` and you will be presented with an image of a "bike in front of a red brick wall".

## Conclusion [\#](\#conclusion)

With just a couple of lines of Python you are able to implement image search as well as reverse image search using the Amazon Titan multimodal model and Supabase Vector.

----

Markdown content for item 2

 AI & Vectors

# Face similarity search

## Identify the celebrities who look most similar to you using Supabase Vecs.

* * *

This guide will walk you through a ["Face Similarity Search"](https://github.com/supabase/supabase/blob/master/examples/ai/face_similarity.ipynb) example using Colab and Supabase Vecs. You will be able to identify the celebrities who look most similar to you (or any other person). You will:

1. Launch a Postgres database that uses pgvector to store embeddings
2. Launch a notebook that connects to your database
3. Load the " `ashraq/tmdb-people-image`" celebrity dataset
4. Use the `face_recognition` model to create an embedding for every celebrity photo.
5. Search for similar faces inside the dataset.

## Project setup [\#](\#project-setup)

Let's create a new Postgres database. This is as simple as starting a new Project in Supabase:

1. [Create a new project](https://database.new/) in the Supabase dashboard.
2. Enter your project details. Remember to store your password somewhere safe.

Your database will be available in less than a minute.

**Finding your credentials:**

You can find your project credentials inside the project [settings](https://supabase.com/dashboard/project/_/settings/), including:

- [Database credentials](https://supabase.com/dashboard/project/_/settings/database): connection strings and connection pooler details.
- [API credentials](https://supabase.com/dashboard/project/_/settings/database): your serverless API URL and `anon` / `service_role` keys.

## Launching a notebook [\#](\#launching-a-notebook)

Launch our [`semantic_text_deduplication`](https://github.com/supabase/supabase/blob/master/examples/ai/face_similarity.ipynb) notebook in Colab:

[![](https://supabase.com/docs/img/ai/colab-badge.svg)](https://colab.research.google.com/github/supabase/supabase/blob/master/examples/ai/face_similarity.ipynb)

At the top of the notebook, you'll see a button `Copy to Drive`. Click this button to copy the notebook to your Google Drive.

## Connecting to your database [\#](\#connecting-to-your-database)

Inside the Notebook, find the cell which specifies the `DB_CONNECTION`. It will contain some code like this:

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

Replace the `DB_CONNECTION` with your own connection string for your database. You can find the Postgres connection string in the [Database Settings](https://supabase.com/dashboard/project/_/settings/database) of your Supabase project.

SQLAlchemy requires the connection string to start with `postgresql://` (instead of `postgres://`). Don't forget to rename this after copying the string from the dashboard.

You must use the "connection pooling" string (domain ending in `*.pooler.supabase.com`) with Google Colab since Colab does not support IPv6.

## Stepping through the notebook [\#](\#stepping-through-the-notebook)

Now all that's left is to step through the notebook. You can do this by clicking the "execute" button ( `ctrl+enter`) at the top left of each code cell. The notebook guides you through the process of creating a collection, adding data to it, and querying it.

You can view the inserted items in the [Table Editor](https://supabase.com/dashboard/project/_/editor/), by selecting the `vecs` schema from the schema dropdown.

![Colab documents](https://supabase.com/docs/img/ai/google-colab/colab-documents.png)

## Next steps [\#](\#next-steps)

You can now start building your own applications with Vecs. Check our [examples](/docs/guides/ai#examples) for ideas.

----

