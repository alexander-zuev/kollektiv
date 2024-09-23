# Content for item 0

```markdown
Loading \[MathJax\]/jax/output/CommonHTML/fonts/TeX/fontdata.js

[Skip to content](https://docs.llamaindex.ai/en/stable/examples/evaluation/pairwise_eval/#pairwise-evaluator)

# Pairwise Evaluator [¶](https://docs.llamaindex.ai/en/stable/examples/evaluation/pairwise_eval/\#pairwise-evaluator)

This notebook uses the `PairwiseEvaluator` module to see if an evaluation LLM would prefer one query engine over another.

In \[ \]:

Copied!

```
%pip install llama-index-llms-openai

```

%pip install llama-index-llms-openai

In \[ \]:

Copied!

```
# attach to the same event-loop
import nest_asyncio

nest_asyncio.apply()

```

\# attach to the same event-loop
import nest\_asyncio

nest\_asyncio.apply()

In \[ \]:

Copied!

```
# configuring logger to INFO level
import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

```

\# configuring logger to INFO level
import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

In \[ \]:

Copied!

```
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Response
from llama_index.llms.openai import OpenAI
from llama_index.core.evaluation import PairwiseComparisonEvaluator
from llama_index.core.node_parser import SentenceSplitter
import pandas as pd

pd.set_option("display.max_colwidth", 0)

```

from llama\_index.core import VectorStoreIndex, SimpleDirectoryReader, Response
from llama\_index.llms.openai import OpenAI
from llama\_index.core.evaluation import PairwiseComparisonEvaluator
from llama\_index.core.node\_parser import SentenceSplitter
import pandas as pd

pd.set\_option("display.max\_colwidth", 0)

Using GPT-4 here for evaluation

In \[ \]:

Copied!

```
# gpt-4
gpt4 = OpenAI(temperature=0, model="gpt-4")

evaluator_gpt4 = PairwiseComparisonEvaluator(llm=gpt4)

```

\# gpt-4
gpt4 = OpenAI(temperature=0, model="gpt-4")

evaluator\_gpt4 = PairwiseComparisonEvaluator(llm=gpt4)

In \[ \]:

Copied!

```
documents = SimpleDirectoryReader("./test_wiki_data/").load_data()

```

documents = SimpleDirectoryReader("./test\_wiki\_data/").load\_data()

In \[ \]:

Copied!

```
# create vector index
splitter_512 = SentenceSplitter(chunk_size=512)
vector_index1 = VectorStoreIndex.from_documents(
    documents, transformations=[splitter_512]
)

splitter_128 = SentenceSplitter(chunk_size=128)
vector_index2 = VectorStoreIndex.from_documents(
    documents, transformations=[splitter_128]
)

```

\# create vector index
splitter\_512 = SentenceSplitter(chunk\_size=512)
vector\_index1 = VectorStoreIndex.from\_documents(
documents, transformations=\[splitter\_512\]
)

splitter\_128 = SentenceSplitter(chunk\_size=128)
vector\_index2 = VectorStoreIndex.from\_documents(
documents, transformations=\[splitter\_128\]
)

In \[ \]:

Copied!

```
query_engine1 = vector_index1.as_query_engine(similarity_top_k=2)
query_engine2 = vector_index2.as_query_engine(similarity_top_k=8)

```

query\_engine1 = vector\_index1.as\_query\_engine(similarity\_top\_k=2)
query\_engine2 = vector\_index2.as\_query\_engine(similarity\_top\_k=8)

In \[ \]:

Copied!

```
# define jupyter display function
def display_eval_df(query, response1, response2, eval_result) -> None:
    eval_df = pd.DataFrame(
        {
            "Query": query,
            "Reference Response (Answer 1)": response2,
            "Current Response (Answer 2)": response1,
            "Score": eval_result.score,
            "Reason": eval_result.feedback,
        },
        index=[0],
    )
    eval_df = eval_df.style.set_properties(
        **{
            "inline-size": "300px",
            "overflow-wrap": "break-word",
        },
        subset=["Current Response (Answer 2)", "Reference Response (Answer 1)"]
    )
    display(eval_df)

