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

### Goals & Target State
- **Comprehensive evaluation**
  - All relevant parts of the RAG application should be assessed - retrieval and generation.
- **Actionable insights**
  - Evaluation should provide actionable insights on weak areas, bottlenecks of the system
- **Efficiency**
  - Ensure evaluation is cost-effective and time-efficient, allowing for frequent evaluations
  - Potentially break down evaluation into tiers (quick & dirty vs long & clean)
- **Scalability**
  - Design the evaluation suite to accommodate changes in the system (e.g., different chunking strategies,
  retrieval methods) without excessive overhead.
- **Reproducibility and versioning**
  - Maintain versioned datasets and results to track progress over time.
- **Visibility and reporting**
  - Allow for an easy visual representation of the end to end results


#### Implementation options
Option 1. Custom evaluation class (requires more time)
Option 2. Evaluation library (start with this)

### Target state

1. [X] Generate questions, ground truth and contexts answers using `ragas` library
2. [X] Generate answers and store contexts using my own retriever
   - [X] Generate answers
   - [] Retrieve contexts
   - [] Make it easy to replace retrievers
3. [X] Upload datasets to Weave
   - Versioning and storage
3. [X] Run evaluation suite on the dataset
4. [X] Implement evaluation pipeline over a dataset
   - Retrieve dataset from Weave
5. [] Analyze the results and identify key areas for improvement
6. [] Costs calculation and visualization
   - Store costs of generating the dataset

### Logical View

**DataLoader class:**
- Centralizes all I/O operations
- Specifically, used to load documents for initial dataset generator
Attributes:
- filepath: str file to load from the raw directory
Methods:
- save/load json - saves or loads json files
- save/load dataset - saves or loads dataset from Weave

**DatasetGenerator class:**
- Used to generate a new dataset based on a set of documents
- Dataset generation is sequential, no support for parallel processing
Attributes
- n_questions: int - controls the amount of questions to generate for a given set of raw documents
- main_llm: str - main llm that generates answers and questions. Should it be the same as the retriever on not?
- critic_llm: str - critic llm that does what?
- embedding_model: str - embedding model that is used by dataset generator and evaluator

**Evaluator class:**
- Manages end-to-end evaluation on a given dataset
- Calculates the metrics and metadata
- Stores the metrics
Methods:
- evaluate_ragas - conducts ragas-based evaluation
- evaluate_custom - conducts own end to end evaluation

#### Process View
Dataset generation (one-time):
- User selects the document over which to create the dataset
- User optionally selects the number of questions to generate
- User optionally selects the main model, critic model, embedding model
- User runs a single method `create_new_dataset` that creates a dataset in the predetermined location and saves it

Run evaluation pipeline (one-time / regular):
- User selects the dataset
- User defines a set of metrics to calculate
- User runs the `evaluate` method which calculates a set of metrics and saves the results


#### Metrics

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
[Course Link](https://www.wandb.courses/courses/take/rag-in-production/lessons/55179976-evaluation-basics)

[MS Build Weave Demo](https://www.youtube.com/watch?v=v5Qm7-OimBs)

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
[Part 1](https://wandb.ai/wandbot/wandbot-eval/reports/How-to-Evaluate-an-LLM-Part-1-Building-an-Evaluation-Dataset-for-our-LLM-System--Vmlldzo1NTAwNTcy)
[Part 2](https://wandb.ai/wandbot/wandbot-eval/reports/How-to-Evaluate-an-LLM-Part-2-Manual-Evaluation-of-Wandbot-our-LLM-Powered-Docs-Assistant--Vmlldzo1NzU4NTM3)

Before doing any evals, they used 'rigorous eyeballing' based evaluation.

So to recap, how W&B built their eval set:
- used real data from users' interaction with their wandbot
- built a golden set of 132 questions
- generated answers to this questions using wandbot
- stored the retrieved context (chunks, with some metadata)
- used manual evaluation (annotation) to determine accuracy of the results
- categorized each response into - correct, incorrect, unsure
- This is essentially measuring E2E accuracy of the results
- Achieved E2E accuracy of 66%, using manual review

**End to end evaluation without ground truth:**
- Using a powerful LLM it's actually feasible to assess accuracy without ground truth:
  - Generate a list of questions (query)
  - Generate the response
  - Store retrieved chunks and metadata
  - Use LLM-as-a-judge to assess it

### LlamaIndex

Useful bits and bytes:
- Can be used to generate questions for the [evaluation dataset](https://docs.llamaindex.
  ai/en/stable/module_guides/evaluating/usage_pattern/). Supports Vertex AI, but doesn't support Gemini AI Studio.
  Supports OpenRouter.
- Integrated with community evaluation tools, such as [DeepEval](https://docs.confident-ai.com/docs/getting-started)
which offers evaluators both for retrieval and generation.
- [DeepEval notebook](https://docs.llamaindex.ai/en/stable/examples/evaluation/Deepeval/)