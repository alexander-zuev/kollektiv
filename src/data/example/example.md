# Content for item 0

```markdown


# Core Agent Classes [\#](\#core-agent-classes "Permanent link")

## Base Types [\#](\#base-types "Permanent link")

Base agent types.

### BaseAgent [\#](\#llama_index.core.agent.types.BaseAgent "Permanent link")

Bases: `BaseChatEngine`, `BaseQueryEngine`

Base Agent.

Source code in `llama-index-core/llama_index/core/base/agent/types.py`

|     |     |
| --- | --- |
| ```<br>30<br>31<br>32<br>33<br>34<br>35<br>36<br>37<br>38<br>39<br>40<br>41<br>42<br>43<br>44<br>45<br>46<br>47<br>48<br>49<br>50<br>51<br>52<br>53<br>54<br>55<br>56<br>57<br>58<br>59<br>60<br>61<br>62<br>63<br>64<br>65<br>66<br>67<br>68<br>69<br>70<br>71<br>72<br>73<br>74<br>75<br>``` | ```<br>class BaseAgent(BaseChatEngine, BaseQueryEngine):<br>    """Base Agent."""<br>    def _get_prompts(self) -> PromptDictType:<br>        """Get prompts."""<br>        # TODO: the ReAct agent does not explicitly specify prompts, would need a<br>        # refactor to expose those prompts<br>        return {}<br>    def _get_prompt_modules(self) -> PromptMixinType:<br>        """Get prompt modules."""<br>        return {}<br>    def _update_prompts(self, prompts: PromptDictType) -> None:<br>        """Update prompts."""<br>    # ===== Query Engine Interface =====<br>    @trace_method("query")<br>    def _query(self, query_bundle: QueryBundle) -> RESPONSE_TYPE:<br>        agent_response = self.chat(<br>            query_bundle.query_str,<br>            chat_history=[],<br>        )<br>        return Response(<br>            response=str(agent_response), source_nodes=agent_response.source_nodes<br>        )<br>    @trace_method("query")<br>    async def _aquery(self, query_bundle: QueryBundle) -> RESPONSE_TYPE:<br>        agent_response = await self.achat(<br>            query_bundle.query_str,<br>            chat_history=[],<br>        )<br>        return Response(<br>            response=str(agent_response), source_nodes=agent_response.source_nodes<br>        )<br>    def stream_chat(<br>        self, message: str, chat_history: Optional[List[ChatMessage]] = None<br>    ) -> StreamingAgentChatResponse:<br>        raise NotImplementedError("stream_chat not implemented")<br>    async def astream_chat(<br>        self, message: str, chat_history: Optional[List[ChatMessage]] = None<br>    ) -> StreamingAgentChatResponse:<br>        raise NotImplementedError("astream_chat not implemented")<br>``` |

### BaseAgentWorker [\#](\#llama_index.core.agent.types.BaseAgentWorker "Permanent link")

Bases: `PromptMixin`, `DispatcherSpanMixin`

Base agent worker.

Source code in `llama-index-core/llama_index/core/base/agent/types.py`

|     |     |
| --- | --- |
| ```<br>192<br>193<br>194<br>195<br>196<br>197<br>198<br>199<br>200<br>201<br>202<br>203<br>204<br>205<br>206<br>207<br>208<br>209<br>210<br>211<br>212<br>213<br>214<br>215<br>216<br>217<br>218<br>219<br>220<br>221<br>222<br>223<br>224<br>225<br>226<br>227<br>228<br>229<br>230<br>231<br>232<br>233<br>234<br>235<br>236<br>237<br>238<br>239<br>240<br>241<br>242<br>243<br>244<br>245<br>246<br>247<br>248<br>``` | ```<br>class BaseAgentWorker(PromptMixin, DispatcherSpanMixin):<br>    """Base agent worker."""<br>    def _get_prompts(self) -> PromptDictType:<br>        """Get prompts."""<br>        # TODO: the ReAct agent does not explicitly specify prompts, would need a<br>        # refactor to expose those prompts<br>        return {}<br>    def _get_prompt_modules(self) -> PromptMixinType:<br>        """Get prompt modules."""<br>        return {}<br>    def _update_prompts(self, prompts: PromptDictType) -> None:<br>        """Update prompts."""<br>    @abstractmethod<br>    def initialize_step(self, task: Task, **kwargs: Any) -> TaskStep:<br>        """Initialize step from task."""<br>    @abstractmethod<br>    def run_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:<br>        """Run step."""<br>    @abstractmethod<br>    async def arun_step(<br>        self, step: TaskStep, task: Task, **kwargs: Any<br>    ) -> TaskStepOutput:<br>        """Run step (async)."""<br>        raise NotImplementedError<br>    @abstractmethod<br>    def stream_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:<br>        """Run step (stream)."""<br>        # TODO: figure out if we need a different type for TaskStepOutput<br>        raise NotImplementedError<br>    @abstractmethod<br>    async def astream_step(<br>        self, step: TaskStep, task: Task, **kwargs: Any<br>    ) -> TaskStepOutput:<br>        """Run step (async stream)."""<br>        raise NotImplementedError<br>    @abstractmethod<br>    def finalize_task(self, task: Task, **kwargs: Any) -> None:<br>        """Finalize task, after all the steps are completed."""<br>    def set_callback_manager(self, callback_manager: CallbackManager) -> None:<br>        """Set callback manager."""<br>        # TODO: make this abstractmethod (right now will break some agent impls)<br>    def as_agent(self, **kwargs: Any) -> "AgentRunner":<br>        """Return as an agent runner."""<br>        from llama_index.core.agent.runner.base import AgentRunner<br>        return AgentRunner(self, **kwargs)<br>``` |

#### initialize\_step`abstractmethod`[\#](\#llama_index.core.agent.types.BaseAgentWorker.initialize_step "Permanent link")

```
initialize_step(task: Task, **kwargs: Any) -> TaskStep

```

Initialize step from task.

Source code in `llama-index-core/llama_index/core/base/agent/types.py`

|     |     |
| --- | --- |
| ```<br>208<br>209<br>210<br>``` | ```<br>@abstractmethod<br>def initialize_step(self, task: Task, **kwargs: Any) -> TaskStep:<br>    """Initialize step from task."""<br>``` |

#### run\_step`abstractmethod`[\#](\#llama_index.core.agent.types.BaseAgentWorker.run_step "Permanent link")

```
run_step(step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput

```

Run step.

Source code in `llama-index-core/llama_index/core/base/agent/types.py`

|     |     |
| --- | --- |
| ```<br>212<br>213<br>214<br>``` | ```<br>@abstractmethod<br>def run_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:<br>    """Run step."""<br>``` |

#### arun\_step`abstractmethod``async`[\#](\#llama_index.core.agent.types.BaseAgentWorker.arun_step "Permanent link")

```
arun_step(step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput

```

Run step (async).

Source code in `llama-index-core/llama_index/core/base/agent/types.py`

|     |     |
| --- | --- |
| ```<br>216<br>217<br>218<br>219<br>220<br>221<br>``` | ```<br>@abstractmethod<br>async def arun_step(<br>    self, step: TaskStep, task: Task, **kwargs: Any<br>) -> TaskStepOutput:<br>    """Run step (async)."""<br>    raise NotImplementedError<br>``` |

#### stream\_step`abstractmethod`[\#](\#llama_index.core.agent.types.BaseAgentWorker.stream_step "Permanent link")

```
stream_step(step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput

```

Run step (stream).

Source code in `llama-index-core/llama_index/core/base/agent/types.py`

|     |     |
| --- | --- |
| ```<br>223<br>224<br>225<br>226<br>227<br>``` | ```<br>@abstractmethod<br>def stream_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:<br>    """Run step (stream)."""<br>    # TODO: figure out if we need a different type for TaskStepOutput<br>    raise NotImplementedError<br>``` |

#### astream\_step`abstractmethod``async`[\#](\#llama_index.core.agent.types.BaseAgentWorker.astream_step "Permanent link")

```
astream_step(step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput

```

Run step (async stream).

Source code in `llama-index-core/llama_index/core/base/agent/types.py`

|     |     |
| --- | --- |
| ```<br>229<br>230<br>231<br>232<br>233<br>234<br>``` | ```<br>@abstractmethod<br>async def astream_step(<br>    self, step: TaskStep, task: Task, **kwargs: Any<br>) -> TaskStepOutput:<br>    """Run step (async stream)."""<br>    raise NotImplementedError<br>``` |

#### finalize\_task`abstractmethod`[\#](\#llama_index.core.agent.types.BaseAgentWorker.finalize_task "Permanent link")

```
finalize_task(task: Task, **kwargs: Any) -> None

```

Finalize task, after all the steps are completed.

Source code in `llama-index-core/llama_index/core/base/agent/types.py`

|     |     |
| --- | --- |
| ```<br>236<br>237<br>238<br>``` | ```<br>@abstractmethod<br>def finalize_task(self, task: Task, **kwargs: Any) -> None:<br>    """Finalize task, after all the steps are completed."""<br>``` |

#### set\_callback\_manager [\#](\#llama_index.core.agent.types.BaseAgentWorker.set_callback_manager "Permanent link")

```
set_callback_manager(callback_manager: CallbackManager) -> None

```

Set callback manager.

Source code in `llama-index-core/llama_index/core/base/agent/types.py`

|     |     |
| --- | --- |
| ```<br>240<br>241<br>``` | ```<br>def set_callback_manager(self, callback_manager: CallbackManager) -> None:<br>    """Set callback manager."""<br>``` |

#### as\_agent [\#](\#llama_index.core.agent.types.BaseAgentWorker.as_agent "Permanent link")

```
as_agent(**kwargs: Any) -> AgentRunner

```

Return as an agent runner.

Source code in `llama-index-core/llama_index/core/base/agent/types.py`

|     |     |
| --- | --- |
| ```<br>244<br>245<br>246<br>247<br>248<br>``` | ```<br>def as_agent(self, **kwargs: Any) -> "AgentRunner":<br>    """Return as an agent runner."""<br>    from llama_index.core.agent.runner.base import AgentRunner<br>    return AgentRunner(self, **kwargs)<br>``` |

### Task [\#](\#llama_index.core.agent.types.Task "Permanent link")

Bases: `BaseModel`

Agent Task.

Represents a "run" of an agent given a user input.

Source code in `llama-index-core/llama_index/core/base/agent/types.py`

|     |     |
| --- | --- |
| ```<br>156<br>157<br>158<br>159<br>160<br>161<br>162<br>163<br>164<br>165<br>166<br>167<br>168<br>169<br>170<br>171<br>172<br>173<br>174<br>175<br>176<br>177<br>178<br>179<br>180<br>181<br>182<br>183<br>184<br>185<br>186<br>187<br>188<br>189<br>``` | ```<br>class Task(BaseModel):<br>    """Agent Task.<br>    Represents a "run" of an agent given a user input.<br>    """<br>    model_config = ConfigDict(arbitrary_types_allowed=True)<br>    task_id: str = Field(<br>        default_factory=lambda: str(uuid.uuid4()), description="Task ID"<br>    )<br>    input: str = Field(..., description="User input")<br>    # NOTE: this is state that may be modified throughout the course of execution of the task<br>    memory: SerializeAsAny[BaseMemory] = Field(<br>        ...,<br>        description=(<br>            "Conversational Memory. Maintains state before execution of this task."<br>        ),<br>    )<br>    callback_manager: CallbackManager = Field(<br>        default_factory=lambda: CallbackManager([]),<br>        exclude=True,<br>        description="Callback manager for the task.",<br>    )<br>    extra_state: Dict[str, Any] = Field(<br>        default_factory=dict,<br>        description=(<br>            "Additional user-specified state for a given task. "<br>            "Can be modified throughout the execution of a task."<br>        ),<br>    )<br>``` |

### TaskStep [\#](\#llama_index.core.agent.types.TaskStep "Permanent link")

Bases: `BaseModel`

Agent task step.

Represents a single input step within the execution run ("Task") of an agent
given a user input.

The output is returned as a `TaskStepOutput`.

Source code in `llama-index-core/llama_index/core/base/agent/types.py`

|     |     |
| --- | --- |
| ```<br> 78<br> 79<br> 80<br> 81<br> 82<br> 83<br> 84<br> 85<br> 86<br> 87<br> 88<br> 89<br> 90<br> 91<br> 92<br> 93<br> 94<br> 95<br> 96<br> 97<br> 98<br> 99<br>100<br>101<br>102<br>103<br>104<br>105<br>106<br>107<br>108<br>109<br>110<br>111<br>112<br>113<br>114<br>115<br>116<br>117<br>118<br>119<br>120<br>121<br>122<br>123<br>124<br>125<br>126<br>127<br>128<br>129<br>130<br>131<br>132<br>133<br>134<br>135<br>136<br>137<br>138<br>139<br>140<br>``` | ```<br>class TaskStep(BaseModel):<br>    """Agent task step.<br>    Represents a single input step within the execution run ("Task") of an agent<br>    given a user input.<br>    The output is returned as a `TaskStepOutput`.<br>    """<br>    task_id: str = Field(..., description="Task ID")<br>    step_id: str = Field(..., description="Step ID")<br>    input: Optional[str] = Field(default=None, description="User input")<br>    # memory: BaseMemory = Field(<br>    #     ..., description="Conversational Memory"<br>    # )<br>    step_state: Dict[str, Any] = Field(<br>        default_factory=dict, description="Additional state for a given step."<br>    )<br>    # NOTE: the state below may change throughout the course of execution<br>    # this tracks the relationships to other steps<br>    next_steps: Dict[str, "TaskStep"] = Field(<br>        default_factory=dict, description="Next steps to be executed."<br>    )<br>    prev_steps: Dict[str, "TaskStep"] = Field(<br>        default_factory=dict,<br>        description="Previous steps that were dependencies for this step.",<br>    )<br>    is_ready: bool = Field(<br>        default=True, description="Is this step ready to be executed?"<br>    )<br>    def get_next_step(<br>        self,<br>        step_id: str,<br>        input: Optional[str] = None,<br>        step_state: Optional[Dict[str, Any]] = None,<br>    ) -> "TaskStep":<br>        """Convenience function to get next step.<br>        Preserve task_id, memory, step_state.<br>        """<br>        return TaskStep(<br>            task_id=self.task_id,<br>            step_id=step_id,<br>            input=input,<br>            # memory=self.memory,<br>            step_state=step_state or self.step_state,<br>        )<br>    def link_step(<br>        self,<br>        next_step: "TaskStep",<br>    ) -> None:<br>        """Link to next step.<br>        Add link from this step to next, and from next step to current.<br>        """<br>        self.next_steps[next_step.step_id] = next_step<br>        next_step.prev_steps[self.step_id] = self<br>``` |

#### get\_next\_step [\#](\#llama_index.core.agent.types.TaskStep.get_next_step "Permanent link")

```
get_next_step(step_id: str, input: Optional[str] = None, step_state: Optional[Dict[str, Any]] = None) -> TaskStep

```

Convenience function to get next step.

Preserve task\_id, memory, step\_state.

Source code in `llama-index-core/llama_index/core/base/agent/types.py`

|     |     |
| --- | --- |
| ```<br>111<br>112<br>113<br>114<br>115<br>116<br>117<br>118<br>119<br>120<br>121<br>122<br>123<br>124<br>125<br>126<br>127<br>128<br>``` | ```<br>def get_next_step(<br>    self,<br>    step_id: str,<br>    input: Optional[str] = None,<br>    step_state: Optional[Dict[str, Any]] = None,<br>) -> "TaskStep":<br>    """Convenience function to get next step.<br>    Preserve task_id, memory, step_state.<br>    """<br>    return TaskStep(<br>        task_id=self.task_id,<br>        step_id=step_id,<br>        input=input,<br>        # memory=self.memory,<br>        step_state=step_state or self.step_state,<br>    )<br>``` |

#### link\_step [\#](\#llama_index.core.agent.types.TaskStep.link_step "Permanent link")

```
link_step(next_step: TaskStep) -> None

```

Link to next step.

Add link from this step to next, and from next step to current.

Source code in `llama-index-core/llama_index/core/base/agent/types.py`

|     |     |
| --- | --- |
| ```<br>130<br>131<br>132<br>133<br>134<br>135<br>136<br>137<br>138<br>139<br>140<br>``` | ```<br>def link_step(<br>    self,<br>    next_step: "TaskStep",<br>) -> None:<br>    """Link to next step.<br>    Add link from this step to next, and from next step to current.<br>    """<br>    self.next_steps[next_step.step_id] = next_step<br>    next_step.prev_steps[self.step_id] = self<br>``` |

### TaskStepOutput [\#](\#llama_index.core.agent.types.TaskStepOutput "Permanent link")

Bases: `BaseModel`

Agent task step output.

Source code in `llama-index-core/llama_index/core/base/agent/types.py`

|     |     |
| --- | --- |
| ```<br>143<br>144<br>145<br>146<br>147<br>148<br>149<br>150<br>151<br>152<br>153<br>``` | ```<br>class TaskStepOutput(BaseModel):<br>    """Agent task step output."""<br>    output: Any = Field(..., description="Task step output")<br>    task_step: TaskStep = Field(..., description="Task step input")<br>    next_steps: List[TaskStep] = Field(..., description="Next steps to be executed.")<br>    is_last: bool = Field(default=False, description="Is this the last step?")<br>    def __str__(self) -> str:<br>        """String representation."""<br>        return str(self.output)<br>``` |

## Runners [\#](\#runners "Permanent link")

### AgentRunner [\#](\#llama_index.core.agent.AgentRunner "Permanent link")

Bases: `BaseAgentRunner`

Agent runner.

Top-level agent orchestrator that can create tasks, run each step in a task,
or run a task e2e. Stores state and keeps track of tasks.

**Parameters:**

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `agent_worker` | `BaseAgentWorker` | step executor | _required_ |
| `chat_history` | `Optional[List[ChatMessage]]` | chat history. Defaults to None. | `None` |
| `state` | `Optional[AgentState]` | agent state. Defaults to None. | `None` |
| `memory` | `Optional[BaseMemory]` | memory. Defaults to None. | `None` |
| `llm` | `Optional[LLM]` | LLM. Defaults to None. | `None` |
| `callback_manager` | `Optional[CallbackManager]` | callback manager. Defaults to None. | `None` |
| `init_task_state_kwargs` | `Optional[dict]` | init task state kwargs. Defaults to None. | `None` |

Source code in `llama-index-core/llama_index/core/agent/runner/base.py`