```

\# define jupyter display function
def display\_eval\_df(query, response1, response2, eval\_result) -> None:
eval\_df = pd.DataFrame(
{
"Query": query,
"Reference Response (Answer 1)": response2,
"Current Response (Answer 2)": response1,
"Score": eval\_result.score,
"Reason": eval\_result.feedback,
},
index=\[0\],
)
eval\_df = eval\_df.style.set\_properties(
\*\*{
"inline-size": "300px",
"overflow-wrap": "break-word",
},
subset=\["Current Response (Answer 2)", "Reference Response (Answer 1)"\]
)
display(eval\_df)

To run evaluations you can call the `.evaluate_response()` function on the `Response` object return from the query to run the evaluations. Lets evaluate the outputs of the vector\_index.

In \[ \]:

Copied!

```
# query_str = "How did New York City get its name?"
query_str = "What was the role of NYC during the American Revolution?"
# query_str = "Tell me about the arts and culture of NYC"
response1 = str(query_engine1.query(query_str))
response2 = str(query_engine2.query(query_str))

```

\# query\_str = "How did New York City get its name?"
query\_str = "What was the role of NYC during the American Revolution?"
\# query\_str = "Tell me about the arts and culture of NYC"
response1 = str(query\_engine1.query(query\_str))
response2 = str(query\_engine2.query(query\_str))

By default, we enforce "consistency" in the pairwise comparison.

We try feeding in the candidate, reference pair, and then swap the order of the two, and make sure that the results are still consistent (or return a TIE if not).

In \[ \]:

Copied!

```
eval_result = await evaluator_gpt4.aevaluate(
    query_str, response=response1, reference=response2
)

```

eval\_result = await evaluator\_gpt4.aevaluate(
query\_str, response=response1, reference=response2
)

```
INFO:openai:message='OpenAI API response' path=https://api.openai.com/v1/chat/completions processing_ms=5536 request_id=8a8f154ee676b2e86ea24b7046e9b80b response_code=200
message='OpenAI API response' path=https://api.openai.com/v1/chat/completions processing_ms=5536 request_id=8a8f154ee676b2e86ea24b7046e9b80b response_code=200
INFO:openai:message='OpenAI API response' path=https://api.openai.com/v1/chat/completions processing_ms=9766 request_id=dfee84227112b1311b4411492f4c8764 response_code=200
message='OpenAI API response' path=https://api.openai.com/v1/chat/completions processing_ms=9766 request_id=dfee84227112b1311b4411492f4c8764 response_code=200

```

In \[ \]:

Copied!

```
display_eval_df(query_str, response1, response2, eval_result)

```

display\_eval\_df(query\_str, response1, response2, eval\_result)

|  | Query | Reference Response (Answer 1) | Current Response (Answer 2) | Score | Reason |
| --- | --- | --- | --- | --- | --- |
| 0 | What was the role of NYC during the American Revolution? | During the American Revolution, New York City served as a significant military and political base of operations for the British forces. After the Battle of Long Island in 1776, in which the Americans were defeated, the British made the city their center of operations in North America. The city was regained by the Dutch in 1673 but was renamed New York in 1674. It became the capital of the United States from 1785 to 1790. Additionally, New York City was a haven for Loyalist refugees and escaped slaves who joined the British lines for freedom. The British forces transported thousands of freedmen for resettlement in Nova Scotia and other locations, including England and the Caribbean. | During the American Revolution, New York City served as the military and political base of operations for the British in North America. It was also a haven for Loyalist refugees and escaped slaves who joined the British lines in search of freedom. The city played a significant role in the war, with the Battle of Long Island being the largest battle of the American Revolutionary War fought within its modern-day borough of Brooklyn. After the war, when the British forces evacuated, they transported freedmen to Nova Scotia, England, and the Caribbean for resettlement. | 0.500000 | It is not clear which answer is better. |

**NOTE**: By default, we enforce consensus by flipping the order of response/reference and making sure that the answers are opposites.

We can disable this - which can lead to more inconsistencies!

In \[ \]:

Copied!

```
evaluator_gpt4_nc = PairwiseComparisonEvaluator(
    llm=gpt4, enforce_consensus=False
)

