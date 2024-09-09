Markdown content for item 0

 [Skip to content](https://docs.llamaindex.ai/en/stable/api_reference/embeddings/adapter/#llama_index.embeddings.adapter.LinearAdapterEmbeddingModel)

# Adapter

## LinearAdapterEmbeddingModel`module-attribute`[\#](https://docs.llamaindex.ai/en/stable/api_reference/embeddings/adapter/\#llama_index.embeddings.adapter.LinearAdapterEmbeddingModel "Permanent link")

```
LinearAdapterEmbeddingModel = AdapterEmbeddingModel

```

## AdapterEmbeddingModel [\#](https://docs.llamaindex.ai/en/stable/api_reference/embeddings/adapter/\#llama_index.embeddings.adapter.AdapterEmbeddingModel "Permanent link")

Bases: `BaseEmbedding`

Adapter for any embedding model.

This is a wrapper around any embedding model that adds an adapter layer on top of it.
This is useful for finetuning an embedding model on a downstream task.
The embedding model can be any model - it does not need to expose gradients.

**Parameters:**

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `base_embed_model` | `BaseEmbedding` | Base embedding model. | _required_ |
| `adapter_path` | `str` | Path to adapter. | _required_ |
| `adapter_cls` | `Optional[Type[Any]]` | Adapter class. Defaults to None, in which case a linear adapter is used. | `None` |
| `transform_query` | `bool` | Whether to transform query embeddings. Defaults to True. | `True` |
| `device` | `Optional[str]` | Device to use. Defaults to None. | `None` |
| `embed_batch_size` | `int` | Batch size for embedding. Defaults to 10. | `DEFAULT_EMBED_BATCH_SIZE` |
| `callback_manager` | `Optional[CallbackManager]` | Callback manager. Defaults to None. | `None` |

Source code in `llama-index-integrations/embeddings/llama-index-embeddings-adapter/llama_index/embeddings/adapter/base.py`

|     |     |
| --- | --- |
| ```<br> 15<br> 16<br> 17<br> 18<br> 19<br> 20<br> 21<br> 22<br> 23<br> 24<br> 25<br> 26<br> 27<br> 28<br> 29<br> 30<br> 31<br> 32<br> 33<br> 34<br> 35<br> 36<br> 37<br> 38<br> 39<br> 40<br> 41<br> 42<br> 43<br> 44<br> 45<br> 46<br> 47<br> 48<br> 49<br> 50<br> 51<br> 52<br> 53<br> 54<br> 55<br> 56<br> 57<br> 58<br> 59<br> 60<br> 61<br> 62<br> 63<br> 64<br> 65<br> 66<br> 67<br> 68<br> 69<br> 70<br> 71<br> 72<br> 73<br> 74<br> 75<br> 76<br> 77<br> 78<br> 79<br> 80<br> 81<br> 82<br> 83<br> 84<br> 85<br> 86<br> 87<br> 88<br> 89<br> 90<br> 91<br> 92<br> 93<br> 94<br> 95<br> 96<br> 97<br> 98<br> 99<br>100<br>101<br>102<br>103<br>104<br>105<br>106<br>107<br>108<br>109<br>110<br>111<br>112<br>``` | ```<br>class AdapterEmbeddingModel(BaseEmbedding):<br>    """Adapter for any embedding model.<br>    This is a wrapper around any embedding model that adds an adapter layer \<br>        on top of it.<br>    This is useful for finetuning an embedding model on a downstream task.<br>    The embedding model can be any model - it does not need to expose gradients.<br>    Args:<br>        base_embed_model (BaseEmbedding): Base embedding model.<br>        adapter_path (str): Path to adapter.<br>        adapter_cls (Optional[Type[Any]]): Adapter class. Defaults to None, in which \<br>            case a linear adapter is used.<br>        transform_query (bool): Whether to transform query embeddings. Defaults to True.<br>        device (Optional[str]): Device to use. Defaults to None.<br>        embed_batch_size (int): Batch size for embedding. Defaults to 10.<br>        callback_manager (Optional[CallbackManager]): Callback manager. \<br>            Defaults to None.<br>    """<br>    _base_embed_model: BaseEmbedding = PrivateAttr()<br>    _adapter: Any = PrivateAttr()<br>    _transform_query: bool = PrivateAttr()<br>    _device: Optional[str] = PrivateAttr()<br>    _target_device: Any = PrivateAttr()<br>    def __init__(<br>        self,<br>        base_embed_model: BaseEmbedding,<br>        adapter_path: str,<br>        adapter_cls: Optional[Type[Any]] = None,<br>        transform_query: bool = True,<br>        device: Optional[str] = None,<br>        embed_batch_size: int = DEFAULT_EMBED_BATCH_SIZE,<br>        callback_manager: Optional[CallbackManager] = None,<br>    ) -> None:<br>        """Init params."""<br>        import torch<br>        from llama_index.embeddings.adapter.utils import BaseAdapter, LinearLayer<br>        super().__init__(<br>            embed_batch_size=embed_batch_size,<br>            callback_manager=callback_manager,<br>            model_name=f"Adapter for {base_embed_model.model_name}",<br>        )<br>        if device is None:<br>            device = infer_torch_device()<br>            logger.info(f"Use pytorch device: {device}")<br>        self._target_device = torch.device(device)<br>        self._base_embed_model = base_embed_model<br>        if adapter_cls is None:<br>            adapter_cls = LinearLayer<br>        else:<br>            adapter_cls = cast(Type[BaseAdapter], adapter_cls)<br>        adapter = adapter_cls.load(adapter_path)<br>        self._adapter = cast(BaseAdapter, adapter)<br>        self._adapter.to(self._target_device)<br>        self._transform_query = transform_query<br>    @classmethod<br>    def class_name(cls) -> str:<br>        return "AdapterEmbeddingModel"<br>    def _get_query_embedding(self, query: str) -> List[float]:<br>        """Get query embedding."""<br>        import torch<br>        query_embedding = self._base_embed_model._get_query_embedding(query)<br>        if self._transform_query:<br>            query_embedding_t = torch.tensor(query_embedding).to(self._target_device)<br>            query_embedding_t = self._adapter.forward(query_embedding_t)<br>            query_embedding = query_embedding_t.tolist()<br>        return query_embedding<br>    async def _aget_query_embedding(self, query: str) -> List[float]:<br>        """Get query embedding."""<br>        import torch<br>        query_embedding = await self._base_embed_model._aget_query_embedding(query)<br>        if self._transform_query:<br>            query_embedding_t = torch.tensor(query_embedding).to(self._target_device)<br>            query_embedding_t = self._adapter.forward(query_embedding_t)<br>            query_embedding = query_embedding_t.tolist()<br>        return query_embedding<br>    def _get_text_embedding(self, text: str) -> List[float]:<br>        return self._base_embed_model._get_text_embedding(text)<br>    async def _aget_text_embedding(self, text: str) -> List[float]:<br>        return await self._base_embed_model._aget_text_embedding(text)<br>``` |

Back to top

Hi, how can I help you?

🦙

----

Markdown content for item 1

 [Skip to content](https://docs.llamaindex.ai/en/stable/api_reference/embeddings/fastembed/#llama_index.embeddings.fastembed.FastEmbedEmbedding)

# Fastembed

## FastEmbedEmbedding [\#](https://docs.llamaindex.ai/en/stable/api_reference/embeddings/fastembed/\#llama_index.embeddings.fastembed.FastEmbedEmbedding "Permanent link")

Bases: `BaseEmbedding`

Qdrant FastEmbedding models.
FastEmbed is a lightweight, fast, Python library built for embedding generation.
See more documentation at:
\\* https://github.com/qdrant/fastembed/
\\* https://qdrant.github.io/fastembed/.

To use this class, you must install the `fastembed` Python package.

`pip install fastembed`
Example:
from llama\_index.embeddings.fastembed import FastEmbedEmbedding
fastembed = FastEmbedEmbedding()

Source code in `llama-index-integrations/embeddings/llama-index-embeddings-fastembed/llama_index/embeddings/fastembed/base.py`

|     |     |
| --- | --- |
| ```<br>10<br>11<br>12<br>13<br>14<br>15<br>16<br>17<br>18<br>19<br>20<br>21<br>22<br>23<br>24<br>25<br>26<br>27<br>28<br>29<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46<br>47<br>48<br>49<br>50<br>51<br>52<br>53<br>54<br>55<br>56<br>57<br>58<br>59<br>60<br>61<br>62<br>63<br>64<br>65<br>66<br>67<br>68<br>69<br>70<br>71<br>72<br>73<br>74<br>75<br>76<br>77<br>78<br>79<br>80<br>81<br>82<br>83<br>84<br>85<br>86<br>87<br>88<br>89<br>90<br>91<br>92<br>93<br>94<br>95<br>96<br>97<br>98<br>99<br>``` | ```<br>class FastEmbedEmbedding(BaseEmbedding):<br>    """<br>    Qdrant FastEmbedding models.<br>    FastEmbed is a lightweight, fast, Python library built for embedding generation.<br>    See more documentation at:<br>    * https://github.com/qdrant/fastembed/<br>    * https://qdrant.github.io/fastembed/.<br>    To use this class, you must install the `fastembed` Python package.<br>    `pip install fastembed`<br>    Example:<br>        from llama_index.embeddings.fastembed import FastEmbedEmbedding<br>        fastembed = FastEmbedEmbedding()<br>    """<br>    model_name: str = Field(<br>        "BAAI/bge-small-en-v1.5",<br>        description="Name of the FastEmbedding model to use.\n"<br>        "Defaults to 'BAAI/bge-small-en-v1.5'.\n"<br>        "Find the list of supported models at "<br>        "https://qdrant.github.io/fastembed/examples/Supported_Models/",<br>    )<br>    max_length: int = Field(<br>        512,<br>        description="The maximum number of tokens. Defaults to 512.\n"<br>        "Unknown behavior for values > 512.",<br>    )<br>    cache_dir: Optional[str] = Field(<br>        None,<br>        description="The path to the cache directory.\n"<br>        "Defaults to `local_cache` in the parent directory",<br>    )<br>    threads: Optional[int] = Field(<br>        None,<br>        description="The number of threads single onnxruntime session can use.\n"<br>        "Defaults to None",<br>    )<br>    doc_embed_type: Literal["default", "passage"] = Field(<br>        "default",<br>        description="Type of embedding method to use for documents.\n"<br>        "Available options are 'default' and 'passage'.",<br>    )<br>    _model: Any = PrivateAttr()<br>    @classmethod<br>    def class_name(self) -> str:<br>        return "FastEmbedEmbedding"<br>    def __init__(<br>        self,<br>        model_name: Optional[str] = "BAAI/bge-small-en-v1.5",<br>        max_length: Optional[int] = 512,<br>        cache_dir: Optional[str] = None,<br>        threads: Optional[int] = None,<br>        doc_embed_type: Literal["default", "passage"] = "default",<br>    ):<br>        super().__init__(<br>            model_name=model_name,<br>            max_length=max_length,<br>            threads=threads,<br>            doc_embed_type=doc_embed_type,<br>        )<br>        self._model = TextEmbedding(<br>            model_name=model_name,<br>            max_length=max_length,<br>            cache_dir=cache_dir,<br>            threads=threads,<br>        )<br>    def _get_text_embedding(self, text: str) -> List[float]:<br>        embeddings: List[np.ndarray]<br>        if self.doc_embed_type == "passage":<br>            embeddings = list(self._model.passage_embed(text))<br>        else:<br>            embeddings = list(self._model.embed(text))<br>        return embeddings[0].tolist()<br>    def _get_query_embedding(self, query: str) -> List[float]:<br>        query_embeddings: np.ndarray = next(self._model.query_embed(query))<br>        return query_embeddings.tolist()<br>    async def _aget_query_embedding(self, query: str) -> List[float]:<br>        return self._get_query_embedding(query)<br>``` |

Back to top

Hi, how can I help you?

🦙

----

Markdown content for item 2

 # Agentops

Back to top

----