|     |     |
| --- | --- |
| ```<br>200<br>201<br>202<br>203<br>204<br>205<br>206<br>207<br>208<br>209<br>210<br>211<br>212<br>213<br>214<br>215<br>216<br>217<br>218<br>219<br>220<br>221<br>222<br>223<br>224<br>225<br>226<br>227<br>228<br>229<br>230<br>231<br>232<br>233<br>234<br>235<br>236<br>237<br>238<br>239<br>240<br>241<br>242<br>243<br>244<br>245<br>246<br>247<br>248<br>249<br>250<br>251<br>252<br>253<br>254<br>255<br>256<br>257<br>258<br>259<br>260<br>261<br>262<br>263<br>264<br>265<br>266<br>267<br>268<br>269<br>270<br>271<br>272<br>273<br>274<br>275<br>276<br>277<br>278<br>279<br>280<br>281<br>282<br>283<br>284<br>285<br>286<br>287<br>288<br>289<br>290<br>291<br>292<br>293<br>294<br>295<br>296<br>297<br>298<br>299<br>300<br>301<br>302<br>303<br>304<br>305<br>306<br>307<br>308<br>309<br>310<br>311<br>312<br>313<br>314<br>315<br>316<br>317<br>318<br>319<br>320<br>321<br>322<br>323<br>324<br>325<br>326<br>327<br>328<br>329<br>330<br>331<br>332<br>333<br>334<br>335<br>336<br>337<br>338<br>339<br>340<br>341<br>342<br>343<br>344<br>345<br>346<br>347<br>348<br>349<br>350<br>351<br>352<br>353<br>354<br>355<br>356<br>357<br>358<br>359<br>360<br>361<br>362<br>363<br>364<br>365<br>366<br>367<br>368<br>369<br>370<br>371<br>372<br>373<br>374<br>375<br>376<br>377<br>378<br>379<br>380<br>381<br>382<br>383<br>384<br>385<br>386<br>387<br>388<br>389<br>390<br>391<br>392<br>393<br>394<br>395<br>396<br>397<br>398<br>399<br>400<br>401<br>402<br>403<br>404<br>405<br>406<br>407<br>408<br>409<br>410<br>411<br>412<br>413<br>414<br>415<br>416<br>417<br>418<br>419<br>420<br>421<br>422<br>423<br>424<br>425<br>426<br>427<br>428<br>429<br>430<br>431<br>432<br>433<br>434<br>435<br>436<br>437<br>438<br>439<br>440<br>441<br>442<br>443<br>444<br>445<br>446<br>447<br>448<br>449<br>450<br>451<br>452<br>453<br>454<br>455<br>456<br>457<br>458<br>459<br>460<br>461<br>462<br>463<br>464<br>465<br>466<br>467<br>468<br>469<br>470<br>471<br>472<br>473<br>474<br>475<br>476<br>477<br>478<br>479<br>480<br>481<br>482<br>483<br>484<br>485<br>486<br>487<br>488<br>489<br>490<br>491<br>492<br>493<br>494<br>495<br>496<br>497<br>498<br>499<br>500<br>501<br>502<br>503<br>504<br>505<br>506<br>507<br>508<br>509<br>510<br>511<br>512<br>513<br>514<br>515<br>516<br>517<br>518<br>519<br>520<br>521<br>522<br>523<br>524<br>525<br>526<br>527<br>528<br>529<br>530<br>531<br>532<br>533<br>534<br>535<br>536<br>537<br>538<br>539<br>540<br>541<br>542<br>543<br>544<br>545<br>546<br>547<br>548<br>549<br>550<br>551<br>552<br>553<br>554<br>555<br>556<br>557<br>558<br>559<br>560<br>561<br>562<br>563<br>564<br>565<br>566<br>567<br>568<br>569<br>570<br>571<br>572<br>573<br>574<br>575<br>576<br>577<br>578<br>579<br>580<br>581<br>582<br>583<br>584<br>585<br>586<br>587<br>588<br>589<br>590<br>591<br>592<br>593<br>594<br>595<br>596<br>597<br>598<br>599<br>600<br>601<br>602<br>603<br>604<br>605<br>606<br>607<br>608<br>609<br>610<br>611<br>612<br>613<br>614<br>615<br>616<br>617<br>618<br>619<br>620<br>621<br>622<br>623<br>624<br>625<br>626<br>627<br>628<br>629<br>630<br>631<br>632<br>633<br>634<br>635<br>636<br>637<br>638<br>639<br>640<br>641<br>642<br>643<br>644<br>645<br>646<br>647<br>648<br>649<br>650<br>651<br>652<br>653<br>654<br>655<br>656<br>657<br>658<br>659<br>660<br>661<br>662<br>663<br>664<br>665<br>666<br>667<br>668<br>669<br>670<br>671<br>672<br>673<br>674<br>675<br>676<br>677<br>678<br>679<br>680<br>681<br>682<br>683<br>684<br>685<br>686<br>687<br>688<br>689<br>690<br>691<br>692<br>693<br>694<br>695<br>696<br>697<br>698<br>699<br>700<br>701<br>702<br>703<br>704<br>705<br>706<br>707<br>708<br>709<br>710<br>711<br>712<br>713<br>714<br>715<br>716<br>717<br>718<br>719<br>720<br>721<br>722<br>723<br>724<br>725<br>726<br>727<br>728<br>729<br>730<br>731<br>732<br>733<br>734<br>735<br>736<br>``` | ```<br>class AgentRunner(BaseAgentRunner):<br>    """Agent runner.<br>    Top-level agent orchestrator that can create tasks, run each step in a task,<br>    or run a task e2e. Stores state and keeps track of tasks.<br>    Args:<br>        agent_worker (BaseAgentWorker): step executor<br>        chat_history (Optional[List[ChatMessage]], optional): chat history. Defaults to None.<br>        state (Optional[AgentState], optional): agent state. Defaults to None.<br>        memory (Optional[BaseMemory], optional): memory. Defaults to None.<br>        llm (Optional[LLM], optional): LLM. Defaults to None.<br>        callback_manager (Optional[CallbackManager], optional): callback manager. Defaults to None.<br>        init_task_state_kwargs (Optional[dict], optional): init task state kwargs. Defaults to None.<br>    """<br>    # # TODO: implement this in Pydantic<br>    def __init__(<br>        self,<br>        agent_worker: BaseAgentWorker,<br>        chat_history: Optional[List[ChatMessage]] = None,<br>        state: Optional[AgentState] = None,<br>        memory: Optional[BaseMemory] = None,<br>        llm: Optional[LLM] = None,<br>        callback_manager: Optional[CallbackManager] = None,<br>        init_task_state_kwargs: Optional[dict] = None,<br>        delete_task_on_finish: bool = False,<br>        default_tool_choice: str = "auto",<br>        verbose: bool = False,<br>    ) -> None:<br>        """Initialize."""<br>        self.agent_worker = agent_worker<br>        self.state = state or AgentState()<br>        self.memory = memory or ChatMemoryBuffer.from_defaults(chat_history, llm=llm)<br>        # get and set callback manager<br>        if callback_manager is not None:<br>            self.agent_worker.set_callback_manager(callback_manager)<br>            self.callback_manager = callback_manager<br>        else:<br>            # TODO: This is *temporary*<br>            # Stopgap before having a callback on the BaseAgentWorker interface.<br>            # Doing that requires a bit more refactoring to make sure existing code<br>            # doesn't break.<br>            if hasattr(self.agent_worker, "callback_manager"):<br>                self.callback_manager = (<br>                    self.agent_worker.callback_manager or CallbackManager()<br>                )<br>            else:<br>                self.callback_manager = CallbackManager()<br>        self.init_task_state_kwargs = init_task_state_kwargs or {}<br>        self.delete_task_on_finish = delete_task_on_finish<br>        self.default_tool_choice = default_tool_choice<br>        self.verbose = verbose<br>    @staticmethod<br>    def from_llm(<br>        tools: Optional[List[BaseTool]] = None,<br>        llm: Optional[LLM] = None,<br>        **kwargs: Any,<br>    ) -> "AgentRunner":<br>        from llama_index.core.agent import ReActAgent<br>        if os.getenv("IS_TESTING"):<br>            return ReActAgent.from_tools(<br>                tools=tools,<br>                llm=llm,<br>                **kwargs,<br>            )<br>        try:<br>            from llama_index.llms.openai import OpenAI  # pants: no-infer-dep<br>            from llama_index.llms.openai.utils import (<br>                is_function_calling_model,<br>            )  # pants: no-infer-dep<br>        except ImportError:<br>            raise ImportError(<br>                "`llama-index-llms-openai` package not found. Please "<br>                "install by running `pip install llama-index-llms-openai`."<br>            )<br>        if isinstance(llm, OpenAI) and is_function_calling_model(llm.model):<br>            from llama_index.agent.openai import OpenAIAgent  # pants: no-infer-dep<br>            return OpenAIAgent.from_tools(<br>                tools=tools,<br>                llm=llm,<br>                **kwargs,<br>            )<br>        else:<br>            return ReActAgent.from_tools(<br>                tools=tools,<br>                llm=llm,<br>                **kwargs,<br>            )<br>    @property<br>    def chat_history(self) -> List[ChatMessage]:<br>        return self.memory.get_all()<br>    def reset(self) -> None:<br>        self.memory.reset()<br>        self.state.reset()<br>    def create_task(self, input: str, **kwargs: Any) -> Task:<br>        """Create task."""<br>        if not self.init_task_state_kwargs:<br>            extra_state = kwargs.pop("extra_state", {})<br>        else:<br>            if "extra_state" in kwargs:<br>                raise ValueError(<br>                    "Cannot specify both `extra_state` and `init_task_state_kwargs`"<br>                )<br>            else:<br>                extra_state = self.init_task_state_kwargs<br>        callback_manager = kwargs.pop("callback_manager", self.callback_manager)<br>        task = Task(<br>            input=input,<br>            memory=self.memory,<br>            extra_state=extra_state,<br>            callback_manager=callback_manager,<br>            **kwargs,<br>        )<br>        # # put input into memory<br>        # self.memory.put(ChatMessage(content=input, role=MessageRole.USER))<br>        # get initial step from task, and put it in the step queue<br>        initial_step = self.agent_worker.initialize_step(task)<br>        task_state = TaskState(<br>            task=task,<br>            step_queue=deque([initial_step]),<br>        )<br>        # add it to state<br>        self.state.task_dict[task.task_id] = task_state<br>        return task<br>    def delete_task(<br>        self,<br>        task_id: str,<br>    ) -> None:<br>        """Delete task.<br>        NOTE: this will not delete any previous executions from memory.<br>        """<br>        self.state.task_dict.pop(task_id)<br>    def list_tasks(self, **kwargs: Any) -> List[Task]:<br>        """List tasks."""<br>        return [task_state.task for task_state in self.state.task_dict.values()]<br>    def get_task(self, task_id: str, **kwargs: Any) -> Task:<br>        """Get task."""<br>        return self.state.get_task(task_id)<br>    def get_upcoming_steps(self, task_id: str, **kwargs: Any) -> List[TaskStep]:<br>        """Get upcoming steps."""<br>        return list(self.state.get_step_queue(task_id))<br>    def get_completed_steps(self, task_id: str, **kwargs: Any) -> List[TaskStepOutput]:<br>        """Get completed steps."""<br>        return self.state.get_completed_steps(task_id)<br>    def get_task_output(self, task_id: str, **kwargs: Any) -> TaskStepOutput:<br>        """Get task output."""<br>        completed_steps = self.get_completed_steps(task_id)<br>        if len(completed_steps) == 0:<br>            raise ValueError(f"No completed steps for task_id: {task_id}")<br>        return completed_steps[-1]<br>    def get_completed_tasks(self, **kwargs: Any) -> List[Task]:<br>        """Get completed tasks."""<br>        task_states = list(self.state.task_dict.values())<br>        completed_tasks = []<br>        for task_state in task_states:<br>            completed_steps = self.get_completed_steps(task_state.task.task_id)<br>            if len(completed_steps) > 0 and completed_steps[-1].is_last:<br>                completed_tasks.append(task_state.task)<br>        return completed_tasks<br>    @dispatcher.span<br>    def _run_step(<br>        self,<br>        task_id: str,<br>        step: Optional[TaskStep] = None,<br>        input: Optional[str] = None,<br>        mode: ChatResponseMode = ChatResponseMode.WAIT,<br>        **kwargs: Any,<br>    ) -> TaskStepOutput:<br>        """Execute step."""<br>        task = self.state.get_task(task_id)<br>        step_queue = self.state.get_step_queue(task_id)<br>        step = step or step_queue.popleft()<br>        if input is not None:<br>            step.input = input<br>        dispatcher.event(<br>            AgentRunStepStartEvent(task_id=task_id, step=step, input=input)<br>        )<br>        if self.verbose:<br>            print(f"> Running step {step.step_id}. Step input: {step.input}")<br>        # TODO: figure out if you can dynamically swap in different step executors<br>        # not clear when you would do that by theoretically possible<br>        if mode == ChatResponseMode.WAIT:<br>            cur_step_output = self.agent_worker.run_step(step, task, **kwargs)<br>        elif mode == ChatResponseMode.STREAM:<br>            cur_step_output = self.agent_worker.stream_step(step, task, **kwargs)<br>        else:<br>            raise ValueError(f"Invalid mode: {mode}")<br>        # append cur_step_output next steps to queue<br>        next_steps = cur_step_output.next_steps<br>        step_queue.extend(next_steps)<br>        # add cur_step_output to completed steps<br>        completed_steps = self.state.get_completed_steps(task_id)<br>        completed_steps.append(cur_step_output)<br>        dispatcher.event(AgentRunStepEndEvent(step_output=cur_step_output))<br>        return cur_step_output<br>    @dispatcher.span<br>    async def _arun_step(<br>        self,<br>        task_id: str,<br>        step: Optional[TaskStep] = None,<br>        input: Optional[str] = None,<br>        mode: ChatResponseMode = ChatResponseMode.WAIT,<br>        **kwargs: Any,<br>    ) -> TaskStepOutput:<br>        """Execute step."""<br>        dispatcher.event(<br>            AgentRunStepStartEvent(task_id=task_id, step=step, input=input)<br>        )<br>        task = self.state.get_task(task_id)<br>        step_queue = self.state.get_step_queue(task_id)<br>        step = step or step_queue.popleft()<br>        if input is not None:<br>            step.input = input<br>        if self.verbose:<br>            print(f"> Running step {step.step_id}. Step input: {step.input}")<br>        # TODO: figure out if you can dynamically swap in different step executors<br>        # not clear when you would do that by theoretically possible<br>        if mode == ChatResponseMode.WAIT:<br>            cur_step_output = await self.agent_worker.arun_step(step, task, **kwargs)<br>        elif mode == ChatResponseMode.STREAM:<br>            cur_step_output = await self.agent_worker.astream_step(step, task, **kwargs)<br>        else:<br>            raise ValueError(f"Invalid mode: {mode}")<br>        # append cur_step_output next steps to queue<br>        next_steps = cur_step_output.next_steps<br>        step_queue.extend(next_steps)<br>        # add cur_step_output to completed steps<br>        completed_steps = self.state.get_completed_steps(task_id)<br>        completed_steps.append(cur_step_output)<br>        dispatcher.event(AgentRunStepEndEvent(step_output=cur_step_output))<br>        return cur_step_output<br>    @dispatcher.span<br>    def run_step(<br>        self,<br>        task_id: str,<br>        input: Optional[str] = None,<br>        step: Optional[TaskStep] = None,<br>        **kwargs: Any,<br>    ) -> TaskStepOutput:<br>        """Run step."""<br>        step = validate_step_from_args(task_id, input, step, **kwargs)<br>        return self._run_step(<br>            task_id, step, input=input, mode=ChatResponseMode.WAIT, **kwargs<br>        )<br>    @dispatcher.span<br>    async def arun_step(<br>        self,<br>        task_id: str,<br>        input: Optional[str] = None,<br>        step: Optional[TaskStep] = None,<br>        **kwargs: Any,<br>    ) -> TaskStepOutput:<br>        """Run step (async)."""<br>        step = validate_step_from_args(task_id, input, step, **kwargs)<br>        return await self._arun_step(<br>            task_id, step, input=input, mode=ChatResponseMode.WAIT, **kwargs<br>        )<br>    @dispatcher.span<br>    def stream_step(<br>        self,<br>        task_id: str,<br>        input: Optional[str] = None,<br>        step: Optional[TaskStep] = None,<br>        **kwargs: Any,<br>    ) -> TaskStepOutput:<br>        """Run step (stream)."""<br>        step = validate_step_from_args(task_id, input, step, **kwargs)<br>        return self._run_step(<br>            task_id, step, input=input, mode=ChatResponseMode.STREAM, **kwargs<br>        )<br>    @dispatcher.span<br>    async def astream_step(<br>        self,<br>        task_id: str,<br>        input: Optional[str] = None,<br>        step: Optional[TaskStep] = None,<br>        **kwargs: Any,<br>    ) -> TaskStepOutput:<br>        """Run step (async stream)."""<br>        step = validate_step_from_args(task_id, input, step, **kwargs)<br>        return await self._arun_step(<br>            task_id, step, input=input, mode=ChatResponseMode.STREAM, **kwargs<br>        )<br>    @dispatcher.span<br>    def finalize_response(<br>        self,<br>        task_id: str,<br>        step_output: Optional[TaskStepOutput] = None,<br>    ) -> AGENT_CHAT_RESPONSE_TYPE:<br>        """Finalize response."""<br>        if step_output is None:<br>            step_output = self.state.get_completed_steps(task_id)[-1]<br>        if not step_output.is_last:<br>            raise ValueError(<br>                "finalize_response can only be called on the last step output"<br>            )<br>        if not isinstance(<br>            step_output.output,<br>            (AgentChatResponse, StreamingAgentChatResponse),<br>        ):<br>            raise ValueError(<br>                "When `is_last` is True, cur_step_output.output must be "<br>                f"AGENT_CHAT_RESPONSE_TYPE: {step_output.output}"<br>            )<br>        # finalize task<br>        self.agent_worker.finalize_task(self.state.get_task(task_id))<br>        if self.delete_task_on_finish:<br>            self.delete_task(task_id)<br>        # Attach all sources generated across all steps<br>        step_output.output.sources = self.get_task(task_id).extra_state.get(<br>            "sources", []<br>        )<br>        step_output.output.set_source_nodes()<br>        return cast(AGENT_CHAT_RESPONSE_TYPE, step_output.output)<br>    @dispatcher.span<br>    def _chat(<br>        self,<br>        message: str,<br>        chat_history: Optional[List[ChatMessage]] = None,<br>        tool_choice: Union[str, dict] = "auto",<br>        mode: ChatResponseMode = ChatResponseMode.WAIT,<br>    ) -> AGENT_CHAT_RESPONSE_TYPE:<br>        """Chat with step executor."""<br>        if chat_history is not None:<br>            self.memory.set(chat_history)<br>        task = self.create_task(message)<br>        result_output = None<br>        dispatcher.event(AgentChatWithStepStartEvent(user_msg=message))<br>        while True:<br>            # pass step queue in as argument, assume step executor is stateless<br>            cur_step_output = self._run_step(<br>                task.task_id, mode=mode, tool_choice=tool_choice<br>            )<br>            if cur_step_output.is_last:<br>                result_output = cur_step_output<br>                break<br>            # ensure tool_choice does not cause endless loops<br>            tool_choice = "auto"<br>        result = self.finalize_response(<br>            task.task_id,<br>            result_output,<br>        )<br>        dispatcher.event(AgentChatWithStepEndEvent(response=result))<br>        return result<br>    @dispatcher.span<br>    async def _achat(<br>        self,<br>        message: str,<br>        chat_history: Optional[List[ChatMessage]] = None,<br>        tool_choice: Union[str, dict] = "auto",<br>        mode: ChatResponseMode = ChatResponseMode.WAIT,<br>    ) -> AGENT_CHAT_RESPONSE_TYPE:<br>        """Chat with step executor."""<br>        if chat_history is not None:<br>            self.memory.set(chat_history)<br>        task = self.create_task(message)<br>        result_output = None<br>        dispatcher.event(AgentChatWithStepStartEvent(user_msg=message))<br>        while True:<br>            # pass step queue in as argument, assume step executor is stateless<br>            cur_step_output = await self._arun_step(<br>                task.task_id, mode=mode, tool_choice=tool_choice<br>            )<br>            if cur_step_output.is_last:<br>                result_output = cur_step_output<br>                break<br>            # ensure tool_choice does not cause endless loops<br>            tool_choice = "auto"<br>        result = self.finalize_response(<br>            task.task_id,<br>            result_output,<br>        )<br>        dispatcher.event(AgentChatWithStepEndEvent(response=result))<br>        return result<br>    @dispatcher.span<br>    @trace_method("chat")<br>    def chat(<br>        self,<br>        message: str,<br>        chat_history: Optional[List[ChatMessage]] = None,<br>        tool_choice: Optional[Union[str, dict]] = None,<br>    ) -> AgentChatResponse:<br>        # override tool choice is provided as input.<br>        if tool_choice is None:<br>            tool_choice = self.default_tool_choice<br>        with self.callback_manager.event(<br>            CBEventType.AGENT_STEP,<br>            payload={EventPayload.MESSAGES: [message]},<br>        ) as e:<br>            chat_response = self._chat(<br>                message=message,<br>                chat_history=chat_history,<br>                tool_choice=tool_choice,<br>                mode=ChatResponseMode.WAIT,<br>            )<br>            assert isinstance(chat_response, AgentChatResponse)<br>            e.on_end(payload={EventPayload.RESPONSE: chat_response})<br>        return chat_response<br>    @dispatcher.span<br>    @trace_method("chat")<br>    async def achat(<br>        self,<br>        message: str,<br>        chat_history: Optional[List[ChatMessage]] = None,<br>        tool_choice: Optional[Union[str, dict]] = None,<br>    ) -> AgentChatResponse:<br>        # override tool choice is provided as input.<br>        if tool_choice is None:<br>            tool_choice = self.default_tool_choice<br>        with self.callback_manager.event(<br>            CBEventType.AGENT_STEP,<br>            payload={EventPayload.MESSAGES: [message]},<br>        ) as e:<br>            chat_response = await self._achat(<br>                message=message,<br>                chat_history=chat_history,<br>                tool_choice=tool_choice,<br>                mode=ChatResponseMode.WAIT,<br>            )<br>            assert isinstance(chat_response, AgentChatResponse)<br>            e.on_end(payload={EventPayload.RESPONSE: chat_response})<br>        return chat_response<br>    @dispatcher.span<br>    @trace_method("chat")<br>    def stream_chat(<br>        self,<br>        message: str,<br>        chat_history: Optional[List[ChatMessage]] = None,<br>        tool_choice: Optional[Union[str, dict]] = None,<br>    ) -> StreamingAgentChatResponse:<br>        # override tool choice is provided as input.<br>        if tool_choice is None:<br>            tool_choice = self.default_tool_choice<br>        with self.callback_manager.event(<br>            CBEventType.AGENT_STEP,<br>            payload={EventPayload.MESSAGES: [message]},<br>        ) as e:<br>            chat_response = self._chat(<br>                message, chat_history, tool_choice, mode=ChatResponseMode.STREAM<br>            )<br>            assert isinstance(chat_response, StreamingAgentChatResponse) or (<br>                isinstance(chat_response, AgentChatResponse)<br>                and chat_response.is_dummy_stream<br>            )<br>            e.on_end(payload={EventPayload.RESPONSE: chat_response})<br>        return chat_response  # type: ignore<br>    @dispatcher.span<br>    @trace_method("chat")<br>    async def astream_chat(<br>        self,<br>        message: str,<br>        chat_history: Optional[List[ChatMessage]] = None,<br>        tool_choice: Optional[Union[str, dict]] = None,<br>    ) -> StreamingAgentChatResponse:<br>        # override tool choice is provided as input.<br>        if tool_choice is None:<br>            tool_choice = self.default_tool_choice<br>        with self.callback_manager.event(<br>            CBEventType.AGENT_STEP,<br>            payload={EventPayload.MESSAGES: [message]},<br>        ) as e:<br>            chat_response = await self._achat(<br>                message, chat_history, tool_choice, mode=ChatResponseMode.STREAM<br>            )<br>            assert isinstance(chat_response, StreamingAgentChatResponse) or (<br>                isinstance(chat_response, AgentChatResponse)<br>                and chat_response.is_dummy_stream<br>            )<br>            e.on_end(payload={EventPayload.RESPONSE: chat_response})<br>        return chat_response  # type: ignore<br>    def undo_step(self, task_id: str) -> None:<br>        """Undo previous step."""<br>        raise NotImplementedError("undo_step not implemented")<br>``` |