```

evaluator\_gpt4\_nc = PairwiseComparisonEvaluator(
llm=gpt4, enforce\_consensus=False
)

In \[ \]:

Copied!

```
eval_result = await evaluator_gpt4_nc.aevaluate(
    query_str, response=response1, reference=response2
)

```

eval\_result = await evaluator\_gpt4\_nc.aevaluate(
query\_str, response=response1, reference=response2
)

```
INFO:openai:message='OpenAI API response' path=https://api.openai.com/v1/chat/completions processing_ms=6714 request_id=472a1f0829846adc1b4347ba4b99c0dd response_code=200
message='OpenAI API response' path=https://api.openai.com/v1/chat/completions processing_ms=6714 request_id=472a1f0829846adc1b4347ba4b99c0dd response_code=200

```

In \[ \]:

Copied!

```
display_eval_df(query_str, response1, response2, eval_result)

```

display\_eval\_df(query\_str, response1, response2, eval\_result)

|  | Query | Reference Response (Answer 1) | Current Response (Answer 2) | Score | Reason |
| --- | --- | --- | --- | --- | --- |
| 0 | What was the role of NYC during the American Revolution? | During the American Revolution, New York City served as a significant military and political base of operations for the British forces. After the Battle of Long Island in 1776, in which the Americans were defeated, the British made the city their center of operations in North America. The city was regained by the Dutch in 1673 but was renamed New York in 1674. It became the capital of the United States from 1785 to 1790. Additionally, New York City was a haven for Loyalist refugees and escaped slaves who joined the British lines for freedom. The British forces transported thousands of freedmen for resettlement in Nova Scotia and other locations, including England and the Caribbean. | During the American Revolution, New York City served as the military and political base of operations for the British in North America. It was also a haven for Loyalist refugees and escaped slaves who joined the British lines in search of freedom. The city played a significant role in the war, with the Battle of Long Island being the largest battle of the American Revolutionary War fought within its modern-day borough of Brooklyn. After the war, when the British forces evacuated, they transported freedmen to Nova Scotia, England, and the Caribbean for resettlement. | 0.000000 | 1<br>Answer 1 is better because it provides more detailed information about the role of New York City during the American Revolution. It not only mentions the city's role as a British base and a haven for Loyalist refugees and escaped slaves, but also provides additional historical context such as the city being renamed and becoming the capital of the United States. |

In \[ \]:

Copied!

```
eval_result = await evaluator_gpt4_nc.aevaluate(
    query_str, response=response2, reference=response1
)

```

eval\_result = await evaluator\_gpt4\_nc.aevaluate(
query\_str, response=response2, reference=response1
)

```
INFO:openai:message='OpenAI API response' path=https://api.openai.com/v1/chat/completions processing_ms=9252 request_id=b73bbe6b10d878ed8138785638232866 response_code=200
message='OpenAI API response' path=https://api.openai.com/v1/chat/completions processing_ms=9252 request_id=b73bbe6b10d878ed8138785638232866 response_code=200

```

In \[ \]:

Copied!

```
display_eval_df(query_str, response2, response1, eval_result)

```

display\_eval\_df(query\_str, response2, response1, eval\_result)

|  | Query | Reference Response (Answer 1) | Current Response (Answer 2) | Score | Reason |
| --- | --- | --- | --- | --- | --- |
| 0 | What was the role of NYC during the American Revolution? | During the American Revolution, New York City served as the military and political base of operations for the British in North America. It was also a haven for Loyalist refugees and escaped slaves who joined the British lines in search of freedom. The city played a significant role in the war, with the Battle of Long Island being the largest battle of the American Revolutionary War fought within its modern-day borough of Brooklyn. After the war, when the British forces evacuated, they transported freedmen to Nova Scotia, England, and the Caribbean for resettlement. | During the American Revolution, New York City served as a significant military and political base of operations for the British forces. After the Battle of Long Island in 1776, in which the Americans were defeated, the British made the city their center of operations in North America. The city was regained by the Dutch in 1673 but was renamed New York in 1674. It became the capital of the United States from 1785 to 1790. Additionally, New York City was a haven for Loyalist refugees and escaped slaves who joined the British lines for freedom. The British forces transported thousands of freedmen for resettlement in Nova Scotia and other locations, including England and the Caribbean. | 0.000000 | 1<br>Answer 1 is better because it directly addresses the user's query about the role of NYC during the American Revolution. It provides a more detailed and accurate account of the city's role, including its status as a British base, a haven for Loyalist refugees and escaped slaves, and the site of the Battle of Long Island. Answer 2 includes some irrelevant information about the city being regained by the Dutch and renamed, which occurred before the American Revolution, and its status as the capital of the United States, which happened after the Revolution. |

## Running on some more Queries [¶](https://docs.llamaindex.ai/en/stable/examples/evaluation/pairwise_eval/\#running-on-some-more-queries)

In \[ \]:

Copied!

```
query_str = "Tell me about the arts and culture of NYC"
response1 = str(query_engine1.query(query_str))
response2 = str(query_engine2.query(query_str))

