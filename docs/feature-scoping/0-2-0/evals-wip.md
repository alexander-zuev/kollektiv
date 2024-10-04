# Retrieval Augmented Generation Evaluation

Currently, OmniClaude doesn't have any measurement setup on the quality of RAG retrieval. There is a need to set up a
proper evaluation suite.

This is necessary to enable the following:
- measurement of impact of changes, for example of different chunking strategies, retrieval strategies, LLM setup on
  the key success metrics of the system
- measurement of RAG quality is a key pre-requisite to rolling out these types of systems in production

## Goals & Scope
1. Define key performance metrics and approaches to measurement of RAG
2. Setup basic evaluation pipeline to measure the defined metrics

## Implementation

### Summary
Performance of a RAG system is typically measured by:
- end-to-end performance (i.e. how good does the overall system perform?)
- retrieval performance (i.e. how relevant are retrieved results?)

### Requirements
- Eval suite should allow efficient recreation of new evaluation datasets, given that chunks can frequently change.
  Irrespective of chunks, the input data will not change (at least until I add multi-modal capabilities)
- Ideal setup is to:
  - Generate 30-50 (TBD) questions per set of documents using a large-context LLM (Gemini Flash, for example)
  - Generate detailed answers to these questions based on actual content, again using a large-context LLM
  - Iterate over chunks (can be very expensive) to create a list of 'correct chunks' for a given dataset.
- How to ensure efficiency?
  - Batch APIs (if available). At least OpenAI has one as well as Gemini.
  - Random sampling of documents? For example, generate questions for a random set of documents (never for chunks
    within different documents):
    - if documents size is 'small' -> use full content
    - if documents size is more than a threshold -> use statistically significant / meaningful percentage of documents
  - Proxies? Headers could be used as proxies to efficiently find relevant chunks although not ideal one.
  - Reduce evaluation dataset size - the goal is to demonstrate overall approach that can be scaled, if necessary
- Always track costs and display running costs of eval suite for:
  - Generation
  - Evaluation
- The goal is to build a small but highly representative evaluation dataset and leverage LLM judges to
evaluate different components of the RAG system.

#### Implementation options
Option 1. Custom evaluation class (requires more time)
Option 2. Evaluation library (start with this)

### Current setup

1. [X] Using `ragas` library to measure both retrieval and generation metrics:
  - Generation:
    - Faithfulness
    - Answer relevancy
    - Answer correctness
  - Retrieval
    - Context recall
    - Context precision
2. [] Efficient re-use:
   - Refactor the pipeline to run in one click
3. [] Versioning and storages
4. [] Visualization and reporting of results
5. [] Costs calculation and visualization

**Faithfulness**
- Measures factual consistency of the generated answer against the given context. The generated answer is
regarded as faithful if all the claims made in the answer can be inferred from the given context.

**Answer Relevance**
- The evaluation metric, Answer Relevancy, focuses on assessing how pertinent the generated answer is to the given
prompt. A lower score is assigned to answers that are incomplete or contain redundant information and higher
scores indicate better relevancy.

**Answer Correctness**
- The assessment of Answer Correctness involves gauging the accuracy of the generated answer when compared to the
ground truth. This evaluation relies on the ground truth and the answer, with scores ranging from 0 to 1. A higher
score indicates a closer alignment between the generated answer and the ground truth, signifying better correctness.

#### TODO: Retriever metrics
for this to work I need to setup retrieval of my own contexts.

**Context recall**
- Context recall measures the extent to which the retrieved context aligns with the annotated answer, treated as the
ground truth. It is computed using question, ground truth and the retrieved context, and the values range between 0
and 1, with higher values indicating better performance.

**Context precision**
- Context Precision is a metric that evaluates whether all of the ground-truth relevant items present in the contexts
are ranked higher or not. Ideally all the relevant chunks must appear at the top ranks. This metric is computed
using the question, ground_truth and the contexts, with values ranging between 0 and 1, where higher scores
indicate better precision.