#### create\_task [\#](\#llama_index.core.agent.AgentRunner.create_task "Permanent link")

```
create_task(input: str, **kwargs: Any) -> Task

```

Create task.

Source code in `llama-index-core/llama_index/core/agent/runner/base.py`

|     |     |
| --- | --- |
| ```<br>306<br>307<br>308<br>309<br>310<br>311<br>312<br>313<br>314<br>315<br>316<br>317<br>318<br>319<br>320<br>321<br>322<br>323<br>324<br>325<br>326<br>327<br>328<br>329<br>330<br>331<br>332<br>333<br>334<br>335<br>336<br>337<br>338<br>``` | ```<br>def create_task(self, input: str, **kwargs: Any) -> Task:<br>    """Create task."""<br>    if not self.init_task_state_kwargs:<br>        extra_state = kwargs.pop("extra_state", {})<br>    else:<br>        if "extra_state" in kwargs:<br>            raise ValueError(<br>                "Cannot specify both `extra_state` and `init_task_state_kwargs`"<br>            )<br>        else:<br>            extra_state = self.init_task_state_kwargs<br>    callback_manager = kwargs.pop("callback_manager", self.callback_manager)<br>    task = Task(<br>        input=input,<br>        memory=self.memory,<br>        extra_state=extra_state,<br>        callback_manager=callback_manager,<br>        **kwargs,<br>    )<br>    # # put input into memory<br>    # self.memory.put(ChatMessage(content=input, role=MessageRole.USER))<br>    # get initial step from task, and put it in the step queue<br>    initial_step = self.agent_worker.initialize_step(task)<br>    task_state = TaskState(<br>        task=task,<br>        step_queue=deque([initial_step]),<br>    )<br>    # add it to state<br>    self.state.task_dict[task.task_id] = task_state<br>    return task<br>``` |

#### delete\_task [\#](\#llama_index.core.agent.AgentRunner.delete_task "Permanent link")

```
delete_task(task_id: str) -> None

```

Delete task.

NOTE: this will not delete any previous executions from memory.

Source code in `llama-index-core/llama_index/core/agent/runner/base.py`

|     |     |
| --- | --- |
| ```<br>340<br>341<br>342<br>343<br>344<br>345<br>346<br>347<br>348<br>349<br>``` | ```<br>def delete_task(<br>    self,<br>    task_id: str,<br>) -> None:<br>    """Delete task.<br>    NOTE: this will not delete any previous executions from memory.<br>    """<br>    self.state.task_dict.pop(task_id)<br>``` |

#### list\_tasks [\#](\#llama_index.core.agent.AgentRunner.list_tasks "Permanent link")

```
list_tasks(**kwargs: Any) -> List[Task]

```

List tasks.

Source code in `llama-index-core/llama_index/core/agent/runner/base.py`

|     |     |
| --- | --- |
| ```<br>351<br>352<br>353<br>``` | ```<br>def list_tasks(self, **kwargs: Any) -> List[Task]:<br>    """List tasks."""<br>    return [task_state.task for task_state in self.state.task_dict.values()]<br>``` |

#### get\_task [\#](\#llama_index.core.agent.AgentRunner.get_task "Permanent link")

```
get_task(task_id: str, **kwargs: Any) -> Task

```

Get task.

Source code in `llama-index-core/llama_index/core/agent/runner/base.py`

|     |     |
| --- | --- |
| ```<br>355<br>356<br>357<br>``` | ```<br>def get_task(self, task_id: str, **kwargs: Any) -> Task:<br>    """Get task."""<br>    return self.state.get_task(task_id)<br>``` |

#### get\_upcoming\_steps [\#](\#llama_index.core.agent.AgentRunner.get_upcoming_steps "Permanent link")

```
get_upcoming_steps(task_id: str, **kwargs: Any) -> List[TaskStep]

```

Get upcoming steps.

Source code in `llama-index-core/llama_index/core/agent/runner/base.py`

|     |     |
| --- | --- |
| ```<br>359<br>360<br>361<br>``` | ```<br>def get_upcoming_steps(self, task_id: str, **kwargs: Any) -> List[TaskStep]:<br>    """Get upcoming steps."""<br>    return list(self.state.get_step_queue(task_id))<br>``` |

#### get\_completed\_steps [\#](\#llama_index.core.agent.AgentRunner.get_completed_steps "Permanent link")

```
get_completed_steps(task_id: str, **kwargs: Any) -> List[TaskStepOutput]

```

Get completed steps.

Source code in `llama-index-core/llama_index/core/agent/runner/base.py`

|     |     |
| --- | --- |
| ```<br>363<br>364<br>365<br>``` | ```<br>def get_completed_steps(self, task_id: str, **kwargs: Any) -> List[TaskStepOutput]:<br>    """Get completed steps."""<br>    return self.state.get_completed_steps(task_id)<br>``` |

#### get\_task\_output [\#](\#llama_index.core.agent.AgentRunner.get_task_output "Permanent link")

```
get_task_output(task_id: str, **kwargs: Any) -> TaskStepOutput

```

Get task output.

Source code in `llama-index-core/llama_index/core/agent/runner/base.py`

|     |     |
| --- | --- |
| ```<br>367<br>368<br>369<br>370<br>371<br>372<br>``` | ```<br>def get_task_output(self, task_id: str, **kwargs: Any) -> TaskStepOutput:<br>    """Get task output."""<br>    completed_steps = self.get_completed_steps(task_id)<br>    if len(completed_steps) == 0:<br>        raise ValueError(f"No completed steps for task_id: {task_id}")<br>    return completed_steps[-1]<br>``` |

#### get\_completed\_tasks [\#](\#llama_index.core.agent.AgentRunner.get_completed_tasks "Permanent link")

```
get_completed_tasks(**kwargs: Any) -> List[Task]

```

Get completed tasks.

Source code in `llama-index-core/llama_index/core/agent/runner/base.py`

|     |     |
| --- | --- |
| ```<br>374<br>375<br>376<br>377<br>378<br>379<br>380<br>381<br>382<br>383<br>``` | ```<br>def get_completed_tasks(self, **kwargs: Any) -> List[Task]:<br>    """Get completed tasks."""<br>    task_states = list(self.state.task_dict.values())<br>    completed_tasks = []<br>    for task_state in task_states:<br>        completed_steps = self.get_completed_steps(task_state.task.task_id)<br>        if len(completed_steps) > 0 and completed_steps[-1].is_last:<br>            completed_tasks.append(task_state.task)<br>    return completed_tasks<br>``` |

#### run\_step [\#](\#llama_index.core.agent.AgentRunner.run_step "Permanent link")

```
run_step(task_id: str, input: Optional[str] = None, step: Optional[TaskStep] = None, **kwargs: Any) -> TaskStepOutput

```

Run step.

Source code in `llama-index-core/llama_index/core/agent/runner/base.py`

|     |     |
| --- | --- |
| ```<br>469<br>470<br>471<br>472<br>473<br>474<br>475<br>476<br>477<br>478<br>479<br>480<br>481<br>``` | ```<br>@dispatcher.span<br>def run_step(<br>    self,<br>    task_id: str,<br>    input: Optional[str] = None,<br>    step: Optional[TaskStep] = None,<br>    **kwargs: Any,<br>) -> TaskStepOutput:<br>    """Run step."""<br>    step = validate_step_from_args(task_id, input, step, **kwargs)<br>    return self._run_step(<br>        task_id, step, input=input, mode=ChatResponseMode.WAIT, **kwargs<br>    )<br>``` |

#### arun\_step`async`[\#](\#llama_index.core.agent.AgentRunner.arun_step "Permanent link")

```
arun_step(task_id: str, input: Optional[str] = None, step: Optional[TaskStep] = None, **kwargs: Any) -> TaskStepOutput

```

Run step (async).

Source code in `llama-index-core/llama_index/core/agent/runner/base.py`

|     |     |
| --- | --- |
| ```<br>483<br>484<br>485<br>486<br>487<br>488<br>489<br>490<br>491<br>492<br>493<br>494<br>495<br>``` | ```<br>@dispatcher.span<br>async def arun_step(<br>    self,<br>    task_id: str,<br>    input: Optional[str] = None,<br>    step: Optional[TaskStep] = None,<br>    **kwargs: Any,<br>) -> TaskStepOutput:<br>    """Run step (async)."""<br>    step = validate_step_from_args(task_id, input, step, **kwargs)<br>    return await self._arun_step(<br>        task_id, step, input=input, mode=ChatResponseMode.WAIT, **kwargs<br>    )<br>``` |

#### stream\_step [\#](\#llama_index.core.agent.AgentRunner.stream_step "Permanent link")

```
stream_step(task_id: str, input: Optional[str] = None, step: Optional[TaskStep] = None, **kwargs: Any) -> TaskStepOutput

```

Run step (stream).

Source code in `llama-index-core/llama_index/core/agent/runner/base.py`

|     |     |
| --- | --- |
| ```<br>497<br>498<br>499<br>500<br>501<br>502<br>503<br>504<br>505<br>506<br>507<br>508<br>509<br>``` | ```<br>@dispatcher.span<br>def stream_step(<br>    self,<br>    task_id: str,<br>    input: Optional[str] = None,<br>    step: Optional[TaskStep] = None,<br>    **kwargs: Any,<br>) -> TaskStepOutput:<br>    """Run step (stream)."""<br>    step = validate_step_from_args(task_id, input, step, **kwargs)<br>    return self._run_step(<br>        task_id, step, input=input, mode=ChatResponseMode.STREAM, **kwargs<br>    )<br>``` |

#### astream\_step`async`[\#](\#llama_index.core.agent.AgentRunner.astream_step "Permanent link")

```
astream_step(task_id: str, input: Optional[str] = None, step: Optional[TaskStep] = None, **kwargs: Any) -> TaskStepOutput

```

Run step (async stream).

Source code in `llama-index-core/llama_index/core/agent/runner/base.py`

|     |     |
| --- | --- |
| ```<br>511<br>512<br>513<br>514<br>515<br>516<br>517<br>518<br>519<br>520<br>521<br>522<br>523<br>``` | ```<br>@dispatcher.span<br>async def astream_step(<br>    self,<br>    task_id: str,<br>    input: Optional[str] = None,<br>    step: Optional[TaskStep] = None,<br>    **kwargs: Any,<br>) -> TaskStepOutput:<br>    """Run step (async stream)."""<br>    step = validate_step_from_args(task_id, input, step, **kwargs)<br>    return await self._arun_step(<br>        task_id, step, input=input, mode=ChatResponseMode.STREAM, **kwargs<br>    )<br>``` |

#### finalize\_response [\#](\#llama_index.core.agent.AgentRunner.finalize_response "Permanent link")

```
finalize_response(task_id: str, step_output: Optional[TaskStepOutput] = None) -> AGENT_CHAT_RESPONSE_TYPE

```

Finalize response.

Source code in `llama-index-core/llama_index/core/agent/runner/base.py`

|     |     |
| --- | --- |
| ```<br>525<br>526<br>527<br>528<br>529<br>530<br>531<br>532<br>533<br>534<br>535<br>536<br>537<br>538<br>539<br>540<br>541<br>542<br>543<br>544<br>545<br>546<br>547<br>548<br>549<br>550<br>551<br>552<br>553<br>554<br>555<br>556<br>557<br>558<br>559<br>560<br>``` | ```<br>@dispatcher.span<br>def finalize_response(<br>    self,<br>    task_id: str,<br>    step_output: Optional[TaskStepOutput] = None,<br>) -> AGENT_CHAT_RESPONSE_TYPE:<br>    """Finalize response."""<br>    if step_output is None:<br>        step_output = self.state.get_completed_steps(task_id)[-1]<br>    if not step_output.is_last:<br>        raise ValueError(<br>            "finalize_response can only be called on the last step output"<br>        )<br>    if not isinstance(<br>        step_output.output,<br>        (AgentChatResponse, StreamingAgentChatResponse),<br>    ):<br>        raise ValueError(<br>            "When `is_last` is True, cur_step_output.output must be "<br>            f"AGENT_CHAT_RESPONSE_TYPE: {step_output.output}"<br>        )<br>    # finalize task<br>    self.agent_worker.finalize_task(self.state.get_task(task_id))<br>    if self.delete_task_on_finish:<br>        self.delete_task(task_id)<br>    # Attach all sources generated across all steps<br>    step_output.output.sources = self.get_task(task_id).extra_state.get(<br>        "sources", []<br>    )<br>    step_output.output.set_source_nodes()<br>    return cast(AGENT_CHAT_RESPONSE_TYPE, step_output.output)<br>``` |

#### undo\_step [\#](\#llama_index.core.agent.AgentRunner.undo_step "Permanent link")

```
undo_step(task_id: str) -> None

```

Undo previous step.

Source code in `llama-index-core/llama_index/core/agent/runner/base.py`

|     |     |
| --- | --- |
| ```<br>734<br>735<br>736<br>``` | ```<br>def undo_step(self, task_id: str) -> None:<br>    """Undo previous step."""<br>    raise NotImplementedError("undo_step not implemented")<br>``` |

### ParallelAgentRunner [\#](\#llama_index.core.agent.ParallelAgentRunner "Permanent link")

Bases: `BaseAgentRunner`

Parallel agent runner.

Executes steps in queue in parallel. Requires async support.

Source code in `llama-index-core/llama_index/core/agent/runner/parallel.py`