```

query\_str = "Tell me about the arts and culture of NYC"
response1 = str(query\_engine1.query(query\_str))
response2 = str(query\_engine2.query(query\_str))

In \[ \]:

Copied!

```
eval_result = await evaluator_gpt4.aevaluate(
    query_str, response=response1, reference=response2
)

```

eval\_result = await evaluator\_gpt4.aevaluate(
query\_str, response=response1, reference=response2
)

```
INFO:openai:message='OpenAI API response' path=https://api.openai.com/v1/chat/completions processing_ms=6053 request_id=749fdbde59bf8d1056a8be6e211d20d9 response_code=200
message='OpenAI API response' path=https://api.openai.com/v1/chat/completions processing_ms=6053 request_id=749fdbde59bf8d1056a8be6e211d20d9 response_code=200
INFO:openai:message='OpenAI API response' path=https://api.openai.com/v1/chat/completions processing_ms=7309 request_id=ba09bb38320b60cf09dbebb1df2c732b response_code=200
message='OpenAI API response' path=https://api.openai.com/v1/chat/completions processing_ms=7309 request_id=ba09bb38320b60cf09dbebb1df2c732b response_code=200

```

In \[ \]:

Copied!

```
display_eval_df(query_str, response1, response2, eval_result)

```

display\_eval\_df(query\_str, response1, response2, eval\_result)

|  | Query | Reference Response (Answer 1) | Current Response (Answer 2) | Score | Reason |
| --- | --- | --- | --- | --- | --- |
| 0 | Tell me about the arts and culture of NYC | New York City is known for its vibrant arts and culture scene. It is home to over 2,000 arts and cultural organizations, as well as more than 500 art galleries. The city has a rich history of cultural institutions, such as Carnegie Hall and the Metropolitan Museum of Art, which are internationally renowned. The Broadway musical, a popular stage form, originated in New York City in the 1880s. The city has also been a hub for Jewish American literature and has been the birthplace of various cultural movements, including the Harlem Renaissance, abstract expressionism, and hip-hop. New York City is considered the dance capital of the world and has a thriving theater scene. The city is also known for its museums, including the Guggenheim and the Metropolitan Museum of Art, which participate in the annual Museum Mile Festival. Additionally, New York City hosts some of the world's most lucrative art auctions. Lincoln Center for the Performing Arts is a major cultural hub, housing influential arts organizations such as the Metropolitan Opera and the New York Philharmonic. Overall, New York City is often regarded as the cultural capital of the world. | New York City is known for its vibrant arts and culture scene. It is home to numerous influential arts organizations, including the Metropolitan Opera, New York City Opera, New York Philharmonic, and New York City Ballet. The city also has a thriving theater district, with Broadway shows selling billions of dollars worth of tickets each season. Additionally, there are over 2,000 arts and cultural organizations and more than 500 art galleries in the city. New York City has a rich history of cultural institutions, such as Carnegie Hall and the Metropolitan Museum of Art, which are internationally renowned. The city's arts and culture have been strongly influenced by its diverse immigrant population, and many plays and musicals are set in or inspired by New York City itself. | 0.000000 | 1<br>Answer 1 provides a more comprehensive and detailed response to the user's query about the arts and culture of NYC. It not only mentions the city's major cultural institutions and organizations, but also discusses the city's role in various cultural movements, its status as the dance capital of the world, its museums, and its art auctions. It also mentions the annual Museum Mile Festival, which Answer 2 does not. |

Back to top
```

----