#### TODO: Promptfoo (probably next iteration)
[Link](https://www.promptfoo.dev/docs/guides/evaluate-rag/)
[Link](https://github.com/promptfoo/promptfoo/tree/main/examples/rag-full)



### Research
#### Anthropic Cookbook
[Link](https://github.com/anthropics/anthropic-cookbook/blob/main/skills/retrieval_augmented_generation/guide.ipynb)

Approach Anthropic takes is mirroring a production ready approach. They use the following metrics:
- AVG Precision, Recall, F1 Score, Mean Reciprocal Rank
- End-to-end Accuracy

Important to measure retrieval performance and end-to-end performance separately.

Evaluation dataset consisted of 100 samples with the following structure:
```json
'id' : 'id of the sample',
'question' : "Question that requires 1 or more chunks to generate a correct reply."
'correct_chunks': [
        'correct_chunk_id1',
        'correct_chunk_id2',
],
'correct_answer' : "Correct answer that an LLM should have given"
```
**Retrieval Metrics**

1. Precision
   1. Measures the % of relevant chunks in total number of retrieved chunks. Out of all of the retrieved chunks, how
   many were relevant?
   2. Depends on the number of retrieved chunks per user query
2. Recall
   1. Of the all correct chunks that exist, how many did the system retrieve? Measures the completeness of the system.
   2. High recall indicates comprehensive coverage of necessary information.
3. F1 Score
   1. F1 provides a balanced view of performance between precision and recall
   2. It's the harmonic mean of precision and recall, tending towards the lower of the two values.
   3. Useful in scenarios where both false positives and false negatives are important.
4. Mean Reciprocal Rank
   1. Measures how well a system ranks relevant information.
   2. MRR ranges from 0 to 1, where 1 is perfect (correct answer always first).
   3. It only considers the rank of the first correct result for each query.

Overall, OmniClaude also favors recall over precision because:
- false positives are not so critical because LLM can filter out irrelevant content itself
- false negative is much more critical because the necessary chunk is not returned. For a RAG system, maximizing
  recall should be more important.

**End-to-end Accuracy**
Using LLM-as-a-judge to evaluate whether the generated answer is correct based on the question and the ground truth
answer.

Accuracy is calculated as:
- correct answers divided by total questions, where accurate answers are assessed by an LLM

### Cohere Guide
[Link](https://docs.cohere.com/page/rag-evaluation-deep-dive)

Models tend to assign higher scores to their own answers. This means that for an end-to-end evaluation it's best to
use a different LLM than the one used to generate answers.

Retrieval evaluation was done in the same manner as in the Anthropic cookbook.
End to end evaluation was much more detailed and consisted in assessing:
- faithfulness - how many claims generated in the response are supported by retrieved docs
- correctness - which claims in the response also occur in the gold answer
- coverage - how many of the claims in the gold answer are included in the generated answer (a-la recall)

### Weights & Biases Course
[Link](https://www.wandb.courses/courses/take/rag-in-production/lessons/55179976-evaluation-basics)

Different types of evaluations:
- direct - measure such aspects of toxicity, etc. etc.
- pairwise - choose better of two responses
- reference - against a gold standard

RAG performance is a balance between:
- speed
- reliability

We can make the system super reliable by double-checking the responses, but it will also make it very slow. And vice
versa. The quickest way to evaluate is eyeballing - which is literally about looking with your own eyes at the
responses generated with the system.

**End-to-End Evaluation:**
- Usually about comparing an LLM response against some ground truth data.
**Component Evaluation:**
- RAG systems consist of multiple components, such as:
  - retrieval
  - reranking
  - generation
- We can and should evaluate these pieces independently.

**Evaluations without ground truth:**
- In some cases, evals do not require ground truth, such as in the case of direct or pairwise evaluation. We can compare
two or more responses generated for the same query and judge which one is better based on criteria like tone,
coherence, or informativeness.

[Notebook](https://github.com/wandb/edu/blob/main/rag-advanced/notebooks/Chapter02.ipynb)

**How eval dataset was created**
[Part 1](https://wandb.ai/wandbot/wandbot-eval/reports/How-to-Evaluate-an-LLM-Part-1-Building-an-Evaluation-Dataset-for
-our-LLM-System--Vmlldzo1NTAwNTcy)
[Part 2](https://wandb.ai/wandbot/wandbot-eval/reports/How-to-Evaluate-an-LLM-Part-2-Manual-Evaluation-of-Wandbot-our-LLM-Powered-Docs-Assistant--Vmlldzo1NzU4NTM3)

Before doing any evals, they used 'rigorous eyeballing' based evaluation.

So to recap, how W&B built their eval set:
- production data from users of their Wandbot that is a QA bot over their own doc (very similar to what I am
  building actually)
- they extracted 100+ queries from real users that they manually annotated answers for
- they assessed accuracy of bot replies using domain experts
- E2E accuracy of 66% was achieved

**End to end evaluation without ground truth:**
- Using a powerful LLM it's actually feasible to assess accuracy without ground truth:
  - Generate a list of questions
  - Retrieve chunks
  - Generate the response
  - Use LLM-as-a-judge to assess it

### LlamaIndex

Useful bits and bytes:
- Can be used to generate questions for the [evaluation dataset](https://docs.llamaindex.
  ai/en/stable/module_guides/evaluating/usage_pattern/). Supports Vertex AI, but doesn't support Gemini AI Studio.
  Supports OpenRouter.
- Integrated with community evaluation tools, such as [DeepEval](https://docs.confident-ai.com/docs/getting-started)
which offers evaluators both for retrieval and generation.
- [DeepEval notebook](https://docs.llamaindex.ai/en/stable/examples/evaluation/Deepeval/)