|     |     |
| --- | --- |
| ```<br> 72<br> 73<br> 74<br> 75<br> 76<br> 77<br> 78<br> 79<br> 80<br> 81<br> 82<br> 83<br> 84<br> 85<br> 86<br> 87<br> 88<br> 89<br> 90<br> 91<br> 92<br> 93<br> 94<br> 95<br> 96<br> 97<br> 98<br> 99<br>100<br>101<br>102<br>103<br>104<br>105<br>106<br>107<br>108<br>109<br>110<br>111<br>112<br>113<br>114<br>115<br>116<br>117<br>118<br>119<br>120<br>121<br>122<br>123<br>124<br>125<br>126<br>127<br>128<br>129<br>130<br>131<br>132<br>133<br>134<br>135<br>136<br>137<br>138<br>139<br>140<br>141<br>142<br>143<br>144<br>145<br>146<br>147<br>148<br>149<br>150<br>151<br>152<br>153<br>154<br>155<br>156<br>157<br>158<br>159<br>160<br>161<br>162<br>163<br>164<br>165<br>166<br>167<br>168<br>169<br>170<br>171<br>172<br>173<br>174<br>175<br>176<br>177<br>178<br>179<br>180<br>181<br>182<br>183<br>184<br>185<br>186<br>187<br>188<br>189<br>190<br>191<br>192<br>193<br>194<br>195<br>196<br>197<br>198<br>199<br>200<br>201<br>202<br>203<br>204<br>205<br>206<br>207<br>208<br>209<br>210<br>211<br>212<br>213<br>214<br>215<br>216<br>217<br>218<br>219<br>220<br>221<br>222<br>223<br>224<br>225<br>226<br>227<br>228<br>229<br>230<br>231<br>232<br>233<br>234<br>235<br>236<br>237<br>238<br>239<br>240<br>241<br>242<br>243<br>244<br>245<br>246<br>247<br>248<br>249<br>250<br>251<br>252<br>253<br>254<br>255<br>256<br>257<br>258<br>259<br>260<br>261<br>262<br>263<br>264<br>265<br>266<br>267<br>268<br>269<br>270<br>271<br>272<br>273<br>274<br>275<br>276<br>277<br>278<br>279<br>280<br>281<br>282<br>283<br>284<br>285<br>286<br>287<br>288<br>289<br>290<br>291<br>292<br>293<br>294<br>295<br>296<br>297<br>298<br>299<br>300<br>301<br>302<br>303<br>304<br>305<br>306<br>307<br>308<br>309<br>310<br>311<br>312<br>313<br>314<br>315<br>316<br>317<br>318<br>319<br>320<br>321<br>322<br>323<br>324<br>325<br>326<br>327<br>328<br>329<br>330<br>331<br>332<br>333<br>334<br>335<br>336<br>337<br>338<br>339<br>340<br>341<br>342<br>343<br>344<br>345<br>346<br>347<br>348<br>349<br>350<br>351<br>352<br>353<br>354<br>355<br>356<br>357<br>358<br>359<br>360<br>361<br>362<br>363<br>364<br>365<br>366<br>367<br>368<br>369<br>370<br>371<br>372<br>373<br>374<br>375<br>376<br>377<br>378<br>379<br>380<br>381<br>382<br>383<br>384<br>385<br>386<br>387<br>388<br>389<br>390<br>391<br>392<br>393<br>394<br>395<br>396<br>397<br>398<br>399<br>400<br>401<br>402<br>403<br>404<br>405<br>406<br>407<br>408<br>409<br>410<br>411<br>412<br>413<br>414<br>415<br>416<br>417<br>418<br>419<br>420<br>421<br>422<br>423<br>424<br>425<br>426<br>427<br>428<br>429<br>430<br>431<br>432<br>433<br>434<br>435<br>436<br>437<br>438<br>439<br>440<br>441<br>442<br>443<br>444<br>445<br>446<br>447<br>448<br>449<br>450<br>451<br>452<br>453<br>454<br>455<br>456<br>457<br>458<br>459<br>460<br>461<br>462<br>463<br>464<br>465<br>466<br>467<br>468<br>469<br>470<br>471<br>472<br>473<br>474<br>475<br>476<br>477<br>478<br>479<br>480<br>481<br>482<br>483<br>484<br>485<br>486<br>487<br>488<br>489<br>490<br>491<br>492<br>493<br>494<br>495<br>496<br>``` | ```<br>class ParallelAgentRunner(BaseAgentRunner):<br>    """Parallel agent runner.<br>    Executes steps in queue in parallel. Requires async support.<br>    """<br>    def __init__(<br>        self,<br>        agent_worker: BaseAgentWorker,<br>        chat_history: Optional[List[ChatMessage]] = None,<br>        state: Optional[DAGAgentState] = None,<br>        memory: Optional[BaseMemory] = None,<br>        llm: Optional[LLM] = None,<br>        callback_manager: Optional[CallbackManager] = None,<br>        init_task_state_kwargs: Optional[dict] = None,<br>        delete_task_on_finish: bool = False,<br>    ) -> None:<br>        """Initialize."""<br>        self.memory = memory or ChatMemoryBuffer.from_defaults(chat_history, llm=llm)<br>        self.state = state or DAGAgentState()<br>        self.callback_manager = callback_manager or CallbackManager([])<br>        self.init_task_state_kwargs = init_task_state_kwargs or {}<br>        self.agent_worker = agent_worker<br>        self.delete_task_on_finish = delete_task_on_finish<br>    @property<br>    def chat_history(self) -> List[ChatMessage]:<br>        return self.memory.get_all()<br>    def reset(self) -> None:<br>        self.memory.reset()<br>    def create_task(self, input: str, **kwargs: Any) -> Task:<br>        """Create task."""<br>        task = Task(<br>            input=input,<br>            memory=self.memory,<br>            extra_state=self.init_task_state_kwargs,<br>            **kwargs,<br>        )<br>        # # put input into memory<br>        # self.memory.put(ChatMessage(content=input, role=MessageRole.USER))<br>        # add it to state<br>        # get initial step from task, and put it in the step queue<br>        initial_step = self.agent_worker.initialize_step(task)<br>        task_state = DAGTaskState(<br>            task=task,<br>            root_step=initial_step,<br>            step_queue=deque([initial_step]),<br>        )<br>        self.state.task_dict[task.task_id] = task_state<br>        return task<br>    def delete_task(<br>        self,<br>        task_id: str,<br>    ) -> None:<br>        """Delete task.<br>        NOTE: this will not delete any previous executions from memory.<br>        """<br>        self.state.task_dict.pop(task_id)<br>    def get_completed_tasks(self, **kwargs: Any) -> List[Task]:<br>        """Get completed tasks."""<br>        task_states = list(self.state.task_dict.values())<br>        return [<br>            task_state.task<br>            for task_state in task_states<br>            if len(task_state.completed_steps) > 0<br>            and task_state.completed_steps[-1].is_last<br>        ]<br>    def get_task_output(self, task_id: str, **kwargs: Any) -> TaskStepOutput:<br>        """Get task output."""<br>        task_state = self.state.task_dict[task_id]<br>        if len(task_state.completed_steps) == 0:<br>            raise ValueError(f"No completed steps for task_id: {task_id}")<br>        return task_state.completed_steps[-1]<br>    def list_tasks(self, **kwargs: Any) -> List[Task]:<br>        """List tasks."""<br>        task_states = list(self.state.task_dict.values())<br>        return [task_state.task for task_state in task_states]<br>    def get_task(self, task_id: str, **kwargs: Any) -> Task:<br>        """Get task."""<br>        return self.state.get_task(task_id)<br>    def get_upcoming_steps(self, task_id: str, **kwargs: Any) -> List[TaskStep]:<br>        """Get upcoming steps."""<br>        return list(self.state.get_step_queue(task_id))<br>    def get_completed_steps(self, task_id: str, **kwargs: Any) -> List[TaskStepOutput]:<br>        """Get completed steps."""<br>        return self.state.get_completed_steps(task_id)<br>    def run_steps_in_queue(<br>        self,<br>        task_id: str,<br>        mode: ChatResponseMode = ChatResponseMode.WAIT,<br>        **kwargs: Any,<br>    ) -> List[TaskStepOutput]:<br>        """Execute steps in queue.<br>        Run all steps in queue, clearing it out.<br>        Assume that all steps can be run in parallel.<br>        """<br>        return asyncio_run(self.arun_steps_in_queue(task_id, mode=mode, **kwargs))<br>    async def arun_steps_in_queue(<br>        self,<br>        task_id: str,<br>        mode: ChatResponseMode = ChatResponseMode.WAIT,<br>        **kwargs: Any,<br>    ) -> List[TaskStepOutput]:<br>        """Execute all steps in queue.<br>        All steps in queue are assumed to be ready.<br>        """<br>        # first pop all steps from step_queue<br>        steps: List[TaskStep] = []<br>        while len(self.state.get_step_queue(task_id)) > 0:<br>            steps.append(self.state.get_step_queue(task_id).popleft())<br>        # take every item in the queue, and run it<br>        tasks = []<br>        for step in steps:<br>            tasks.append(self._arun_step(task_id, step=step, mode=mode, **kwargs))<br>        return await asyncio.gather(*tasks)<br>    def _run_step(<br>        self,<br>        task_id: str,<br>        step: Optional[TaskStep] = None,<br>        mode: ChatResponseMode = ChatResponseMode.WAIT,<br>        **kwargs: Any,<br>    ) -> TaskStepOutput:<br>        """Execute step."""<br>        task = self.state.get_task(task_id)<br>        task_queue = self.state.get_step_queue(task_id)<br>        step = step or task_queue.popleft()<br>        if not step.is_ready:<br>            raise ValueError(f"Step {step.step_id} is not ready")<br>        if mode == ChatResponseMode.WAIT:<br>            cur_step_output: TaskStepOutput = self.agent_worker.run_step(<br>                step, task, **kwargs<br>            )<br>        elif mode == ChatResponseMode.STREAM:<br>            cur_step_output = self.agent_worker.stream_step(step, task, **kwargs)<br>        else:<br>            raise ValueError(f"Invalid mode: {mode}")<br>        for next_step in cur_step_output.next_steps:<br>            if next_step.is_ready:<br>                task_queue.append(next_step)<br>        # add cur_step_output to completed steps<br>        completed_steps = self.state.get_completed_steps(task_id)<br>        completed_steps.append(cur_step_output)<br>        return cur_step_output<br>    async def _arun_step(<br>        self,<br>        task_id: str,<br>        step: Optional[TaskStep] = None,<br>        mode: ChatResponseMode = ChatResponseMode.WAIT,<br>        **kwargs: Any,<br>    ) -> TaskStepOutput:<br>        """Execute step."""<br>        task = self.state.get_task(task_id)<br>        task_queue = self.state.get_step_queue(task_id)<br>        step = step or task_queue.popleft()<br>        if not step.is_ready:<br>            raise ValueError(f"Step {step.step_id} is not ready")<br>        if mode == ChatResponseMode.WAIT:<br>            cur_step_output = await self.agent_worker.arun_step(step, task, **kwargs)<br>        elif mode == ChatResponseMode.STREAM:<br>            cur_step_output = await self.agent_worker.astream_step(step, task, **kwargs)<br>        else:<br>            raise ValueError(f"Invalid mode: {mode}")<br>        for next_step in cur_step_output.next_steps:<br>            if next_step.is_ready:<br>                task_queue.append(next_step)<br>        # add cur_step_output to completed steps<br>        completed_steps = self.state.get_completed_steps(task_id)<br>        completed_steps.append(cur_step_output)<br>        return cur_step_output<br>    def run_step(<br>        self,<br>        task_id: str,<br>        input: Optional[str] = None,<br>        step: Optional[TaskStep] = None,<br>        **kwargs: Any,<br>    ) -> TaskStepOutput:<br>        """Run step."""<br>        return self._run_step(task_id, step, mode=ChatResponseMode.WAIT, **kwargs)<br>    async def arun_step(<br>        self,<br>        task_id: str,<br>        input: Optional[str] = None,<br>        step: Optional[TaskStep] = None,<br>        **kwargs: Any,<br>    ) -> TaskStepOutput:<br>        """Run step (async)."""<br>        return await self._arun_step(<br>            task_id, step, mode=ChatResponseMode.WAIT, **kwargs<br>        )<br>    def stream_step(<br>        self,<br>        task_id: str,<br>        input: Optional[str] = None,<br>        step: Optional[TaskStep] = None,<br>        **kwargs: Any,<br>    ) -> TaskStepOutput:<br>        """Run step (stream)."""<br>        return self._run_step(task_id, step, mode=ChatResponseMode.STREAM, **kwargs)<br>    async def astream_step(<br>        self,<br>        task_id: str,<br>        input: Optional[str] = None,<br>        step: Optional[TaskStep] = None,<br>        **kwargs: Any,<br>    ) -> TaskStepOutput:<br>        """Run step (async stream)."""<br>        return await self._arun_step(<br>            task_id, step, mode=ChatResponseMode.STREAM, **kwargs<br>        )<br>    def finalize_response(<br>        self,<br>        task_id: str,<br>        step_output: Optional[TaskStepOutput] = None,<br>    ) -> AGENT_CHAT_RESPONSE_TYPE:<br>        """Finalize response."""<br>        if step_output is None:<br>            step_output = self.state.get_completed_steps(task_id)[-1]<br>        if not step_output.is_last:<br>            raise ValueError(<br>                "finalize_response can only be called on the last step output"<br>            )<br>        if not isinstance(<br>            step_output.output,<br>            (AgentChatResponse, StreamingAgentChatResponse),<br>        ):<br>            raise ValueError(<br>                "When `is_last` is True, cur_step_output.output must be "<br>                f"AGENT_CHAT_RESPONSE_TYPE: {step_output.output}"<br>            )<br>        # finalize task<br>        self.agent_worker.finalize_task(self.state.get_task(task_id))<br>        if self.delete_task_on_finish:<br>            self.delete_task(task_id)<br>        return cast(AGENT_CHAT_RESPONSE_TYPE, step_output.output)<br>    def _chat(<br>        self,<br>        message: str,<br>        chat_history: Optional[List[ChatMessage]] = None,<br>        tool_choice: Union[str, dict] = "auto",<br>        mode: ChatResponseMode = ChatResponseMode.WAIT,<br>    ) -> AGENT_CHAT_RESPONSE_TYPE:<br>        """Chat with step executor."""<br>        if chat_history is not None:<br>            self.memory.set(chat_history)<br>        task = self.create_task(message)<br>        result_output = None<br>        while True:<br>            # pass step queue in as argument, assume step executor is stateless<br>            cur_step_outputs = self.run_steps_in_queue(task.task_id, mode=mode)<br>            # check if a step output is_last<br>            is_last = any(<br>                cur_step_output.is_last for cur_step_output in cur_step_outputs<br>            )<br>            if is_last:<br>                if len(cur_step_outputs) > 1:<br>                    raise ValueError(<br>                        "More than one step output returned in final step."<br>                    )<br>                cur_step_output = cur_step_outputs[0]<br>                result_output = cur_step_output<br>                break<br>        return self.finalize_response(<br>            task.task_id,<br>            result_output,<br>        )<br>    async def _achat(<br>        self,<br>        message: str,<br>        chat_history: Optional[List[ChatMessage]] = None,<br>        tool_choice: Union[str, dict] = "auto",<br>        mode: ChatResponseMode = ChatResponseMode.WAIT,<br>    ) -> AGENT_CHAT_RESPONSE_TYPE:<br>        """Chat with step executor."""<br>        if chat_history is not None:<br>            self.memory.set(chat_history)<br>        task = self.create_task(message)<br>        result_output = None<br>        while True:<br>            # pass step queue in as argument, assume step executor is stateless<br>            cur_step_outputs = await self.arun_steps_in_queue(task.task_id, mode=mode)<br>            # check if a step output is_last<br>            is_last = any(<br>                cur_step_output.is_last for cur_step_output in cur_step_outputs<br>            )<br>            if is_last:<br>                if len(cur_step_outputs) > 1:<br>                    raise ValueError(<br>                        "More than one step output returned in final step."<br>                    )<br>                cur_step_output = cur_step_outputs[0]<br>                result_output = cur_step_output<br>                break<br>        return self.finalize_response(<br>            task.task_id,<br>            result_output,<br>        )<br>    @trace_method("chat")<br>    def chat(<br>        self,<br>        message: str,<br>        chat_history: Optional[List[ChatMessage]] = None,<br>        tool_choice: Union[str, dict] = "auto",<br>    ) -> AgentChatResponse:<br>        with self.callback_manager.event(<br>            CBEventType.AGENT_STEP,<br>            payload={EventPayload.MESSAGES: [message]},<br>        ) as e:<br>            chat_response = self._chat(<br>                message, chat_history, tool_choice, mode=ChatResponseMode.WAIT<br>            )<br>            assert isinstance(chat_response, AgentChatResponse)<br>            e.on_end(payload={EventPayload.RESPONSE: chat_response})<br>        return chat_response<br>    @trace_method("chat")<br>    async def achat(<br>        self,<br>        message: str,<br>        chat_history: Optional[List[ChatMessage]] = None,<br>        tool_choice: Union[str, dict] = "auto",<br>    ) -> AgentChatResponse:<br>        with self.callback_manager.event(<br>            CBEventType.AGENT_STEP,<br>            payload={EventPayload.MESSAGES: [message]},<br>        ) as e:<br>            chat_response = await self._achat(<br>                message, chat_history, tool_choice, mode=ChatResponseMode.WAIT<br>            )<br>            assert isinstance(chat_response, AgentChatResponse)<br>            e.on_end(payload={EventPayload.RESPONSE: chat_response})<br>        return chat_response<br>    @trace_method("chat")<br>    def stream_chat(<br>        self,<br>        message: str,<br>        chat_history: Optional[List[ChatMessage]] = None,<br>        tool_choice: Union[str, dict] = "auto",<br>    ) -> StreamingAgentChatResponse:<br>        with self.callback_manager.event(<br>            CBEventType.AGENT_STEP,<br>            payload={EventPayload.MESSAGES: [message]},<br>        ) as e:<br>            chat_response = self._chat(<br>                message, chat_history, tool_choice, mode=ChatResponseMode.STREAM<br>            )<br>            e.on_end(payload={EventPayload.RESPONSE: chat_response})<br>        return chat_response  # type: ignore<br>    @trace_method("chat")<br>    async def astream_chat(<br>        self,<br>        message: str,<br>        chat_history: Optional[List[ChatMessage]] = None,<br>        tool_choice: Union[str, dict] = "auto",<br>    ) -> StreamingAgentChatResponse:<br>        with self.callback_manager.event(<br>            CBEventType.AGENT_STEP,<br>            payload={EventPayload.MESSAGES: [message]},<br>        ) as e:<br>            chat_response = await self._achat(<br>                message, chat_history, tool_choice, mode=ChatResponseMode.STREAM<br>            )<br>            e.on_end(payload={EventPayload.RESPONSE: chat_response})<br>        return chat_response  # type: ignore<br>    def undo_step(self, task_id: str) -> None:<br>        """Undo previous step."""<br>        raise NotImplementedError("undo_step not implemented")<br>``` |

#### create\_task [\#](\#llama_index.core.agent.ParallelAgentRunner.create_task "Permanent link")

```
create_task(input: str, **kwargs: Any) -> Task

```

Create task.

Source code in `llama-index-core/llama_index/core/agent/runner/parallel.py`

|     |     |
| --- | --- |
| ```<br>105<br>106<br>107<br>108<br>109<br>110<br>111<br>112<br>113<br>114<br>115<br>116<br>117<br>118<br>119<br>120<br>121<br>122<br>123<br>124<br>125<br>126<br>127<br>``` | ```<br>def create_task(self, input: str, **kwargs: Any) -> Task:<br>    """Create task."""<br>    task = Task(<br>        input=input,<br>        memory=self.memory,<br>        extra_state=self.init_task_state_kwargs,<br>        **kwargs,<br>    )<br>    # # put input into memory<br>    # self.memory.put(ChatMessage(content=input, role=MessageRole.USER))<br>    # add it to state<br>    # get initial step from task, and put it in the step queue<br>    initial_step = self.agent_worker.initialize_step(task)<br>    task_state = DAGTaskState(<br>        task=task,<br>        root_step=initial_step,<br>        step_queue=deque([initial_step]),<br>    )<br>    self.state.task_dict[task.task_id] = task_state<br>    return task<br>``` |

#### delete\_task [\#](\#llama_index.core.agent.ParallelAgentRunner.delete_task "Permanent link")

```
delete_task(task_id: str) -> None

```

Delete task.

NOTE: this will not delete any previous executions from memory.

Source code in `llama-index-core/llama_index/core/agent/runner/parallel.py`

|     |     |
| --- | --- |
| ```<br>129<br>130<br>131<br>132<br>133<br>134<br>135<br>136<br>137<br>138<br>``` | ```<br>def delete_task(<br>    self,<br>    task_id: str,<br>) -> None:<br>    """Delete task.<br>    NOTE: this will not delete any previous executions from memory.<br>    """<br>    self.state.task_dict.pop(task_id)<br>``` |

#### get\_completed\_tasks [\#](\#llama_index.core.agent.ParallelAgentRunner.get_completed_tasks "Permanent link")

```
get_completed_tasks(**kwargs: Any) -> List[Task]

```

Get completed tasks.

Source code in `llama-index-core/llama_index/core/agent/runner/parallel.py`

|     |     |
| --- | --- |
| ```<br>140<br>141<br>142<br>143<br>144<br>145<br>146<br>147<br>148<br>``` | ```<br>def get_completed_tasks(self, **kwargs: Any) -> List[Task]:<br>    """Get completed tasks."""<br>    task_states = list(self.state.task_dict.values())<br>    return [<br>        task_state.task<br>        for task_state in task_states<br>        if len(task_state.completed_steps) > 0<br>        and task_state.completed_steps[-1].is_last<br>    ]<br>``` |

#### get\_task\_output [\#](\#llama_index.core.agent.ParallelAgentRunner.get_task_output "Permanent link")

```
get_task_output(task_id: str, **kwargs: Any) -> TaskStepOutput

```

Get task output.

Source code in `llama-index-core/llama_index/core/agent/runner/parallel.py`

