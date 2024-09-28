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
- end-to-end performance (i.e. how good does the overal system perform?)
- retrieval performance (i.e. how relevant are retrieved results?)

### Approaches

#### Anthropic Cookbook
[URL](https://github.com/anthropics/anthropic-cookbook/blob/main/skills/retrieval_augmented_generation/guide.ipynb)

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