|     |     |
| --- | --- |
| ```<br>150<br>151<br>152<br>153<br>154<br>155<br>``` | ```<br>def get_task_output(self, task_id: str, **kwargs: Any) -> TaskStepOutput:<br>    """Get task output."""<br>    task_state = self.state.task_dict[task_id]<br>    if len(task_state.completed_steps) == 0:<br>        raise ValueError(f"No completed steps for task_id: {task_id}")<br>    return task_state.completed_steps[-1]<br>``` |

#### list\_tasks [\#](\#llama_index.core.agent.ParallelAgentRunner.list_tasks "Permanent link")

```
list_tasks(**kwargs: Any) -> List[Task]

```

List tasks.

Source code in `llama-index-core/llama_index/core/agent/runner/parallel.py`

|     |     |
| --- | --- |
| ```<br>157<br>158<br>159<br>160<br>``` | ```<br>def list_tasks(self, **kwargs: Any) -> List[Task]:<br>    """List tasks."""<br>    task_states = list(self.state.task_dict.values())<br>    return [task_state.task for task_state in task_states]<br>``` |

#### get\_task [\#](\#llama_index.core.agent.ParallelAgentRunner.get_task "Permanent link")

```
get_task(task_id: str, **kwargs: Any) -> Task

```

Get task.

Source code in `llama-index-core/llama_index/core/agent/runner/parallel.py`

|     |     |
| --- | --- |
| ```<br>162<br>163<br>164<br>``` | ```<br>def get_task(self, task_id: str, **kwargs: Any) -> Task:<br>    """Get task."""<br>    return self.state.get_task(task_id)<br>``` |

#### get\_upcoming\_steps [\#](\#llama_index.core.agent.ParallelAgentRunner.get_upcoming_steps "Permanent link")

```
get_upcoming_steps(task_id: str, **kwargs: Any) -> List[TaskStep]

```

Get upcoming steps.

Source code in `llama-index-core/llama_index/core/agent/runner/parallel.py`

|     |     |
| --- | --- |
| ```<br>166<br>167<br>168<br>``` | ```<br>def get_upcoming_steps(self, task_id: str, **kwargs: Any) -> List[TaskStep]:<br>    """Get upcoming steps."""<br>    return list(self.state.get_step_queue(task_id))<br>``` |

#### get\_completed\_steps [\#](\#llama_index.core.agent.ParallelAgentRunner.get_completed_steps "Permanent link")

```
get_completed_steps(task_id: str, **kwargs: Any) -> List[TaskStepOutput]

```

Get completed steps.

Source code in `llama-index-core/llama_index/core/agent/runner/parallel.py`

|     |     |
| --- | --- |
| ```<br>170<br>171<br>172<br>``` | ```<br>def get_completed_steps(self, task_id: str, **kwargs: Any) -> List[TaskStepOutput]:<br>    """Get completed steps."""<br>    return self.state.get_completed_steps(task_id)<br>``` |

#### run\_steps\_in\_queue [\#](\#llama_index.core.agent.ParallelAgentRunner.run_steps_in_queue "Permanent link")

```
run_steps_in_queue(task_id: str, mode: ChatResponseMode = ChatResponseMode.WAIT, **kwargs: Any) -> List[TaskStepOutput]

```

Execute steps in queue.

Run all steps in queue, clearing it out.

Assume that all steps can be run in parallel.

Source code in `llama-index-core/llama_index/core/agent/runner/parallel.py`

|     |     |
| --- | --- |
| ```<br>174<br>175<br>176<br>177<br>178<br>179<br>180<br>181<br>182<br>183<br>184<br>185<br>186<br>187<br>``` | ```<br>def run_steps_in_queue(<br>    self,<br>    task_id: str,<br>    mode: ChatResponseMode = ChatResponseMode.WAIT,<br>    **kwargs: Any,<br>) -> List[TaskStepOutput]:<br>    """Execute steps in queue.<br>    Run all steps in queue, clearing it out.<br>    Assume that all steps can be run in parallel.<br>    """<br>    return asyncio_run(self.arun_steps_in_queue(task_id, mode=mode, **kwargs))<br>``` |

#### arun\_steps\_in\_queue`async`[\#](\#llama_index.core.agent.ParallelAgentRunner.arun_steps_in_queue "Permanent link")

```
arun_steps_in_queue(task_id: str, mode: ChatResponseMode = ChatResponseMode.WAIT, **kwargs: Any) -> List[TaskStepOutput]

```

Execute all steps in queue.

All steps in queue are assumed to be ready.

Source code in `llama-index-core/llama_index/core/agent/runner/parallel.py`

|     |     |
| --- | --- |
| ```<br>189<br>190<br>191<br>192<br>193<br>194<br>195<br>196<br>197<br>198<br>199<br>200<br>201<br>202<br>203<br>204<br>205<br>206<br>207<br>208<br>209<br>210<br>``` | ```<br>async def arun_steps_in_queue(<br>    self,<br>    task_id: str,<br>    mode: ChatResponseMode = ChatResponseMode.WAIT,<br>    **kwargs: Any,<br>) -> List[TaskStepOutput]:<br>    """Execute all steps in queue.<br>    All steps in queue are assumed to be ready.<br>    """<br>    # first pop all steps from step_queue<br>    steps: List[TaskStep] = []<br>    while len(self.state.get_step_queue(task_id)) > 0:<br>        steps.append(self.state.get_step_queue(task_id).popleft())<br>    # take every item in the queue, and run it<br>    tasks = []<br>    for step in steps:<br>        tasks.append(self._arun_step(task_id, step=step, mode=mode, **kwargs))<br>    return await asyncio.gather(*tasks)<br>``` |

#### run\_step [\#](\#llama_index.core.agent.ParallelAgentRunner.run_step "Permanent link")

```
run_step(task_id: str, input: Optional[str] = None, step: Optional[TaskStep] = None, **kwargs: Any) -> TaskStepOutput

```

Run step.

Source code in `llama-index-core/llama_index/core/agent/runner/parallel.py`

|     |     |
| --- | --- |
| ```<br>278<br>279<br>280<br>281<br>282<br>283<br>284<br>285<br>286<br>``` | ```<br>def run_step(<br>    self,<br>    task_id: str,<br>    input: Optional[str] = None,<br>    step: Optional[TaskStep] = None,<br>    **kwargs: Any,<br>) -> TaskStepOutput:<br>    """Run step."""<br>    return self._run_step(task_id, step, mode=ChatResponseMode.WAIT, **kwargs)<br>``` |

#### arun\_step`async`[\#](\#llama_index.core.agent.ParallelAgentRunner.arun_step "Permanent link")

```
arun_step(task_id: str, input: Optional[str] = None, step: Optional[TaskStep] = None, **kwargs: Any) -> TaskStepOutput

```

Run step (async).

Source code in `llama-index-core/llama_index/core/agent/runner/parallel.py`

|     |     |
| --- | --- |
| ```<br>288<br>289<br>290<br>291<br>292<br>293<br>294<br>295<br>296<br>297<br>298<br>``` | ```<br>async def arun_step(<br>    self,<br>    task_id: str,<br>    input: Optional[str] = None,<br>    step: Optional[TaskStep] = None,<br>    **kwargs: Any,<br>) -> TaskStepOutput:<br>    """Run step (async)."""<br>    return await self._arun_step(<br>        task_id, step, mode=ChatResponseMode.WAIT, **kwargs<br>    )<br>``` |

#### stream\_step [\#](\#llama_index.core.agent.ParallelAgentRunner.stream_step "Permanent link")

```
stream_step(task_id: str, input: Optional[str] = None, step: Optional[TaskStep] = None, **kwargs: Any) -> TaskStepOutput

```

Run step (stream).

Source code in `llama-index-core/llama_index/core/agent/runner/parallel.py`

|     |     |
| --- | --- |
| ```<br>300<br>301<br>302<br>303<br>304<br>305<br>306<br>307<br>308<br>``` | ```<br>def stream_step(<br>    self,<br>    task_id: str,<br>    input: Optional[str] = None,<br>    step: Optional[TaskStep] = None,<br>    **kwargs: Any,<br>) -> TaskStepOutput:<br>    """Run step (stream)."""<br>    return self._run_step(task_id, step, mode=ChatResponseMode.STREAM, **kwargs)<br>``` |

#### astream\_step`async`[\#](\#llama_index.core.agent.ParallelAgentRunner.astream_step "Permanent link")

```
astream_step(task_id: str, input: Optional[str] = None, step: Optional[TaskStep] = None, **kwargs: Any) -> TaskStepOutput

```

Run step (async stream).

Source code in `llama-index-core/llama_index/core/agent/runner/parallel.py`

|     |     |
| --- | --- |
| ```<br>310<br>311<br>312<br>313<br>314<br>315<br>316<br>317<br>318<br>319<br>320<br>``` | ```<br>async def astream_step(<br>    self,<br>    task_id: str,<br>    input: Optional[str] = None,<br>    step: Optional[TaskStep] = None,<br>    **kwargs: Any,<br>) -> TaskStepOutput:<br>    """Run step (async stream)."""<br>    return await self._arun_step(<br>        task_id, step, mode=ChatResponseMode.STREAM, **kwargs<br>    )<br>``` |

#### finalize\_response [\#](\#llama_index.core.agent.ParallelAgentRunner.finalize_response "Permanent link")

```
finalize_response(task_id: str, step_output: Optional[TaskStepOutput] = None) -> AGENT_CHAT_RESPONSE_TYPE

```

Finalize response.

Source code in `llama-index-core/llama_index/core/agent/runner/parallel.py`

|     |     |
| --- | --- |
| ```<br>322<br>323<br>324<br>325<br>326<br>327<br>328<br>329<br>330<br>331<br>332<br>333<br>334<br>335<br>336<br>337<br>338<br>339<br>340<br>341<br>342<br>343<br>344<br>345<br>346<br>347<br>348<br>349<br>350<br>``` | ```<br>def finalize_response(<br>    self,<br>    task_id: str,<br>    step_output: Optional[TaskStepOutput] = None,<br>) -> AGENT_CHAT_RESPONSE_TYPE:<br>    """Finalize response."""<br>    if step_output is None:<br>        step_output = self.state.get_completed_steps(task_id)[-1]<br>    if not step_output.is_last:<br>        raise ValueError(<br>            "finalize_response can only be called on the last step output"<br>        )<br>    if not isinstance(<br>        step_output.output,<br>        (AgentChatResponse, StreamingAgentChatResponse),<br>    ):<br>        raise ValueError(<br>            "When `is_last` is True, cur_step_output.output must be "<br>            f"AGENT_CHAT_RESPONSE_TYPE: {step_output.output}"<br>        )<br>    # finalize task<br>    self.agent_worker.finalize_task(self.state.get_task(task_id))<br>    if self.delete_task_on_finish:<br>        self.delete_task(task_id)<br>    return cast(AGENT_CHAT_RESPONSE_TYPE, step_output.output)<br>``` |

#### undo\_step [\#](\#llama_index.core.agent.ParallelAgentRunner.undo_step "Permanent link")

```
undo_step(task_id: str) -> None

```

Undo previous step.

Source code in `llama-index-core/llama_index/core/agent/runner/parallel.py`

|     |     |
| --- | --- |
| ```<br>494<br>495<br>496<br>``` | ```<br>def undo_step(self, task_id: str) -> None:<br>    """Undo previous step."""<br>    raise NotImplementedError("undo_step not implemented")<br>``` |

## Workers [\#](\#workers "Permanent link")

### CustomSimpleAgentWorker [\#](\#llama_index.core.agent.CustomSimpleAgentWorker "Permanent link")

Bases: `BaseModel`, `BaseAgentWorker`

Custom simple agent worker.

This is "simple" in the sense that some of the scaffolding is setup already.
Assumptions:
\- assumes that the agent has tools, llm, callback manager, and tool retriever
\- has a `from_tools` convenience function
\- assumes that the agent is sequential, and doesn't take in any additional
intermediate inputs.

**Parameters:**

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `tools` | `Sequence[BaseTool]` | Tools to use for reasoning | _required_ |
| `llm` | `LLM` | LLM to use | _required_ |
| `callback_manager` | `CallbackManager` | Callback manager | `None` |
| `tool_retriever` | `Optional[ObjectRetriever[BaseTool]]` | Tool retriever | `None` |
| `verbose` | `bool` | Whether to print out reasoning steps | `False` |

Source code in `llama-index-core/llama_index/core/agent/custom/simple.py`

|     |     |
| --- | --- |
| ```<br> 39<br> 40<br> 41<br> 42<br> 43<br> 44<br> 45<br> 46<br> 47<br> 48<br> 49<br> 50<br> 51<br> 52<br> 53<br> 54<br> 55<br> 56<br> 57<br> 58<br> 59<br> 60<br> 61<br> 62<br> 63<br> 64<br> 65<br> 66<br> 67<br> 68<br> 69<br> 70<br> 71<br> 72<br> 73<br> 74<br> 75<br> 76<br> 77<br> 78<br> 79<br> 80<br> 81<br> 82<br> 83<br> 84<br> 85<br> 86<br> 87<br> 88<br> 89<br> 90<br> 91<br> 92<br> 93<br> 94<br> 95<br> 96<br> 97<br> 98<br> 99<br>100<br>101<br>102<br>103<br>104<br>105<br>106<br>107<br>108<br>109<br>110<br>111<br>112<br>113<br>114<br>115<br>116<br>117<br>118<br>119<br>120<br>121<br>122<br>123<br>124<br>125<br>126<br>127<br>128<br>129<br>130<br>131<br>132<br>133<br>134<br>135<br>136<br>137<br>138<br>139<br>140<br>141<br>142<br>143<br>144<br>145<br>146<br>147<br>148<br>149<br>150<br>151<br>152<br>153<br>154<br>155<br>156<br>157<br>158<br>159<br>160<br>161<br>162<br>163<br>164<br>165<br>166<br>167<br>168<br>169<br>170<br>171<br>172<br>173<br>174<br>175<br>176<br>177<br>178<br>179<br>180<br>181<br>182<br>183<br>184<br>185<br>186<br>187<br>188<br>189<br>190<br>191<br>192<br>193<br>194<br>195<br>196<br>197<br>198<br>199<br>200<br>201<br>202<br>203<br>204<br>205<br>206<br>207<br>208<br>209<br>210<br>211<br>212<br>213<br>214<br>215<br>216<br>217<br>218<br>219<br>220<br>221<br>222<br>223<br>224<br>225<br>226<br>227<br>228<br>229<br>230<br>231<br>232<br>233<br>234<br>235<br>236<br>237<br>238<br>239<br>240<br>241<br>242<br>243<br>244<br>245<br>246<br>247<br>248<br>249<br>250<br>251<br>252<br>253<br>254<br>255<br>256<br>257<br>258<br>259<br>260<br>261<br>``` | ```<br>class CustomSimpleAgentWorker(BaseModel, BaseAgentWorker):<br>    """Custom simple agent worker.<br>    This is "simple" in the sense that some of the scaffolding is setup already.<br>    Assumptions:<br>    - assumes that the agent has tools, llm, callback manager, and tool retriever<br>    - has a `from_tools` convenience function<br>    - assumes that the agent is sequential, and doesn't take in any additional<br>    intermediate inputs.<br>    Args:<br>        tools (Sequence[BaseTool]): Tools to use for reasoning<br>        llm (LLM): LLM to use<br>        callback_manager (CallbackManager): Callback manager<br>        tool_retriever (Optional[ObjectRetriever[BaseTool]]): Tool retriever<br>        verbose (bool): Whether to print out reasoning steps<br>    """<br>    model_config = ConfigDict(arbitrary_types_allowed=True)<br>    tools: Sequence[BaseTool] = Field(..., description="Tools to use for reasoning")<br>    llm: LLM = Field(..., description="LLM to use")<br>    callback_manager: CallbackManager = Field(<br>        default_factory=lambda: CallbackManager([]), exclude=True<br>    )<br>    tool_retriever: Optional[ObjectRetriever[BaseTool]] = Field(<br>        default=None, description="Tool retriever"<br>    )<br>    verbose: bool = Field(False, description="Whether to print out reasoning steps")<br>    _get_tools: Callable[[str], Sequence[BaseTool]] = PrivateAttr()<br>    def __init__(<br>        self,<br>        tools: Sequence[BaseTool],<br>        llm: LLM,<br>        callback_manager: Optional[CallbackManager] = None,<br>        verbose: bool = False,<br>        tool_retriever: Optional[ObjectRetriever[BaseTool]] = None,<br>        **kwargs: Any,<br>    ) -> None:<br>        callback_manager = callback_manager or CallbackManager([])<br>        super().__init__(<br>            tools=tools,<br>            llm=llm,<br>            callback_manager=callback_manager or CallbackManager([]),<br>            tool_retriever=tool_retriever,<br>            verbose=verbose,<br>            **kwargs,<br>        )<br>        if len(tools) > 0 and tool_retriever is not None:<br>            raise ValueError("Cannot specify both tools and tool_retriever")<br>        elif len(tools) > 0:<br>            self._get_tools = lambda _: tools<br>        elif tool_retriever is not None:<br>            tool_retriever_c = cast(ObjectRetriever[BaseTool], tool_retriever)<br>            self._get_tools = lambda message: tool_retriever_c.retrieve(message)<br>        else:<br>            self._get_tools = lambda _: []<br>    @classmethod<br>    def from_tools(<br>        cls,<br>        tools: Optional[Sequence[BaseTool]] = None,<br>        tool_retriever: Optional[ObjectRetriever[BaseTool]] = None,<br>        llm: Optional[LLM] = None,<br>        callback_manager: Optional[CallbackManager] = None,<br>        verbose: bool = False,<br>        **kwargs: Any,<br>    ) -> "CustomSimpleAgentWorker":<br>        """Convenience constructor method from set of of BaseTools (Optional)."""<br>        llm = llm or Settings.llm<br>        if callback_manager is not None:<br>            llm.callback_manager = callback_manager<br>        return cls(<br>            tools=tools or [],<br>            tool_retriever=tool_retriever,<br>            llm=llm,<br>            callback_manager=callback_manager or CallbackManager([]),<br>            verbose=verbose,<br>            **kwargs,<br>        )<br>    @abstractmethod<br>    def _initialize_state(self, task: Task, **kwargs: Any) -> Dict[str, Any]:<br>        """Initialize state."""<br>    def initialize_step(self, task: Task, **kwargs: Any) -> TaskStep:<br>        """Initialize step from task."""<br>        sources: List[ToolOutput] = []<br>        # temporary memory for new messages<br>        new_memory = ChatMemoryBuffer.from_defaults()<br>        # initialize initial state<br>        initial_state = {<br>            "sources": sources,<br>            "memory": new_memory,<br>        }<br>        step_state = self._initialize_state(task, **kwargs)<br>        # if intersecting keys, error<br>        if set(step_state.keys()).intersection(set(initial_state.keys())):<br>            raise ValueError(<br>                f"Step state keys {step_state.keys()} and initial state keys {initial_state.keys()} intersect."<br>                f"*NOTE*: initial state keys {initial_state.keys()} are reserved."<br>            )<br>        step_state.update(initial_state)<br>        return TaskStep(<br>            task_id=task.task_id,<br>            step_id=str(uuid.uuid4()),<br>            input=task.input,<br>            step_state=step_state,<br>        )<br>    def get_tools(self, input: str) -> List[AsyncBaseTool]:<br>        """Get tools."""<br>        return [adapt_to_async_tool(t) for t in self._get_tools(input)]<br>    def _get_task_step_response(<br>        self, agent_response: AGENT_CHAT_RESPONSE_TYPE, step: TaskStep, is_done: bool<br>    ) -> TaskStepOutput:<br>        """Get task step response."""<br>        if is_done:<br>            new_steps = []<br>        else:<br>            new_steps = [<br>                step.get_next_step(<br>                    step_id=str(uuid.uuid4()),<br>                    # NOTE: input is unused<br>                    input=None,<br>                )<br>            ]<br>        return TaskStepOutput(<br>            output=agent_response,<br>            task_step=step,<br>            is_last=is_done,<br>            next_steps=new_steps,<br>        )<br>    @abstractmethod<br>    def _run_step(<br>        self, state: Dict[str, Any], task: Task, input: Optional[str] = None<br>    ) -> Tuple[AgentChatResponse, bool]:<br>        """Run step.<br>        Returns:<br>            Tuple of (agent_response, is_done)<br>        """<br>    async def _arun_step(<br>        self, state: Dict[str, Any], task: Task, input: Optional[str] = None<br>    ) -> Tuple[AgentChatResponse, bool]:<br>        """Run step (async).<br>        Can override this method if you want to run the step asynchronously.<br>        Returns:<br>            Tuple of (agent_response, is_done)<br>        """<br>        raise NotImplementedError(<br>            "This agent does not support async." "Please implement _arun_step."<br>        )<br>    @trace_method("run_step")<br>    def run_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:<br>        """Run step."""<br>        agent_response, is_done = self._run_step(<br>            step.step_state, task, input=step.input<br>        )<br>        response = self._get_task_step_response(agent_response, step, is_done)<br>        # sync step state with task state<br>        task.extra_state.update(step.step_state)<br>        return response<br>    @trace_method("run_step")<br>    async def arun_step(<br>        self, step: TaskStep, task: Task, **kwargs: Any<br>    ) -> TaskStepOutput:<br>        """Run step (async)."""<br>        agent_response, is_done = await self._arun_step(<br>            step.step_state, task, input=step.input<br>        )<br>        response = self._get_task_step_response(agent_response, step, is_done)<br>        task.extra_state.update(step.step_state)<br>        return response<br>    @trace_method("run_step")<br>    def stream_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:<br>        """Run step (stream)."""<br>        raise NotImplementedError("This agent does not support streaming.")<br>    @trace_method("run_step")<br>    async def astream_step(<br>        self, step: TaskStep, task: Task, **kwargs: Any<br>    ) -> TaskStepOutput:<br>        """Run step (async stream)."""<br>        raise NotImplementedError("This agent does not support streaming.")<br>    @abstractmethod<br>    def _finalize_task(self, state: Dict[str, Any], **kwargs: Any) -> None:<br>        """Finalize task, after all the steps are completed.<br>        State is all the step states.<br>        """<br>    def finalize_task(self, task: Task, **kwargs: Any) -> None:<br>        """Finalize task, after all the steps are completed."""<br>        # add new messages to memory<br>        task.memory.set(task.memory.get() + task.extra_state["memory"].get_all())<br>        # reset new memory<br>        task.extra_state["memory"].reset()<br>        self._finalize_task(task.extra_state, **kwargs)<br>    def set_callback_manager(self, callback_manager: CallbackManager) -> None:<br>        """Set callback manager."""<br>        # TODO: make this abstractmethod (right now will break some agent impls)<br>        self.callback_manager = callback_manager<br>``` |

#### from\_tools`classmethod`[\#](\#llama_index.core.agent.CustomSimpleAgentWorker.from_tools "Permanent link")

```
from_tools(tools: Optional[Sequence[BaseTool]] = None, tool_retriever: Optional[ObjectRetriever[BaseTool]] = None, llm: Optional[LLM] = None, callback_manager: Optional[CallbackManager] = None, verbose: bool = False, **kwargs: Any) -> CustomSimpleAgentWorker

```

Convenience constructor method from set of of BaseTools (Optional).

Source code in `llama-index-core/llama_index/core/agent/custom/simple.py`

|     |     |
| --- | --- |
| ```<br>100<br>101<br>102<br>103<br>104<br>105<br>106<br>107<br>108<br>109<br>110<br>111<br>112<br>113<br>114<br>115<br>116<br>117<br>118<br>119<br>120<br>121<br>``` | ```<br>@classmethod<br>def from_tools(<br>    cls,<br>    tools: Optional[Sequence[BaseTool]] = None,<br>    tool_retriever: Optional[ObjectRetriever[BaseTool]] = None,<br>    llm: Optional[LLM] = None,<br>    callback_manager: Optional[CallbackManager] = None,<br>    verbose: bool = False,<br>    **kwargs: Any,<br>) -> "CustomSimpleAgentWorker":<br>    """Convenience constructor method from set of of BaseTools (Optional)."""<br>    llm = llm or Settings.llm<br>    if callback_manager is not None:<br>        llm.callback_manager = callback_manager<br>    return cls(<br>        tools=tools or [],<br>        tool_retriever=tool_retriever,<br>        llm=llm,<br>        callback_manager=callback_manager or CallbackManager([]),<br>        verbose=verbose,<br>        **kwargs,<br>    )<br>``` |

#### initialize\_step [\#](\#llama_index.core.agent.CustomSimpleAgentWorker.initialize_step "Permanent link")

```
initialize_step(task: Task, **kwargs: Any) -> TaskStep

```

Initialize step from task.

Source code in `llama-index-core/llama_index/core/agent/custom/simple.py`

|     |     |
| --- | --- |
| ```<br>127<br>128<br>129<br>130<br>131<br>132<br>133<br>134<br>135<br>136<br>137<br>138<br>139<br>140<br>141<br>142<br>143<br>144<br>145<br>146<br>147<br>148<br>149<br>150<br>151<br>152<br>153<br>``` | ```<br>def initialize_step(self, task: Task, **kwargs: Any) -> TaskStep:<br>    """Initialize step from task."""<br>    sources: List[ToolOutput] = []<br>    # temporary memory for new messages<br>    new_memory = ChatMemoryBuffer.from_defaults()<br>    # initialize initial state<br>    initial_state = {<br>        "sources": sources,<br>        "memory": new_memory,<br>    }<br>    step_state = self._initialize_state(task, **kwargs)<br>    # if intersecting keys, error<br>    if set(step_state.keys()).intersection(set(initial_state.keys())):<br>        raise ValueError(<br>            f"Step state keys {step_state.keys()} and initial state keys {initial_state.keys()} intersect."<br>            f"*NOTE*: initial state keys {initial_state.keys()} are reserved."<br>        )<br>    step_state.update(initial_state)<br>    return TaskStep(<br>        task_id=task.task_id,<br>        step_id=str(uuid.uuid4()),<br>        input=task.input,<br>        step_state=step_state,<br>    )<br>``` |

#### get\_tools [\#](\#llama_index.core.agent.CustomSimpleAgentWorker.get_tools "Permanent link")

```
get_tools(input: str) -> List[AsyncBaseTool]

```

Get tools.

Source code in `llama-index-core/llama_index/core/agent/custom/simple.py`

|     |     |
| --- | --- |
| ```<br>155<br>156<br>157<br>``` | ```<br>def get_tools(self, input: str) -> List[AsyncBaseTool]:<br>    """Get tools."""<br>    return [adapt_to_async_tool(t) for t in self._get_tools(input)]<br>``` |

#### run\_step [\#](\#llama_index.core.agent.CustomSimpleAgentWorker.run_step "Permanent link")

```
run_step(step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput

```

Run step.

Source code in `llama-index-core/llama_index/core/agent/custom/simple.py`

|     |     |
| --- | --- |
| ```<br>207<br>208<br>209<br>210<br>211<br>212<br>213<br>214<br>215<br>216<br>``` | ```<br>@trace_method("run_step")<br>def run_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:<br>    """Run step."""<br>    agent_response, is_done = self._run_step(<br>        step.step_state, task, input=step.input<br>    )<br>    response = self._get_task_step_response(agent_response, step, is_done)<br>    # sync step state with task state<br>    task.extra_state.update(step.step_state)<br>    return response<br>``` |

#### arun\_step`async`[\#](\#llama_index.core.agent.CustomSimpleAgentWorker.arun_step "Permanent link")

```
arun_step(step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput

```

Run step (async).

Source code in `llama-index-core/llama_index/core/agent/custom/simple.py`

|     |     |
| --- | --- |
| ```<br>218<br>219<br>220<br>221<br>222<br>223<br>224<br>225<br>226<br>227<br>228<br>``` | ```<br>@trace_method("run_step")<br>async def arun_step(<br>    self, step: TaskStep, task: Task, **kwargs: Any<br>) -> TaskStepOutput:<br>    """Run step (async)."""<br>    agent_response, is_done = await self._arun_step(<br>        step.step_state, task, input=step.input<br>    )<br>    response = self._get_task_step_response(agent_response, step, is_done)<br>    task.extra_state.update(step.step_state)<br>    return response<br>``` |

#### stream\_step [\#](\#llama_index.core.agent.CustomSimpleAgentWorker.stream_step "Permanent link")

```
stream_step(step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput

```

Run step (stream).

Source code in `llama-index-core/llama_index/core/agent/custom/simple.py`

|     |     |
| --- | --- |
| ```<br>230<br>231<br>232<br>233<br>``` | ```<br>@trace_method("run_step")<br>def stream_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:<br>    """Run step (stream)."""<br>    raise NotImplementedError("This agent does not support streaming.")<br>``` |

#### astream\_step`async`[\#](\#llama_index.core.agent.CustomSimpleAgentWorker.astream_step "Permanent link")

```
astream_step(step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput

```

Run step (async stream).

Source code in `llama-index-core/llama_index/core/agent/custom/simple.py`

|     |     |
| --- | --- |
| ```<br>235<br>236<br>237<br>238<br>239<br>240<br>``` | ```<br>@trace_method("run_step")<br>async def astream_step(<br>    self, step: TaskStep, task: Task, **kwargs: Any<br>) -> TaskStepOutput:<br>    """Run step (async stream)."""<br>    raise NotImplementedError("This agent does not support streaming.")<br>``` |

#### finalize\_task [\#](\#llama_index.core.agent.CustomSimpleAgentWorker.finalize_task "Permanent link")

```
finalize_task(task: Task, **kwargs: Any) -> None

```

Finalize task, after all the steps are completed.

Source code in `llama-index-core/llama_index/core/agent/custom/simple.py`

|     |     |
| --- | --- |
| ```<br>250<br>251<br>252<br>253<br>254<br>255<br>256<br>``` | ```<br>def finalize_task(self, task: Task, **kwargs: Any) -> None:<br>    """Finalize task, after all the steps are completed."""<br>    # add new messages to memory<br>    task.memory.set(task.memory.get() + task.extra_state["memory"].get_all())<br>    # reset new memory<br>    task.extra_state["memory"].reset()<br>    self._finalize_task(task.extra_state, **kwargs)<br>``` |

#### set\_callback\_manager [\#](\#llama_index.core.agent.CustomSimpleAgentWorker.set_callback_manager "Permanent link")

```
set_callback_manager(callback_manager: CallbackManager) -> None

```

Set callback manager.

Source code in `llama-index-core/llama_index/core/agent/custom/simple.py`

|     |     |
| --- | --- |
| ```<br>258<br>259<br>260<br>261<br>``` | ```<br>def set_callback_manager(self, callback_manager: CallbackManager) -> None:<br>    """Set callback manager."""<br>    # TODO: make this abstractmethod (right now will break some agent impls)<br>    self.callback_manager = callback_manager<br>``` |

### MultimodalReActAgentWorker [\#](\#llama_index.core.agent.MultimodalReActAgentWorker "Permanent link")

Bases: `BaseAgentWorker`

Multimodal ReAct Agent worker.

**NOTE**: This is a BETA feature.

Source code in `llama-index-core/llama_index/core/agent/react_multimodal/step.py`

|     |     |
| --- | --- |
| ```<br>103<br>104<br>105<br>106<br>107<br>108<br>109<br>110<br>111<br>112<br>113<br>114<br>115<br>116<br>117<br>118<br>119<br>120<br>121<br>122<br>123<br>124<br>125<br>126<br>127<br>128<br>129<br>130<br>131<br>132<br>133<br>134<br>135<br>136<br>137<br>138<br>139<br>140<br>141<br>142<br>143<br>144<br>145<br>146<br>147<br>148<br>149<br>150<br>151<br>152<br>153<br>154<br>155<br>156<br>157<br>158<br>159<br>160<br>161<br>162<br>163<br>164<br>165<br>166<br>167<br>168<br>169<br>170<br>171<br>172<br>173<br>174<br>175<br>176<br>177<br>178<br>179<br>180<br>181<br>182<br>183<br>184<br>185<br>186<br>187<br>188<br>189<br>190<br>191<br>192<br>193<br>194<br>195<br>196<br>197<br>198<br>199<br>200<br>201<br>202<br>203<br>204<br>205<br>206<br>207<br>208<br>209<br>210<br>211<br>212<br>213<br>214<br>215<br>216<br>217<br>218<br>219<br>220<br>221<br>222<br>223<br>224<br>225<br>226<br>227<br>228<br>229<br>230<br>231<br>232<br>233<br>234<br>235<br>236<br>237<br>238<br>239<br>240<br>241<br>242<br>243<br>244<br>245<br>246<br>247<br>248<br>249<br>250<br>251<br>252<br>253<br>254<br>255<br>256<br>257<br>258<br>259<br>260<br>261<br>262<br>263<br>264<br>265<br>266<br>267<br>268<br>269<br>270<br>271<br>272<br>273<br>274<br>275<br>276<br>277<br>278<br>279<br>280<br>281<br>282<br>283<br>284<br>285<br>286<br>287<br>288<br>289<br>290<br>291<br>292<br>293<br>294<br>295<br>296<br>297<br>298<br>299<br>300<br>301<br>302<br>303<br>304<br>305<br>306<br>307<br>308<br>309<br>310<br>311<br>312<br>313<br>314<br>315<br>316<br>317<br>318<br>319<br>320<br>321<br>322<br>323<br>324<br>325<br>326<br>327<br>328<br>329<br>330<br>331<br>332<br>333<br>334<br>335<br>336<br>337<br>338<br>339<br>340<br>341<br>342<br>343<br>344<br>345<br>346<br>347<br>348<br>349<br>350<br>351<br>352<br>353<br>354<br>355<br>356<br>357<br>358<br>359<br>360<br>361<br>362<br>363<br>364<br>365<br>366<br>367<br>368<br>369<br>370<br>371<br>372<br>373<br>374<br>375<br>376<br>377<br>378<br>379<br>380<br>381<br>382<br>383<br>384<br>385<br>386<br>387<br>388<br>389<br>390<br>391<br>392<br>393<br>394<br>395<br>396<br>397<br>398<br>399<br>400<br>401<br>402<br>403<br>404<br>405<br>406<br>407<br>408<br>409<br>410<br>411<br>412<br>413<br>414<br>415<br>416<br>417<br>418<br>419<br>420<br>421<br>422<br>423<br>424<br>425<br>426<br>427<br>428<br>429<br>430<br>431<br>432<br>433<br>434<br>435<br>436<br>437<br>438<br>439<br>440<br>441<br>442<br>443<br>444<br>445<br>446<br>447<br>448<br>449<br>450<br>451<br>452<br>453<br>454<br>455<br>456<br>457<br>458<br>459<br>460<br>461<br>462<br>463<br>464<br>465<br>466<br>467<br>468<br>469<br>470<br>471<br>472<br>473<br>474<br>475<br>476<br>477<br>478<br>479<br>480<br>481<br>482<br>483<br>484<br>485<br>486<br>487<br>488<br>489<br>490<br>491<br>492<br>493<br>494<br>495<br>496<br>497<br>498<br>499<br>500<br>501<br>502<br>503<br>504<br>505<br>506<br>507<br>508<br>509<br>510<br>511<br>512<br>513<br>514<br>515<br>516<br>517<br>518<br>519<br>520<br>521<br>522<br>523<br>524<br>``` | ```<br>class MultimodalReActAgentWorker(BaseAgentWorker):<br>    """Multimodal ReAct Agent worker.<br>    **NOTE**: This is a BETA feature.<br>    """<br>    def __init__(<br>        self,<br>        tools: Sequence[BaseTool],<br>        multi_modal_llm: MultiModalLLM,<br>        max_iterations: int = 10,<br>        react_chat_formatter: Optional[ReActChatFormatter] = None,<br>        output_parser: Optional[ReActOutputParser] = None,<br>        callback_manager: Optional[CallbackManager] = None,<br>        verbose: bool = False,<br>        tool_retriever: Optional[ObjectRetriever[BaseTool]] = None,<br>    ) -> None:<br>        self._multi_modal_llm = multi_modal_llm<br>        self.callback_manager = callback_manager or CallbackManager([])<br>        self._max_iterations = max_iterations<br>        self._react_chat_formatter = react_chat_formatter or ReActChatFormatter(<br>            system_header=REACT_MM_CHAT_SYSTEM_HEADER<br>        )<br>        self._output_parser = output_parser or ReActOutputParser()<br>        self._verbose = verbose<br>        try:<br>            from llama_index.multi_modal_llms.openai.utils import (<br>                generate_openai_multi_modal_chat_message,<br>            )  # pants: no-infer-dep<br>            self._add_user_step_to_reasoning = partial(<br>                add_user_step_to_reasoning,<br>                generate_chat_message_fn=generate_openai_multi_modal_chat_message,  # type: ignore<br>            )<br>        except ImportError:<br>            raise ImportError(<br>                "`llama-index-multi-modal-llms-openai` package cannot be found. "<br>                "Please install it by using `pip install `llama-index-multi-modal-llms-openai`"<br>            )<br>        if len(tools) > 0 and tool_retriever is not None:<br>            raise ValueError("Cannot specify both tools and tool_retriever")<br>        elif len(tools) > 0:<br>            self._get_tools = lambda _: tools<br>        elif tool_retriever is not None:<br>            tool_retriever_c = cast(ObjectRetriever[BaseTool], tool_retriever)<br>            self._get_tools = lambda message: tool_retriever_c.retrieve(message)<br>        else:<br>            self._get_tools = lambda _: []<br>    @classmethod<br>    def from_tools(<br>        cls,<br>        tools: Optional[Sequence[BaseTool]] = None,<br>        tool_retriever: Optional[ObjectRetriever[BaseTool]] = None,<br>        multi_modal_llm: Optional[MultiModalLLM] = None,<br>        max_iterations: int = 10,<br>        react_chat_formatter: Optional[ReActChatFormatter] = None,<br>        output_parser: Optional[ReActOutputParser] = None,<br>        callback_manager: Optional[CallbackManager] = None,<br>        verbose: bool = False,<br>        **kwargs: Any,<br>    ) -> "MultimodalReActAgentWorker":<br>        """Convenience constructor method from set of of BaseTools (Optional).<br>        NOTE: kwargs should have been exhausted by this point. In other words<br>        the various upstream components such as BaseSynthesizer (response synthesizer)<br>        or BaseRetriever should have picked up off their respective kwargs in their<br>        constructions.<br>        Returns:<br>            ReActAgent<br>        """<br>        if multi_modal_llm is None:<br>            try:<br>                from llama_index.multi_modal_llms.openai import (<br>                    OpenAIMultiModal,<br>                )  # pants: no-infer-dep<br>                multi_modal_llm = multi_modal_llm or OpenAIMultiModal(<br>                    model="gpt-4-vision-preview", max_new_tokens=1000<br>                )<br>            except ImportError:<br>                raise ImportError(<br>                    "`llama-index-multi-modal-llms-openai` package cannot be found. "<br>                    "Please install it by using `pip install `llama-index-multi-modal-llms-openai`"<br>                )<br>        return cls(<br>            tools=tools or [],<br>            tool_retriever=tool_retriever,<br>            multi_modal_llm=multi_modal_llm,<br>            max_iterations=max_iterations,<br>            react_chat_formatter=react_chat_formatter,<br>            output_parser=output_parser,<br>            callback_manager=callback_manager,<br>            verbose=verbose,<br>        )<br>    def initialize_step(self, task: Task, **kwargs: Any) -> TaskStep:<br>        """Initialize step from task."""<br>        sources: List[ToolOutput] = []<br>        current_reasoning: List[BaseReasoningStep] = []<br>        # temporary memory for new messages<br>        new_memory = ChatMemoryBuffer.from_defaults()<br>        # validation<br>        if "image_docs" not in task.extra_state:<br>            raise ValueError("Image docs not found in task extra state.")<br>        # initialize task state<br>        task_state = {<br>            "sources": sources,<br>            "current_reasoning": current_reasoning,<br>            "new_memory": new_memory,<br>        }<br>        task.extra_state.update(task_state)<br>        return TaskStep(<br>            task_id=task.task_id,<br>            step_id=str(uuid.uuid4()),<br>            input=task.input,<br>            step_state={"is_first": True, "image_docs": task.extra_state["image_docs"]},<br>        )<br>    def get_tools(self, input: str) -> List[AsyncBaseTool]:<br>        """Get tools."""<br>        return [adapt_to_async_tool(t) for t in self._get_tools(input)]<br>    def _extract_reasoning_step(<br>        self, output: ChatResponse, is_streaming: bool = False<br>    ) -> Tuple[str, List[BaseReasoningStep], bool]:<br>        """<br>        Extracts the reasoning step from the given output.<br>        This method parses the message content from the output,<br>        extracts the reasoning step, and determines whether the processing is<br>        complete. It also performs validation checks on the output and<br>        handles possible errors.<br>        """<br>        if output.message.content is None:<br>            raise ValueError("Got empty message.")<br>        message_content = output.message.content<br>        current_reasoning = []<br>        try:<br>            reasoning_step = self._output_parser.parse(message_content, is_streaming)<br>        except BaseException as exc:<br>            raise ValueError(f"Could not parse output: {message_content}") from exc<br>        if self._verbose:<br>            print_text(f"{reasoning_step.get_content()}\n", color="pink")<br>        current_reasoning.append(reasoning_step)<br>        if reasoning_step.is_done:<br>            return message_content, current_reasoning, True<br>        reasoning_step = cast(ActionReasoningStep, reasoning_step)<br>        if not isinstance(reasoning_step, ActionReasoningStep):<br>            raise ValueError(f"Expected ActionReasoningStep, got {reasoning_step}")<br>        return message_content, current_reasoning, False<br>    def _process_actions(<br>        self,<br>        task: Task,<br>        tools: Sequence[AsyncBaseTool],<br>        output: ChatResponse,<br>        is_streaming: bool = False,<br>    ) -> Tuple[List[BaseReasoningStep], bool]:<br>        tools_dict: Dict[str, AsyncBaseTool] = {<br>            tool.metadata.get_name(): tool for tool in tools<br>        }<br>        _, current_reasoning, is_done = self._extract_reasoning_step(<br>            output, is_streaming<br>        )<br>        if is_done:<br>            return current_reasoning, True<br>        # call tool with input<br>        reasoning_step = cast(ActionReasoningStep, current_reasoning[-1])<br>        tool = tools_dict[reasoning_step.action]<br>        with self.callback_manager.event(<br>            CBEventType.FUNCTION_CALL,<br>            payload={<br>                EventPayload.FUNCTION_CALL: reasoning_step.action_input,<br>                EventPayload.TOOL: tool.metadata,<br>            },<br>        ) as event:<br>            tool_output = tool.call(**reasoning_step.action_input)<br>            event.on_end(payload={EventPayload.FUNCTION_OUTPUT: str(tool_output)})<br>        task.extra_state["sources"].append(tool_output)<br>        observation_step = ObservationReasoningStep(<br>            observation=str(tool_output), return_direct=tool.metadata.return_direct<br>        )<br>        current_reasoning.append(observation_step)<br>        if self._verbose:<br>            print_text(f"{observation_step.get_content()}\n", color="blue")<br>        return current_reasoning, tool.metadata.return_direct<br>    async def _aprocess_actions(<br>        self,<br>        task: Task,<br>        tools: Sequence[AsyncBaseTool],<br>        output: ChatResponse,<br>        is_streaming: bool = False,<br>    ) -> Tuple[List[BaseReasoningStep], bool]:<br>        tools_dict = {tool.metadata.name: tool for tool in tools}<br>        _, current_reasoning, is_done = self._extract_reasoning_step(<br>            output, is_streaming<br>        )<br>        if is_done:<br>            return current_reasoning, True<br>        # call tool with input<br>        reasoning_step = cast(ActionReasoningStep, current_reasoning[-1])<br>        tool = tools_dict[reasoning_step.action]<br>        with self.callback_manager.event(<br>            CBEventType.FUNCTION_CALL,<br>            payload={<br>                EventPayload.FUNCTION_CALL: reasoning_step.action_input,<br>                EventPayload.TOOL: tool.metadata,<br>            },<br>        ) as event:<br>            tool_output = await tool.acall(**reasoning_step.action_input)<br>            event.on_end(payload={EventPayload.FUNCTION_OUTPUT: str(tool_output)})<br>        task.extra_state["sources"].append(tool_output)<br>        observation_step = ObservationReasoningStep(<br>            observation=str(tool_output), return_direct=tool.metadata.return_direct<br>        )<br>        current_reasoning.append(observation_step)<br>        if self._verbose:<br>            print_text(f"{observation_step.get_content()}\n", color="blue")<br>        return current_reasoning, tool.metadata.return_direct<br>    def _get_response(<br>        self,<br>        current_reasoning: List[BaseReasoningStep],<br>        sources: List[ToolOutput],<br>    ) -> AgentChatResponse:<br>        """Get response from reasoning steps."""<br>        if len(current_reasoning) == 0:<br>            raise ValueError("No reasoning steps were taken.")<br>        elif len(current_reasoning) == self._max_iterations:<br>            raise ValueError("Reached max iterations.")<br>        if isinstance(current_reasoning[-1], ResponseReasoningStep):<br>            response_step = cast(ResponseReasoningStep, current_reasoning[-1])<br>            response_str = response_step.response<br>        elif (<br>            isinstance(current_reasoning[-1], ObservationReasoningStep)<br>            and current_reasoning[-1].return_direct<br>        ):<br>            response_str = current_reasoning[-1].observation<br>        else:<br>            response_str = current_reasoning[-1].get_content()<br>        # TODO: add sources from reasoning steps<br>        return AgentChatResponse(response=response_str, sources=sources)<br>    def _get_task_step_response(<br>        self, agent_response: AGENT_CHAT_RESPONSE_TYPE, step: TaskStep, is_done: bool<br>    ) -> TaskStepOutput:<br>        """Get task step response."""<br>        if is_done:<br>            new_steps = []<br>        else:<br>            new_steps = [<br>                step.get_next_step(<br>                    step_id=str(uuid.uuid4()),<br>                    # NOTE: input is unused<br>                    input=None,<br>                )<br>            ]<br>        return TaskStepOutput(<br>            output=agent_response,<br>            task_step=step,<br>            is_last=is_done,<br>            next_steps=new_steps,<br>        )<br>    def _run_step(<br>        self,<br>        step: TaskStep,<br>        task: Task,<br>    ) -> TaskStepOutput:<br>        """Run step."""<br>        # This is either not None on the first step or if the user specifies<br>        # an intermediate step in the middle<br>        if step.input is not None:<br>            self._add_user_step_to_reasoning(<br>                step=step,<br>                memory=task.extra_state["new_memory"],<br>                current_reasoning=task.extra_state["current_reasoning"],<br>                verbose=self._verbose,<br>            )<br>        # TODO: see if we want to do step-based inputs<br>        tools = self.get_tools(task.input)<br>        input_chat = self._react_chat_formatter.format(<br>            tools,<br>            chat_history=task.memory.get_all()<br>            + task.extra_state["new_memory"].get_all(),<br>            current_reasoning=task.extra_state["current_reasoning"],<br>        )<br>        # send prompt<br>        chat_response = self._multi_modal_llm.chat(input_chat)<br>        # given react prompt outputs, call tools or return response<br>        reasoning_steps, is_done = self._process_actions(<br>            task, tools, output=chat_response<br>        )<br>        task.extra_state["current_reasoning"].extend(reasoning_steps)<br>        agent_response = self._get_response(<br>            task.extra_state["current_reasoning"], task.extra_state["sources"]<br>        )<br>        if is_done:<br>            task.extra_state["new_memory"].put(<br>                ChatMessage(content=agent_response.response, role=MessageRole.ASSISTANT)<br>            )<br>        return self._get_task_step_response(agent_response, step, is_done)<br>    async def _arun_step(<br>        self,<br>        step: TaskStep,<br>        task: Task,<br>    ) -> TaskStepOutput:<br>        """Run step."""<br>        if step.input is not None:<br>            self._add_user_step_to_reasoning(<br>                step=step,<br>                memory=task.extra_state["new_memory"],<br>                current_reasoning=task.extra_state["current_reasoning"],<br>                verbose=self._verbose,<br>            )<br>        # TODO: see if we want to do step-based inputs<br>        tools = self.get_tools(task.input)<br>        input_chat = self._react_chat_formatter.format(<br>            tools,<br>            chat_history=task.memory.get_all()<br>            + task.extra_state["new_memory"].get_all(),<br>            current_reasoning=task.extra_state["current_reasoning"],<br>        )<br>        # send prompt<br>        chat_response = await self._multi_modal_llm.achat(input_chat)<br>        # given react prompt outputs, call tools or return response<br>        reasoning_steps, is_done = await self._aprocess_actions(<br>            task, tools, output=chat_response<br>        )<br>        task.extra_state["current_reasoning"].extend(reasoning_steps)<br>        agent_response = self._get_response(<br>            task.extra_state["current_reasoning"], task.extra_state["sources"]<br>        )<br>        if is_done:<br>            task.extra_state["new_memory"].put(<br>                ChatMessage(content=agent_response.response, role=MessageRole.ASSISTANT)<br>            )<br>        return self._get_task_step_response(agent_response, step, is_done)<br>    def _run_step_stream(<br>        self,<br>        step: TaskStep,<br>        task: Task,<br>    ) -> TaskStepOutput:<br>        """Run step."""<br>        raise NotImplementedError("Stream step not implemented yet.")<br>    async def _arun_step_stream(<br>        self,<br>        step: TaskStep,<br>        task: Task,<br>    ) -> TaskStepOutput:<br>        """Run step."""<br>        raise NotImplementedError("Stream step not implemented yet.")<br>    @trace_method("run_step")<br>    def run_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:<br>        """Run step."""<br>        return self._run_step(step, task)<br>    @trace_method("run_step")<br>    async def arun_step(<br>        self, step: TaskStep, task: Task, **kwargs: Any<br>    ) -> TaskStepOutput:<br>        """Run step (async)."""<br>        return await self._arun_step(step, task)<br>    @trace_method("run_step")<br>    def stream_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:<br>        """Run step (stream)."""<br>        # TODO: figure out if we need a different type for TaskStepOutput<br>        return self._run_step_stream(step, task)<br>    @trace_method("run_step")<br>    async def astream_step(<br>        self, step: TaskStep, task: Task, **kwargs: Any<br>    ) -> TaskStepOutput:<br>        """Run step (async stream)."""<br>        return await self._arun_step_stream(step, task)<br>    def finalize_task(self, task: Task, **kwargs: Any) -> None:<br>        """Finalize task, after all the steps are completed."""<br>        # add new messages to memory<br>        task.memory.set(<br>            task.memory.get_all() + task.extra_state["new_memory"].get_all()<br>        )<br>        # reset new memory<br>        task.extra_state["new_memory"].reset()<br>    def set_callback_manager(self, callback_manager: CallbackManager) -> None:<br>        """Set callback manager."""<br>        # TODO: make this abstractmethod (right now will break some agent impls)<br>        self.callback_manager = callback_manager<br>``` |

#### from\_tools`classmethod`[\#](\#llama_index.core.agent.MultimodalReActAgentWorker.from_tools "Permanent link")

```
from_tools(tools: Optional[Sequence[BaseTool]] = None, tool_retriever: Optional[ObjectRetriever[BaseTool]] = None, multi_modal_llm: Optional[MultiModalLLM] = None, max_iterations: int = 10, react_chat_formatter: Optional[ReActChatFormatter] = None, output_parser: Optional[ReActOutputParser] = None, callback_manager: Optional[CallbackManager] = None, verbose: bool = False, **kwargs: Any) -> MultimodalReActAgentWorker

```

Convenience constructor method from set of of BaseTools (Optional).

NOTE: kwargs should have been exhausted by this point. In other words
the various upstream components such as BaseSynthesizer (response synthesizer)
or BaseRetriever should have picked up off their respective kwargs in their
constructions.

**Returns:**

| Type | Description |
| --- | --- |
| `MultimodalReActAgentWorker` | ReActAgent |

Source code in `llama-index-core/llama_index/core/agent/react_multimodal/step.py`

|     |     |
| --- | --- |
| ```<br>155<br>156<br>157<br>158<br>159<br>160<br>161<br>162<br>163<br>164<br>165<br>166<br>167<br>168<br>169<br>170<br>171<br>172<br>173<br>174<br>175<br>176<br>177<br>178<br>179<br>180<br>181<br>182<br>183<br>184<br>185<br>186<br>187<br>188<br>189<br>190<br>191<br>192<br>193<br>194<br>195<br>196<br>197<br>198<br>199<br>200<br>201<br>``` | ```<br>@classmethod<br>def from_tools(<br>    cls,<br>    tools: Optional[Sequence[BaseTool]] = None,<br>    tool_retriever: Optional[ObjectRetriever[BaseTool]] = None,<br>    multi_modal_llm: Optional[MultiModalLLM] = None,<br>    max_iterations: int = 10,<br>    react_chat_formatter: Optional[ReActChatFormatter] = None,<br>    output_parser: Optional[ReActOutputParser] = None,<br>    callback_manager: Optional[CallbackManager] = None,<br>    verbose: bool = False,<br>    **kwargs: Any,<br>) -> "MultimodalReActAgentWorker":<br>    """Convenience constructor method from set of of BaseTools (Optional).<br>    NOTE: kwargs should have been exhausted by this point. In other words<br>    the various upstream components such as BaseSynthesizer (response synthesizer)<br>    or BaseRetriever should have picked up off their respective kwargs in their<br>    constructions.<br>    Returns:<br>        ReActAgent<br>    """<br>    if multi_modal_llm is None:<br>        try:<br>            from llama_index.multi_modal_llms.openai import (<br>                OpenAIMultiModal,<br>            )  # pants: no-infer-dep<br>            multi_modal_llm = multi_modal_llm or OpenAIMultiModal(<br>                model="gpt-4-vision-preview", max_new_tokens=1000<br>            )<br>        except ImportError:<br>            raise ImportError(<br>                "`llama-index-multi-modal-llms-openai` package cannot be found. "<br>                "Please install it by using `pip install `llama-index-multi-modal-llms-openai`"<br>            )<br>    return cls(<br>        tools=tools or [],<br>        tool_retriever=tool_retriever,<br>        multi_modal_llm=multi_modal_llm,<br>        max_iterations=max_iterations,<br>        react_chat_formatter=react_chat_formatter,<br>        output_parser=output_parser,<br>        callback_manager=callback_manager,<br>        verbose=verbose,<br>    )<br>``` |

#### initialize\_step [\#](\#llama_index.core.agent.MultimodalReActAgentWorker.initialize_step "Permanent link")

```
initialize_step(task: Task, **kwargs: Any) -> TaskStep

```

Initialize step from task.

Source code in `llama-index-core/llama_index/core/agent/react_multimodal/step.py`

|     |     |
| --- | --- |
| ```<br>203<br>204<br>205<br>206<br>207<br>208<br>209<br>210<br>211<br>212<br>213<br>214<br>215<br>216<br>217<br>218<br>219<br>220<br>221<br>222<br>223<br>224<br>225<br>226<br>227<br>``` | ```<br>def initialize_step(self, task: Task, **kwargs: Any) -> TaskStep:<br>    """Initialize step from task."""<br>    sources: List[ToolOutput] = []<br>    current_reasoning: List[BaseReasoningStep] = []<br>    # temporary memory for new messages<br>    new_memory = ChatMemoryBuffer.from_defaults()<br>    # validation<br>    if "image_docs" not in task.extra_state:<br>        raise ValueError("Image docs not found in task extra state.")<br>    # initialize task state<br>    task_state = {<br>        "sources": sources,<br>        "current_reasoning": current_reasoning,<br>        "new_memory": new_memory,<br>    }<br>    task.extra_state.update(task_state)<br>    return TaskStep(<br>        task_id=task.task_id,<br>        step_id=str(uuid.uuid4()),<br>        input=task.input,<br>        step_state={"is_first": True, "image_docs": task.extra_state["image_docs"]},<br>    )<br>``` |

#### get\_tools [\#](\#llama_index.core.agent.MultimodalReActAgentWorker.get_tools "Permanent link")

```
get_tools(input: str) -> List[AsyncBaseTool]

```

Get tools.

Source code in `llama-index-core/llama_index/core/agent/react_multimodal/step.py`

|     |     |
| --- | --- |
| ```<br>229<br>230<br>231<br>``` | ```<br>def get_tools(self, input: str) -> List[AsyncBaseTool]:<br>    """Get tools."""<br>    return [adapt_to_async_tool(t) for t in self._get_tools(input)]<br>``` |

#### run\_step [\#](\#llama_index.core.agent.MultimodalReActAgentWorker.run_step "Permanent link")

```
run_step(step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput

```

Run step.

Source code in `llama-index-core/llama_index/core/agent/react_multimodal/step.py`

|     |     |
| --- | --- |
| ```<br>487<br>488<br>489<br>490<br>``` | ```<br>@trace_method("run_step")<br>def run_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:<br>    """Run step."""<br>    return self._run_step(step, task)<br>``` |

#### arun\_step`async`[\#](\#llama_index.core.agent.MultimodalReActAgentWorker.arun_step "Permanent link")

```
arun_step(step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput

```

Run step (async).

Source code in `llama-index-core/llama_index/core/agent/react_multimodal/step.py`

|     |     |
| --- | --- |
| ```<br>492<br>493<br>494<br>495<br>496<br>497<br>``` | ```<br>@trace_method("run_step")<br>async def arun_step(<br>    self, step: TaskStep, task: Task, **kwargs: Any<br>) -> TaskStepOutput:<br>    """Run step (async)."""<br>    return await self._arun_step(step, task)<br>``` |

#### stream\_step [\#](\#llama_index.core.agent.MultimodalReActAgentWorker.stream_step "Permanent link")

```
stream_step(step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput

```

Run step (stream).

Source code in `llama-index-core/llama_index/core/agent/react_multimodal/step.py`

|     |     |
| --- | --- |
| ```<br>499<br>500<br>501<br>502<br>503<br>``` | ```<br>@trace_method("run_step")<br>def stream_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:<br>    """Run step (stream)."""<br>    # TODO: figure out if we need a different type for TaskStepOutput<br>    return self._run_step_stream(step, task)<br>``` |

#### astream\_step`async`[\#](\#llama_index.core.agent.MultimodalReActAgentWorker.astream_step "Permanent link")

```
astream_step(step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput

```

Run step (async stream).

Source code in `llama-index-core/llama_index/core/agent/react_multimodal/step.py`

|     |     |
| --- | --- |
| ```<br>505<br>506<br>507<br>508<br>509<br>510<br>``` | ```<br>@trace_method("run_step")<br>async def astream_step(<br>    self, step: TaskStep, task: Task, **kwargs: Any<br>) -> TaskStepOutput:<br>    """Run step (async stream)."""<br>    return await self._arun_step_stream(step, task)<br>``` |

#### finalize\_task [\#](\#llama_index.core.agent.MultimodalReActAgentWorker.finalize_task "Permanent link")

```
finalize_task(task: Task, **kwargs: Any) -> None

```

Finalize task, after all the steps are completed.

Source code in `llama-index-core/llama_index/core/agent/react_multimodal/step.py`

|     |     |
| --- | --- |
| ```<br>512<br>513<br>514<br>515<br>516<br>517<br>518<br>519<br>``` | ```<br>def finalize_task(self, task: Task, **kwargs: Any) -> None:<br>    """Finalize task, after all the steps are completed."""<br>    # add new messages to memory<br>    task.memory.set(<br>        task.memory.get_all() + task.extra_state["new_memory"].get_all()<br>    )<br>    # reset new memory<br>    task.extra_state["new_memory"].reset()<br>``` |

#### set\_callback\_manager [\#](\#llama_index.core.agent.MultimodalReActAgentWorker.set_callback_manager "Permanent link")

```
set_callback_manager(callback_manager: CallbackManager) -> None

```

Set callback manager.

Source code in `llama-index-core/llama_index/core/agent/react_multimodal/step.py`

|     |     |
| --- | --- |
| ```<br>521<br>522<br>523<br>524<br>``` | ```<br>def set_callback_manager(self, callback_manager: CallbackManager) -> None:<br>    """Set callback manager."""<br>    # TODO: make this abstractmethod (right now will break some agent impls)<br>    self.callback_manager = callback_manager<br>``` |

### QueryPipelineAgentWorker [\#](\#llama_index.core.agent.QueryPipelineAgentWorker "Permanent link")

Bases: `BaseModel`, `BaseAgentWorker`

Query Pipeline agent worker.

NOTE: This is now deprecated. Use `FnAgentWorker` instead to build a stateful agent.

Barebones agent worker that takes in a query pipeline.

**Default Workflow**: The default workflow assumes that you compose
a query pipeline with `StatefulFnComponent` objects. This allows you to store, update
and retrieve state throughout the executions of the query pipeline by the agent.

The task and step state of the agent are stored in this `state` variable via a special key.
Of course you can choose to store other variables in this state as well.

**Deprecated Workflow**: The deprecated workflow assumes that the first component in the
query pipeline is an `AgentInputComponent` and last is `AgentFnComponent`.

**Parameters:**

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `pipeline` | `QueryPipeline` | Query pipeline | _required_ |

Source code in `llama-index-core/llama_index/core/agent/custom/pipeline_worker.py`

|     |     |
| --- | --- |
| ```<br> 54<br> 55<br> 56<br> 57<br> 58<br> 59<br> 60<br> 61<br> 62<br> 63<br> 64<br> 65<br> 66<br> 67<br> 68<br> 69<br> 70<br> 71<br> 72<br> 73<br> 74<br> 75<br> 76<br> 77<br> 78<br> 79<br> 80<br> 81<br> 82<br> 83<br> 84<br> 85<br> 86<br> 87<br> 88<br> 89<br> 90<br> 91<br> 92<br> 93<br> 94<br> 95<br> 96<br> 97<br> 98<br> 99<br>100<br>101<br>102<br>103<br>104<br>105<br>106<br>107<br>108<br>109<br>110<br>111<br>112<br>113<br>114<br>115<br>116<br>117<br>118<br>119<br>120<br>121<br>122<br>123<br>124<br>125<br>126<br>127<br>128<br>129<br>130<br>131<br>132<br>133<br>134<br>135<br>136<br>137<br>138<br>139<br>140<br>141<br>142<br>143<br>144<br>145<br>146<br>147<br>148<br>149<br>150<br>151<br>152<br>153<br>154<br>155<br>156<br>157<br>158<br>159<br>160<br>161<br>162<br>163<br>164<br>165<br>166<br>167<br>168<br>169<br>170<br>171<br>172<br>173<br>174<br>175<br>176<br>177<br>178<br>179<br>180<br>181<br>182<br>183<br>184<br>185<br>186<br>187<br>188<br>189<br>190<br>191<br>192<br>193<br>194<br>195<br>196<br>197<br>198<br>199<br>200<br>201<br>202<br>203<br>204<br>205<br>206<br>207<br>208<br>209<br>210<br>211<br>212<br>213<br>214<br>215<br>216<br>217<br>218<br>219<br>220<br>221<br>222<br>223<br>224<br>225<br>226<br>227<br>228<br>229<br>230<br>231<br>232<br>233<br>234<br>235<br>236<br>237<br>238<br>239<br>240<br>241<br>242<br>243<br>244<br>245<br>246<br>247<br>248<br>249<br>250<br>251<br>252<br>253<br>254<br>255<br>256<br>``` | ```<br>@deprecated("Use `FnAgentWorker` instead to build a stateful agent.")<br>class QueryPipelineAgentWorker(BaseModel, BaseAgentWorker):<br>    """Query Pipeline agent worker.<br>    NOTE: This is now deprecated. Use `FnAgentWorker` instead to build a stateful agent.<br>    Barebones agent worker that takes in a query pipeline.<br>    **Default Workflow**: The default workflow assumes that you compose<br>    a query pipeline with `StatefulFnComponent` objects. This allows you to store, update<br>    and retrieve state throughout the executions of the query pipeline by the agent.<br>    The task and step state of the agent are stored in this `state` variable via a special key.<br>    Of course you can choose to store other variables in this state as well.<br>    **Deprecated Workflow**: The deprecated workflow assumes that the first component in the<br>    query pipeline is an `AgentInputComponent` and last is `AgentFnComponent`.<br>    Args:<br>        pipeline (QueryPipeline): Query pipeline<br>    """<br>    model_config = ConfigDict(arbitrary_types_allowed=True)<br>    pipeline: QueryPipeline = Field(..., description="Query pipeline")<br>    callback_manager: CallbackManager = Field(..., exclude=True)<br>    task_key: str = Field("task", description="Key to store task in state")<br>    step_state_key: str = Field("step_state", description="Key to store step in state")<br>    def __init__(<br>        self,<br>        pipeline: QueryPipeline,<br>        callback_manager: Optional[CallbackManager] = None,<br>        **kwargs: Any,<br>    ) -> None:<br>        """Initialize."""<br>        if callback_manager is not None:<br>            # set query pipeline callback<br>            pipeline.set_callback_manager(callback_manager)<br>        else:<br>            callback_manager = pipeline.callback_manager<br>        super().__init__(<br>            pipeline=pipeline,<br>            callback_manager=callback_manager,<br>            **kwargs,<br>        )<br>        # validate query pipeline<br>        # self.agent_input_component<br>        self.agent_components<br>    @property<br>    def agent_input_component(self) -> AgentInputComponent:<br>        """Get agent input component.<br>        NOTE: This is deprecated and will be removed in the future.<br>        """<br>        root_key = self.pipeline.get_root_keys()[0]<br>        if not isinstance(self.pipeline.module_dict[root_key], AgentInputComponent):<br>            raise ValueError(<br>                "Query pipeline first component must be AgentInputComponent, got "<br>                f"{self.pipeline.module_dict[root_key]}"<br>            )<br>        return cast(AgentInputComponent, self.pipeline.module_dict[root_key])<br>    @property<br>    def agent_components(self) -> Sequence[BaseAgentComponent]:<br>        """Get agent output component."""<br>        return _get_agent_components(self.pipeline)<br>    def preprocess(self, task: Task, step: TaskStep) -> None:<br>        """Preprocessing flow.<br>        This runs preprocessing to propagate the task and step as variables<br>        to relevant components in the query pipeline.<br>        Contains deprecated flow of updating agent components.<br>        But also contains main flow of updating StatefulFnComponent components.<br>        """<br>        # NOTE: this is deprecated<br>        # partial agent output component with task and step<br>        for agent_fn_component in self.agent_components:<br>            agent_fn_component.partial(task=task, state=step.step_state)<br>        # update stateful components<br>        self.pipeline.update_state(<br>            {self.task_key: task, self.step_state_key: step.step_state}<br>        )<br>    def initialize_step(self, task: Task, **kwargs: Any) -> TaskStep:<br>        """Initialize step from task."""<br>        sources: List[ToolOutput] = []<br>        # temporary memory for new messages<br>        new_memory = ChatMemoryBuffer.from_defaults()<br>        # initialize initial state<br>        initial_state = {<br>            "sources": sources,<br>            "memory": new_memory,<br>        }<br>        return TaskStep(<br>            task_id=task.task_id,<br>            step_id=str(uuid.uuid4()),<br>            input=task.input,<br>            step_state=initial_state,<br>        )<br>    def _get_task_step_response(<br>        self, agent_response: AGENT_CHAT_RESPONSE_TYPE, step: TaskStep, is_done: bool<br>    ) -> TaskStepOutput:<br>        """Get task step response."""<br>        if is_done:<br>            new_steps = []<br>        else:<br>            new_steps = [<br>                step.get_next_step(<br>                    step_id=str(uuid.uuid4()),<br>                    # NOTE: input is unused<br>                    input=None,<br>                )<br>            ]<br>        return TaskStepOutput(<br>            output=agent_response,<br>            task_step=step,<br>            is_last=is_done,<br>            next_steps=new_steps,<br>        )<br>    @trace_method("run_step")<br>    def run_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:<br>        """Run step."""<br>        self.preprocess(task, step)<br>        # HACK: do a try/except for now. Fine since old agent components are deprecated<br>        try:<br>            self.agent_input_component<br>            uses_deprecated = True<br>        except ValueError:<br>            uses_deprecated = False<br>        if uses_deprecated:<br>            agent_response, is_done = self.pipeline.run(<br>                state=step.step_state, task=task<br>            )<br>        else:<br>            agent_response, is_done = self.pipeline.run()<br>        response = self._get_task_step_response(agent_response, step, is_done)<br>        # sync step state with task state<br>        task.extra_state.update(step.step_state)<br>        return response<br>    @trace_method("run_step")<br>    async def arun_step(<br>        self, step: TaskStep, task: Task, **kwargs: Any<br>    ) -> TaskStepOutput:<br>        """Run step (async)."""<br>        self.preprocess(task, step)<br>        # HACK: do a try/except for now. Fine since old agent components are deprecated<br>        try:<br>            self.agent_input_component<br>            uses_deprecated = True<br>        except ValueError:<br>            uses_deprecated = False<br>        if uses_deprecated:<br>            agent_response, is_done = await self.pipeline.arun(<br>                state=step.step_state, task=task<br>            )<br>        else:<br>            agent_response, is_done = await self.pipeline.arun()<br>        response = self._get_task_step_response(agent_response, step, is_done)<br>        task.extra_state.update(step.step_state)<br>        return response<br>    @trace_method("run_step")<br>    def stream_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:<br>        """Run step (stream)."""<br>        raise NotImplementedError("This agent does not support streaming.")<br>    @trace_method("run_step")<br>    async def astream_step(<br>        self, step: TaskStep, task: Task, **kwargs: Any<br>    ) -> TaskStepOutput:<br>        """Run step (async stream)."""<br>        raise NotImplementedError("This agent does not support streaming.")<br>    def finalize_task(self, task: Task, **kwargs: Any) -> None:<br>        """Finalize task, after all the steps are completed."""<br>        # add new messages to memory<br>        task.memory.set(task.memory.get() + task.extra_state["memory"].get_all())<br>        # reset new memory<br>        task.extra_state["memory"].reset()<br>    def set_callback_manager(self, callback_manager: CallbackManager) -> None:<br>        """Set callback manager."""<br>        # TODO: make this abstractmethod (right now will break some agent impls)<br>        self.callback_manager = callback_manager<br>        self.pipeline.set_callback_manager(callback_manager)<br>``` |

#### agent\_input\_component`property`[\#](\#llama_index.core.agent.QueryPipelineAgentWorker.agent_input_component "Permanent link")

```
agent_input_component: AgentInputComponent

```

Get agent input component.

NOTE: This is deprecated and will be removed in the future.

#### agent\_components`property`[\#](\#llama_index.core.agent.QueryPipelineAgentWorker.agent_components "Permanent link")

```
agent_components: Sequence[BaseAgentComponent]

```

Get agent output component.

#### preprocess [\#](\#llama_index.core.agent.QueryPipelineAgentWorker.preprocess "Permanent link")

```
preprocess(task: Task, step: TaskStep) -> None

```

Preprocessing flow.

This runs preprocessing to propagate the task and step as variables
to relevant components in the query pipeline.

Contains deprecated flow of updating agent components.
But also contains main flow of updating StatefulFnComponent components.

Source code in `llama-index-core/llama_index/core/agent/custom/pipeline_worker.py`

|     |     |
| --- | --- |
| ```<br>125<br>126<br>127<br>128<br>129<br>130<br>131<br>132<br>133<br>134<br>135<br>136<br>137<br>138<br>139<br>140<br>141<br>142<br>143<br>``` | ```<br>def preprocess(self, task: Task, step: TaskStep) -> None:<br>    """Preprocessing flow.<br>    This runs preprocessing to propagate the task and step as variables<br>    to relevant components in the query pipeline.<br>    Contains deprecated flow of updating agent components.<br>    But also contains main flow of updating StatefulFnComponent components.<br>    """<br>    # NOTE: this is deprecated<br>    # partial agent output component with task and step<br>    for agent_fn_component in self.agent_components:<br>        agent_fn_component.partial(task=task, state=step.step_state)<br>    # update stateful components<br>    self.pipeline.update_state(<br>        {self.task_key: task, self.step_state_key: step.step_state}<br>    )<br>``` |

#### initialize\_step [\#](\#llama_index.core.agent.QueryPipelineAgentWorker.initialize_step "Permanent link")

```
initialize_step(task: Task, **kwargs: Any) -> TaskStep

```

Initialize step from task.

Source code in `llama-index-core/llama_index/core/agent/custom/pipeline_worker.py`

|     |     |
| --- | --- |
| ```<br>145<br>146<br>147<br>148<br>149<br>150<br>151<br>152<br>153<br>154<br>155<br>156<br>157<br>158<br>159<br>160<br>161<br>162<br>``` | ```<br>def initialize_step(self, task: Task, **kwargs: Any) -> TaskStep:<br>    """Initialize step from task."""<br>    sources: List[ToolOutput] = []<br>    # temporary memory for new messages<br>    new_memory = ChatMemoryBuffer.from_defaults()<br>    # initialize initial state<br>    initial_state = {<br>        "sources": sources,<br>        "memory": new_memory,<br>    }<br>    return TaskStep(<br>        task_id=task.task_id,<br>        step_id=str(uuid.uuid4()),<br>        input=task.input,<br>        step_state=initial_state,<br>    )<br>``` |

#### run\_step [\#](\#llama_index.core.agent.QueryPipelineAgentWorker.run_step "Permanent link")

```
run_step(step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput

```

Run step.

Source code in `llama-index-core/llama_index/core/agent/custom/pipeline_worker.py`

|     |     |
| --- | --- |
| ```<br>186<br>187<br>188<br>189<br>190<br>191<br>192<br>193<br>194<br>195<br>196<br>197<br>198<br>199<br>200<br>201<br>202<br>203<br>204<br>205<br>206<br>207<br>``` | ```<br>@trace_method("run_step")<br>def run_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:<br>    """Run step."""<br>    self.preprocess(task, step)<br>    # HACK: do a try/except for now. Fine since old agent components are deprecated<br>    try:<br>        self.agent_input_component<br>        uses_deprecated = True<br>    except ValueError:<br>        uses_deprecated = False<br>    if uses_deprecated:<br>        agent_response, is_done = self.pipeline.run(<br>            state=step.step_state, task=task<br>        )<br>    else:<br>        agent_response, is_done = self.pipeline.run()<br>    response = self._get_task_step_response(agent_response, step, is_done)<br>    # sync step state with task state<br>    task.extra_state.update(step.step_state)<br>    return response<br>``` |

#### arun\_step`async`[\#](\#llama_index.core.agent.QueryPipelineAgentWorker.arun_step "Permanent link")

```
arun_step(step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput

```

Run step (async).

Source code in `llama-index-core/llama_index/core/agent/custom/pipeline_worker.py`

|     |     |
| --- | --- |
| ```<br>209<br>210<br>211<br>212<br>213<br>214<br>215<br>216<br>217<br>218<br>219<br>220<br>221<br>222<br>223<br>224<br>225<br>226<br>227<br>228<br>229<br>230<br>231<br>``` | ```<br>@trace_method("run_step")<br>async def arun_step(<br>    self, step: TaskStep, task: Task, **kwargs: Any<br>) -> TaskStepOutput:<br>    """Run step (async)."""<br>    self.preprocess(task, step)<br>    # HACK: do a try/except for now. Fine since old agent components are deprecated<br>    try:<br>        self.agent_input_component<br>        uses_deprecated = True<br>    except ValueError:<br>        uses_deprecated = False<br>    if uses_deprecated:<br>        agent_response, is_done = await self.pipeline.arun(<br>            state=step.step_state, task=task<br>        )<br>    else:<br>        agent_response, is_done = await self.pipeline.arun()<br>    response = self._get_task_step_response(agent_response, step, is_done)<br>    task.extra_state.update(step.step_state)<br>    return response<br>``` |

#### stream\_step [\#](\#llama_index.core.agent.QueryPipelineAgentWorker.stream_step "Permanent link")

```
stream_step(step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput

```

Run step (stream).

Source code in `llama-index-core/llama_index/core/agent/custom/pipeline_worker.py`

|     |     |
| --- | --- |
| ```<br>233<br>234<br>235<br>236<br>``` | ```<br>@trace_method("run_step")<br>def stream_step(self, step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput:<br>    """Run step (stream)."""<br>    raise NotImplementedError("This agent does not support streaming.")<br>``` |

#### astream\_step`async`[\#](\#llama_index.core.agent.QueryPipelineAgentWorker.astream_step "Permanent link")

```
astream_step(step: TaskStep, task: Task, **kwargs: Any) -> TaskStepOutput

```

Run step (async stream).

Source code in `llama-index-core/llama_index/core/agent/custom/pipeline_worker.py`

|     |     |
| --- | --- |
| ```<br>238<br>239<br>240<br>241<br>242<br>243<br>``` | ```<br>@trace_method("run_step")<br>async def astream_step(<br>    self, step: TaskStep, task: Task, **kwargs: Any<br>) -> TaskStepOutput:<br>    """Run step (async stream)."""<br>    raise NotImplementedError("This agent does not support streaming.")<br>``` |

#### finalize\_task [\#](\#llama_index.core.agent.QueryPipelineAgentWorker.finalize_task "Permanent link")

```
finalize_task(task: Task, **kwargs: Any) -> None

```

Finalize task, after all the steps are completed.

Source code in `llama-index-core/llama_index/core/agent/custom/pipeline_worker.py`

|     |     |
| --- | --- |
| ```<br>245<br>246<br>247<br>248<br>249<br>250<br>``` | ```<br>def finalize_task(self, task: Task, **kwargs: Any) -> None:<br>    """Finalize task, after all the steps are completed."""<br>    # add new messages to memory<br>    task.memory.set(task.memory.get() + task.extra_state["memory"].get_all())<br>    # reset new memory<br>    task.extra_state["memory"].reset()<br>``` |

#### set\_callback\_manager [\#](\#llama_index.core.agent.QueryPipelineAgentWorker.set_callback_manager "Permanent link")

```
set_callback_manager(callback_manager: CallbackManager) -> None

```

Set callback manager.

Source code in `llama-index-core/llama_index/core/agent/custom/pipeline_worker.py`

|     |     |
| --- | --- |
| ```<br>252<br>253<br>254<br>255<br>256<br>``` | ```<br>def set_callback_manager(self, callback_manager: CallbackManager) -> None:<br>    """Set callback manager."""<br>    # TODO: make this abstractmethod (right now will break some agent impls)<br>    self.callback_manager = callback_manager<br>    self.pipeline.set_callback_manager(callback_manager)<br>``` |

Back to top
```

----

